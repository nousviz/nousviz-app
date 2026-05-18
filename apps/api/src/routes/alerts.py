"""
/api/alerts — Alert management

Handles pre-built plugin alerts (toggle on/off with config) and
custom user-created alerts.

Storage: Postgres `alert_rules` table (migration 025).
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn, rows_as_dicts
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.alerts import (
    AlertDeleteResponse,
    AlertRow,
    AlertSourcesResponse,
    AlertSparklineResponse,
    AlertTestResponse,
    AlertsListResponse,
)

logger = logging.getLogger("nousviz.api.alerts")

router = APIRouter(tags=["alerts"])

# B228: register alerts routes.
register_route("GET", "/api/alerts", "alerts.read")
register_route("GET", "/api/alerts/sources", "alerts.read")
register_route("POST", "/api/alerts", "alerts.write")
register_route("PUT", "/api/alerts/{alert_id}", "alerts.write")
register_route("DELETE", "/api/alerts/{alert_id}", "alerts.write")
register_route("POST", "/api/alerts/{alert_id}/test", "alerts.write")
register_route("GET", "/api/alerts/{alert_id}/sparkline", "alerts.read")


# ── Models ────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    name: str
    label: str
    description: str | None = None
    plugin_id: str
    dataset: str
    metric: str
    aggregation: str = "sum"
    condition_type: str = "threshold_drop"
    threshold: float | None = None
    compare_to: str = "7d_avg"
    scope: str = "all"
    group_by: str | None = None
    scope_filters: dict = {}
    check_frequency: str = "daily"
    check_period: str = "yesterday"
    cooldown_hours: int = 24
    min_baseline: float = 0
    notify_channels: list[str] = ["email"]
    enabled: bool = True
    is_template: bool = False


class AlertUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    enabled: bool | None = None
    threshold: float | None = None
    compare_to: str | None = None
    check_period: str | None = None
    group_by: str | None = None
    scope_filters: dict | None = None
    cooldown_hours: int | None = None
    min_baseline: float | None = None
    notify_channels: list[str] | None = None


# ── Frequency / period label helpers ──────────────────────────────────

_FREQUENCY_LABELS = {
    "hourly": "Runs every hour",
    "daily":  "Runs once a day",
    "weekly": "Runs once a week",
}

_PERIOD_LABELS = {
    "today":              "checks today's data",
    "yesterday":          "checks yesterday's data",
    "today_or_yesterday": "checks today or yesterday",
    "this_week":          "checks this week",
    "rolling_7d":         "checks the last 7 days",
}


def _serialize_alert(row: dict) -> dict:
    """Serialize a DB row for JSON response."""
    for k in ("created_at", "updated_at", "last_triggered"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()
    # Inject human-readable labels
    freq = row.get("check_frequency", "daily")
    period = row.get("check_period", "yesterday")
    row["frequency_label"] = _FREQUENCY_LABELS.get(freq, f"Runs {freq}")
    row["period_label"] = _PERIOD_LABELS.get(period, period)
    return row


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/alerts",
    operation_id="alerts.list",
    response_model=AlertsListResponse,
    response_model_exclude_none=True,
    summary="List alert configs (newest-first, optional plugin/enabled filter)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
    },
)
async def list_alerts(
    plugin_id: str | None = None,
    enabled_only: bool = False,
    _: None = Depends(requires("alerts.read")),
):
    """List all alerts, with human-readable frequency and period labels."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM alert_rules WHERE 1=1"
        params: list = []

        if plugin_id:
            sql += " AND plugin_id = %s"
            params.append(plugin_id)
        if enabled_only:
            sql += " AND enabled = true"

        sql += " ORDER BY created_at DESC"
        cur.execute(sql, params)
        alerts = rows_as_dicts(cur)

    for a in alerts:
        _serialize_alert(a)

    return {"alerts": alerts, "count": len(alerts)}


