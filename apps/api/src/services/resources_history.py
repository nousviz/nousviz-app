"""
B273 (v0.9.11.19) — read helpers for `system_resources_history`.

The snapshot worker (apps/worker/src/snapshot_resources.py) writes one
row per day with compact JSONB. This module turns those rows into the
two time-series shapes the API exposes:

  - per-metric history: e.g. plugin_size for plugin 'gsc' over 30 days
  - per-finding history: presence/severity per snapshot for one rule_id

Defense in depth: the metric and finding identifiers are validated
against in-code whitelists (`SUPPORTED_METRICS` and the diagnostics
POLICIES_BY_KEY) before any SQL composes. JSON path extraction uses
parameter binding so user input never reaches identifier position.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.resources_history")


# Whitelisted metrics. Each entry is (json_path_kind, field_name) where
# json_path_kind is one of 'postgres_scalar', 'plugin_size'. New metrics
# go through this map — keeps the service free of arbitrary JSON path
# composition from URL params.
SUPPORTED_METRICS: dict[str, tuple[str, str]] = {
    "db_size": ("postgres_scalar", "db_size_mb"),
    "cache_hit_pct": ("postgres_scalar", "cache_hit_pct"),
    "plugin_size": ("plugin_size", "total_size_mb"),
}


# Days param ceiling — refuses absurd queries that would scan the
# whole table.
MAX_HISTORY_DAYS = 90


# ── Data shapes ─────────────────────────────────────────────────────


@dataclass
class HistoryPoint:
    snapshot_at: str
    value: Optional[float]


@dataclass
class FindingHistoryPoint:
    snapshot_at: str
    present: bool
    severity: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────


def _ts_iso(ts) -> str:
    if ts is None:
        return ""
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def _clamp_days(days: int) -> int:
    if days < 1:
        return 1
    if days > MAX_HISTORY_DAYS:
        return MAX_HISTORY_DAYS
    return days


# ── Metric history ─────────────────────────────────────────────────


def get_metric_history(
    metric: str,
    *,
    plugin: Optional[str] = None,
    days: int = 30,
) -> list[HistoryPoint]:
    """Return [{snapshot_at, value}] over the last N days for one metric.

    `metric` must be in SUPPORTED_METRICS. For `plugin_size`, `plugin`
    is required. For `postgres_scalar` metrics, `plugin` is ignored.

    A snapshot where the metric is absent (e.g. plugin not installed
    yet) returns `value=None` so gaps render as "no data" in the UI,
    not as zero.
    """
    if metric not in SUPPORTED_METRICS:
        raise ValueError(
            f"Unsupported metric: {metric!r}. Supported: {sorted(SUPPORTED_METRICS)}"
        )
    kind, field = SUPPORTED_METRICS[metric]
    if kind == "plugin_size" and not plugin:
        raise ValueError(f"metric={metric!r} requires the `plugin` parameter")

    days = _clamp_days(days)
    out: list[HistoryPoint] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        if kind == "postgres_scalar":
            # postgres -> field, e.g. postgres->>'db_size_mb'
            cur.execute(
                """
                SELECT snapshot_at, (postgres ->> %s)::float
                FROM system_resources_history
                WHERE snapshot_at >= now() - make_interval(days => %s)
                ORDER BY snapshot_at ASC
                """,
                (field, days),
            )
        else:
            # plugin_size: jsonb_array_elements(plugins) → find id == plugin → take field
            cur.execute(
                """
                SELECT snapshot_at,
                       (
                         SELECT (entry ->> %s)::float
                         FROM jsonb_array_elements(plugins) AS entry
                         WHERE entry ->> 'id' = %s
                         LIMIT 1
                       ) AS value
                FROM system_resources_history
                WHERE snapshot_at >= now() - make_interval(days => %s)
                ORDER BY snapshot_at ASC
                """,
                (field, plugin, days),
            )
        for row in cur.fetchall():
            ts, value = row
            out.append(HistoryPoint(
                snapshot_at=_ts_iso(ts),
                value=float(value) if value is not None else None,
            ))
    return out


# ── Finding history ────────────────────────────────────────────────


def get_finding_history(
    finding_id: str,
    *,
    days: int = 30,
) -> list[FindingHistoryPoint]:
    """Return [{snapshot_at, present, severity}] over the last N days.

    A snapshot where the finding is in the array → present=True with
    severity. A snapshot where it's absent → present=False, severity=None.
    """
    # Validate against the diagnostics rule registry — if the rule_id
    # doesn't match a known rule, we still query (the historical row
    # might predate a renamed rule), but reject obviously-malformed input.
    if not finding_id or len(finding_id) > 80 or not all(
        c.isalnum() or c in "_:-." for c in finding_id
    ):
        raise ValueError(f"Invalid finding_id: {finding_id!r}")

    days = _clamp_days(days)
    out: list[FindingHistoryPoint] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT snapshot_at,
                   findings @> jsonb_build_array(jsonb_build_object('id', %s::text)) AS present,
                   (
                     SELECT entry ->> 'severity'
                     FROM jsonb_array_elements(findings) AS entry
                     WHERE entry ->> 'id' = %s
                     LIMIT 1
                   ) AS severity
            FROM system_resources_history
            WHERE snapshot_at >= now() - make_interval(days => %s)
            ORDER BY snapshot_at ASC
            """,
            (finding_id, finding_id, days),
        )
        for row in cur.fetchall():
            ts, present, severity = row
            out.append(FindingHistoryPoint(
                snapshot_at=_ts_iso(ts),
                present=bool(present),
                severity=severity,
            ))
    return out