@router.get(
    "/alerts/sources",
    operation_id="alerts.sources",
    response_model=AlertSourcesResponse,
    response_model_exclude_none=True,
    summary="Available data sources for alert configuration (grouped by origin)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
    },
)
async def alert_sources(_: None = Depends(requires("alerts.read"))):
    """
    Return available data sources for alert configuration, grouped by origin:
    - postgres: Platform tables in the public schema (with columns + row counts)
    - plugin: Datasets declared in installed plugin manifests
    - connection: External data sources registered in the connections table
    """
    # v0.10.0.6.2 (Phase 12 §I3): replaced the per-plugin manifest walk and
    # the N+1 information_schema.columns query with the catalog cache +
    # one batched columns query. Cost dropped from ~2N file reads + (50+
    # round trips) to ~3 DB queries total.
    from .. import catalog as catalog_mod
    from .plugins import _load_plugin

    postgres_tables: list[dict] = []
    connections_list: list[dict] = []
    plugin_datasets: list[dict] = []

    # Plugin → owned tables, from the mtime-cached catalog map.
    ownership_map = catalog_mod._build_plugin_ownership_map()  # {table: plugin_id}, cached
    # Build the legacy {table: (plugin_id, display_name)} shape the
    # rendering loop below expects.
    plugin_table_owner: dict[str, tuple[str, str]] = {}
    plugin_display_names: dict[str, str] = {}
    for tname, pid in ownership_map.items():
        if pid not in plugin_display_names:
            try:
                data = _load_plugin(pid, installed_only=True) or {}
                plugin_display_names[pid] = data.get("display_name") or pid
            except Exception:
                plugin_display_names[pid] = pid
        plugin_table_owner[tname] = (pid, plugin_display_names[pid])

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # ONE query for table list + row estimates.
            cur.execute("""
                SELECT t.table_name,
                       COALESCE(pg_stat_user_tables.n_live_tup, 0) AS row_estimate
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables
                       ON pg_stat_user_tables.relname = t.table_name
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
            """)
            table_rows = cur.fetchall()
            all_table_names = [r[0] for r in table_rows]

            # ONE batched query for column metadata across every table.
            columns_by_table: dict[str, list[dict]] = {}
            if all_table_names:
                cur.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = ANY(%s)
                    ORDER BY table_name, ordinal_position
                """, (all_table_names,))
                for tname, col_name, col_type in cur.fetchall():
                    columns_by_table.setdefault(tname, []).append({
                        "name": col_name, "type": col_type,
                    })

            for (tname, row_estimate) in table_rows:
                owner = plugin_table_owner.get(tname)
                postgres_tables.append({
                    "id": f"pg:{tname}",
                    "label": tname,
                    "source_type": "plugin_postgres" if owner else "postgres",
                    "source_label": owner[1] if owner else "PostgreSQL",
                    "plugin_id": owner[0] if owner else None,
                    "table": tname,
                    "row_estimate": int(row_estimate or 0),
                    "columns": columns_by_table.get(tname, []),
                })

            try:
                cur.execute("""
                    SELECT id, plugin_id, name, connection_type, status,
                           last_successful_sync, last_error
                    FROM connections ORDER BY created_at
                """)
                for row in cur.fetchall():
                    connections_list.append({
                        "id": f"conn:{row[0]}",
                        "connection_id": str(row[0]),
                        "plugin_id": row[1],
                        "label": row[2],
                        "connection_type": row[3],
                        "status": row[4],
                        "last_sync": row[5].isoformat() if row[5] else None,
                        "last_error": row[6],
                        "source_type": "connection",
                        "source_label": row[2],
                        "columns": [],
                    })
            except Exception:
                conn.rollback()

    except Exception as e:
        logger.warning(f"Could not fetch alert sources: {e}")

    # v0.10.0.6.2: plugin_datasets reads the same manifests via the
    # catalog cache (manifest.datasets[] doesn't appear in the ownership
    # map, so we still need _load_plugin for the dataset declarations —
    # but those reads are also mtime-cached via the ownership map's
    # underlying _load_plugin caching).
    plugin_ids = set(plugin_display_names.keys())
    for plugin_id in plugin_ids:
        try:
            manifest = _load_plugin(plugin_id, installed_only=True)
            if not manifest:
                continue
            plugin_label = plugin_display_names.get(plugin_id, plugin_id)
            for ds in manifest.get("datasets", []):
                ds_name = ds.get("name") or ds.get("table", "")
                columns = [
                    {"name": fld.get("name", ""), "type": fld.get("type", "unknown")}
                    for fld in ds.get("fields", [])
                ]
                plugin_datasets.append({
                    "id": f"plugin:{plugin_id}:{ds_name}",
                    "label": ds.get("label") or ds_name,
                    "source_type": "plugin",
                    "source_label": plugin_label,
                    "plugin_id": plugin_id,
                    "table": ds_name,
                    "columns": columns,
                })
        except Exception as e:
            logger.warning(f"Could not read manifest for {plugin_id}: {e}")

    pg_table_names = {t["table"] for t in postgres_tables}
    plugin_datasets_deduped = [ds for ds in plugin_datasets if ds["table"] not in pg_table_names]

    return {
        "postgres": postgres_tables,
        "connections": connections_list,
        "plugins": plugin_datasets_deduped,
    }


@router.post(
    "/alerts",
    operation_id="alerts.create",
    response_model=AlertRow,
    response_model_exclude_none=True,
    summary="Create an alert rule",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.write permission."},
    },
)
async def create_alert(
    req: AlertCreate,
    request: Request,
    _: None = Depends(requires("alerts.write")),
):
    """Create a new alert."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alert_rules (
                name, label, description, plugin_id, dataset,
                metric, aggregation, condition_type, threshold, compare_to,
                scope, group_by, scope_filters, check_frequency, check_period,
                cooldown_hours, min_baseline, notify_channels, enabled, is_template
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) RETURNING *
        """, (
            req.name, req.label, req.description, req.plugin_id, req.dataset,
            req.metric, req.aggregation, req.condition_type, req.threshold, req.compare_to,
            req.scope, req.group_by, json.dumps(req.scope_filters), req.check_frequency, req.check_period,
            req.cooldown_hours, req.min_baseline, req.notify_channels, req.enabled, req.is_template,
        ))
        row = rows_as_dicts(cur)[0]

    logger.info(f"Alert created: {req.label}")
    return _serialize_alert(row)


@router.put(
    "/alerts/{alert_id}",
    operation_id="alerts.update",
    response_model=AlertRow,
    response_model_exclude_none=True,
    summary="Patch an alert (partial — null fields skipped)",
    responses={
        400: {"model": ErrorDetail, "description": "Empty body."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.write permission."},
        404: {"model": ErrorDetail, "description": "Alert not found."},
    },
)
async def update_alert(
    alert_id: str,
    req: AlertUpdate,
    request: Request,
    _: None = Depends(requires("alerts.write")),
):
    """Update an alert (toggle, change threshold, etc.)."""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")

    # Serialize scope_filters to JSON string for Postgres
    if "scope_filters" in updates:
        updates["scope_filters"] = json.dumps(updates["scope_filters"])
    if "notify_channels" in updates:
        updates["notify_channels"] = updates["notify_channels"]  # TEXT[] handled by psycopg2

    updates["updated_at"] = datetime.now(timezone.utc)
    set_parts = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [alert_id]

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE alert_rules SET {set_parts} WHERE id = %s RETURNING *", values)
        rows = rows_as_dicts(cur)

    if not rows:
        raise HTTPException(404, "Alert not found")
    return _serialize_alert(rows[0])


@router.delete(
    "/alerts/{alert_id}",
    operation_id="alerts.delete",
    response_model=AlertDeleteResponse,
    summary="Delete an alert",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.write permission."},
        404: {"model": ErrorDetail, "description": "Alert not found."},
    },
)
async def delete_alert(
    alert_id: str,
    request: Request,
    _: None = Depends(requires("alerts.write")),
):
    """Delete a custom alert."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM alert_rules WHERE id = %s RETURNING id", (alert_id,))
        deleted = cur.fetchone()

    if not deleted:
        raise HTTPException(404, "Alert not found")
    return {"status": "deleted"}