# ── Snapshot writer (used by the worker) ───────────────────────────


def _json_default(obj):
    """JSON encoder fallback for psycopg2-typed values that don't have
    a native JSON form: Decimal (postgres NUMERIC), datetime/date,
    UUID. Coerces each to a sensible primitive so json.dumps doesn't
    raise TypeError on snapshot persistence.

    v0.9.11.19.1 hotfix: production caught `Object of type Decimal is
    not JSON serializable` on the first manual snapshot run because
    postgres_resources surfaces some pct/size values as Decimal. We
    keep the conversion here at the JSON boundary rather than mapping
    every collector field, so future schema additions can't reintroduce
    the same failure mode.
    """
    from decimal import Decimal
    from datetime import date
    from uuid import UUID
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def insert_snapshot(payload: dict, snapshot_at: Optional[datetime] = None) -> None:
    """Insert one snapshot row. Uses the supplied timestamp or now()."""
    import json
    when = snapshot_at or datetime.now(timezone.utc)

    def _dump(value) -> str:
        return json.dumps(value, default=_json_default)

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO system_resources_history (
                snapshot_at, server, postgres, plugins, syncs, findings
            ) VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
            ON CONFLICT (snapshot_at) DO UPDATE SET
                server   = EXCLUDED.server,
                postgres = EXCLUDED.postgres,
                plugins  = EXCLUDED.plugins,
                syncs    = EXCLUDED.syncs,
                findings = EXCLUDED.findings
            """,
            (
                when,
                _dump(payload.get("server")),
                _dump(payload.get("postgres")),
                _dump(payload.get("plugins") or []),
                _dump(payload.get("syncs") or []),
                _dump(payload.get("findings") or []),
            ),
        )
        conn.commit()


def purge_old_snapshots(retention_days: int = 90) -> int:
    """Drop snapshots older than retention_days. Returns row count."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM system_resources_history
            WHERE snapshot_at < now() - make_interval(days => %s)
            """,
            (int(retention_days),),
        )
        n = cur.rowcount
        conn.commit()
    return max(0, n or 0)


# ── Compactor (used by the worker) ─────────────────────────────────


def compact_snapshot(
    snap: dict,
    findings: list[dict],
    *,
    max_per_section: int = 20,
) -> dict:
    """Strip a `_collect_resources_snapshot()` dict + findings list to
    the top-N entries per section. Drops fields the history queries
    don't need, keeps row size < 50 KB on production-shape data.

    The plugins / syncs lists arrive already sorted by size / load
    descending from postgres_resources, so [:max_per_section] is the
    right "top N".
    """
    return {
        "server": snap.get("server"),
        "postgres": snap.get("postgres"),
        "plugins": (snap.get("plugins") or [])[:max_per_section],
        "syncs": (snap.get("syncs") or [])[:max_per_section],
        # Findings are already bounded (~12 rules); store id+severity only.
        "findings": [
            {"id": f.get("id"), "severity": f.get("severity")}
            for f in (findings or [])
        ],
    }