@router.post(
    "/alerts/{alert_id}/test",
    operation_id="alerts.test",
    response_model=AlertTestResponse,
    response_model_exclude_none=True,
    summary="Dry-run an alert against current data",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.write permission."},
        404: {"model": ErrorDetail, "description": "Alert not found."},
    },
)
async def test_alert(
    alert_id: str,
    request: Request,
    _: None = Depends(requires("alerts.write")),
):
    """Test-run an alert against current data without triggering notifications.

    Imports the worker's evaluator at request time. If the worker module
    isn't importable on this server, returns `{error: ...}` instead of
    a fired/checked breakdown.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alert_rules WHERE id = %s", (alert_id,))
        rows = rows_as_dicts(cur)

    if not rows:
        raise HTTPException(404, "Alert not found")
    alert = rows[0]

    # Run the alert check in dry-run mode (no notifications, no recording)
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
        from apps.worker.src.run_alerts import build_check_sql, evaluate_row, query_postgres
        import psycopg2

        pg = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "nousviz"),
            user=os.environ.get("POSTGRES_USER", "nousviz"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
        )
        pg.autocommit = True

        sql, params = build_check_sql(alert)
        rows_data = query_postgres(pg, sql, params)
        pg.close()

        if not rows_data:
            return {"alert_id": alert_id, "fired": False, "message": "No data returned for this alert's query.", "rows_checked": 0}

        triggered = []
        for row in rows_data:
            result = evaluate_row(alert, row)
            if result:
                triggered.append(result)

        return {
            "alert_id": alert_id,
            "fired": len(triggered) > 0,
            "message": f"Would fire on {len(triggered)} of {len(rows_data)} rows" if triggered else "Would not fire — all values within threshold",
            "rows_checked": len(rows_data),
            "triggered_rows": triggered[:5],
        }
    except ImportError:
        return {"alert_id": alert_id, "error": "Alert worker module not available on this server."}
    except Exception as e:
        logger.error(f"Alert test failed: {e}", exc_info=True)
        return {"alert_id": alert_id, "error": "Test failed. Check server logs for details."}


# ── Alert sparkline ────────────────────────────────────────────────────

@router.get(
    "/alerts/{alert_id}/sparkline",
    operation_id="alerts.sparkline",
    response_model=AlertSparklineResponse,
    response_model_exclude_none=True,
    summary="Per-day trigger counts + semantic-score sparkline",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
        404: {"model": ErrorDetail, "description": "Alert not found."},
    },
)
async def alert_sparkline(
    alert_id: str,
    days: int = 30,
    _: None = Depends(requires("alerts.read")),
):
    """Return per-day trigger counts + dominant semantic score for the last N days."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alert_rules WHERE id = %s", (alert_id,))
        rows = rows_as_dicts(cur)

    if not rows:
        raise HTTPException(404, "Alert not found")
    alert = rows[0]

    frequency = alert.get("check_frequency", "daily")
    check_period = alert.get("check_period", "yesterday")

    today = datetime.now(timezone.utc).date()
    date_range = [(today - timedelta(days=days - 1 - i)) for i in range(days)]
    buckets = {d.isoformat(): {"date": d.isoformat(), "count": 0, "scores": []} for d in date_range}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT triggered_at::date AS day, COUNT(*) AS cnt, semantic_score
                FROM alert_triggers
                WHERE alert_id = %s AND triggered_at >= %s
                GROUP BY day, semantic_score
                ORDER BY day
            """, (alert_id, cutoff))
            trigger_rows = cur.fetchall()
    except Exception:
        trigger_rows = []

    for row in trigger_rows:
        day_str = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        cnt = int(row[1])
        score = row[2]
        if day_str in buckets:
            buckets[day_str]["count"] += cnt
            if score:
                buckets[day_str]["scores"].extend([score] * cnt)

    def dominant(scores: list[str]) -> str | None:
        if not scores:
            return None
        for s in ("useful", "neutral", "useless"):
            if scores.count(s) >= len(scores) / 2:
                return s
        return scores[0]

    day_list = []
    semantic_summary = {"useful": 0, "neutral": 0, "useless": 0}
    total = 0
    for d in date_range:
        b = buckets[d.isoformat()]
        score = dominant(b["scores"])
        day_list.append({"date": b["date"], "count": b["count"], "score": score})
        total += b["count"]
        if score:
            semantic_summary[score] = semantic_summary.get(score, 0) + b["count"]

    return {
        "alert_id": alert_id,
        "alert_label": alert["label"],
        "check_frequency": frequency,
        "frequency_label": _FREQUENCY_LABELS.get(frequency, f"Runs {frequency}"),
        "check_period": check_period,
        "period_label": _PERIOD_LABELS.get(check_period, check_period),
        "cooldown_hours": alert.get("cooldown_hours", 24),
        "days": day_list,
        "total_triggers": total,
        "semantic_summary": semantic_summary,
    }
