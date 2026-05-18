"""
B271 (v0.9.11.13) — Postgres-level resource metrics for /api/system/resources.

Pure SQL — no shell. Reuses the existing `get_pg_conn()` and the
plugin-ownership map from `catalog.py` so per-plugin attribution
matches what the Datasets page shows.

Design constraints:
- Cap result sets (top 50 tables, top 20 indexes) — these populate UI panels
- Single connection across all queries (cheap, fewer round trips)
- Tolerant of missing extensions (pg_stat_statements may not be installed)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional

from ..db import get_pg_conn
from ..catalog import _build_plugin_ownership_map

logger = logging.getLogger("nousviz.services.postgres_resources")


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass
class DatabaseSummary:
    db_size_mb: int
    cache_hit_pct: float
    active_connections: int
    idle_connections: int
    max_connections: int
    pg_stat_statements_installed: bool


@dataclass
class TableStat:
    schema: str
    name: str
    plugin: Optional[str]  # plugin slug, or None for host-owned
    total_size_mb: float
    data_mb: float
    index_mb: float
    rows: int
    dead_rows: int
    dead_pct: float
    last_vacuum: Optional[str]   # ISO timestamp or None
    last_analyze: Optional[str]
    seq_scan_count: int
    idx_scan_count: int
    seq_scan_pct: float


@dataclass
class PluginStat:
    id: str  # plugin slug or "<host>" for host-owned
    table_count: int
    total_size_mb: float
    total_rows: int
    last_sync_at: Optional[str]
    sync_schedule_cron: Optional[str]


@dataclass
class SyncStat:
    plugin_id: str
    schedule_cron: str
    schedule_interval_seconds: int
    runs_24h: int
    errors_24h: int
    avg_duration_ms: Optional[int]
    max_duration_ms: Optional[int]
    cpu_load_pct_estimate: float  # capped at 100


@dataclass
class IndexStat:
    schema: str
    table: str
    name: str
    size_mb: float
    scans_lifetime: int
    tuples_read: int
    # B272 v0.9.11.19.3: is_primary + is_unique drive unused_index rule
    # filtering. PKs and unique indexes are load-bearing for constraint
    # enforcement and FK lookups even when no SELECT scans probe them,
    # so they shouldn't be flagged as droppable just because
    # pg_stat_user_indexes.idx_scan = 0.
    is_primary: bool = False
    is_unique: bool = False


# ── Helpers ──────────────────────────────────────────────────────────


def _bytes_to_mb(b: Optional[int]) -> float:
    """Bytes → MB rounded to 1 decimal."""
    if b is None:
        return 0.0
    return round(b / (1024 ** 2), 1)


def _ts_to_iso(ts) -> Optional[str]:
    """psycopg2 timestamp → ISO string. None passes through."""
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def _cron_to_interval_seconds(cron: str) -> int:
    """Best-effort cron → seconds-between-fires for the cpu_load math.
    Handles the common cases used in nousviz manifests; falls back to
    24 hours for anything else (conservative — under-counts CPU usage)."""
    if not cron:
        return 86400
    cron = cron.strip()
    # Hourly: "0 * * * *"
    if cron == "0 * * * *":
        return 3600
    # Every N minutes: "*/N * * * *"
    if cron.startswith("*/") and " * * * *" in cron:
        try:
            n = int(cron.split()[0][2:])
            return max(60, n * 60)
        except (ValueError, IndexError):
            pass
    # Every N hours: "0 */N * * *"
    if cron.startswith("0 */") and cron.endswith(" * * *"):
        try:
            n = int(cron.split()[1][2:])
            return max(3600, n * 3600)
        except (ValueError, IndexError):
            pass
    # Daily at fixed hour: "0 N * * *"
    parts = cron.split()
    if len(parts) == 5 and parts[0] == "0" and parts[2] == "*" and parts[3] == "*" and parts[4] == "*":
        try:
            int(parts[1])  # hour
            return 86400
        except ValueError:
            pass
    return 86400


# ── Collectors ───────────────────────────────────────────────────────


def get_database_summary() -> DatabaseSummary:
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT pg_database_size('nousviz')")
        db_bytes = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT
              sum(heap_blks_read), sum(heap_blks_hit)
            FROM pg_statio_user_tables
        """)
        reads, hits = cur.fetchone() or (0, 0)
        reads = reads or 0
        hits = hits or 0
        cache_hit_pct = round(hits / max(1, hits + reads) * 100, 2)

        cur.execute("""
            SELECT state, count(*) FROM pg_stat_activity
            WHERE datname = 'nousviz' GROUP BY state
        """)
        states = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SHOW max_connections")
        max_conn = int(cur.fetchone()[0])

        cur.execute("""
            SELECT EXISTS (
              SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            )
        """)
        pgss_installed = bool(cur.fetchone()[0])

    return DatabaseSummary(
        db_size_mb=int(db_bytes // (1024 ** 2)),
        cache_hit_pct=cache_hit_pct,
        active_connections=states.get("active", 0),
        idle_connections=states.get("idle", 0),
        max_connections=max_conn,
        pg_stat_statements_installed=pgss_installed,
    )


def get_top_tables(limit: int = 50) -> list[TableStat]:
    """Top tables by total relation size, with plugin attribution + vacuum
    + scan-ratio metrics."""
    ownership = _build_plugin_ownership_map()  # {table_name: plugin_id}

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
              n.nspname AS schema,
              c.relname AS name,
              pg_total_relation_size(c.oid) AS total_bytes,
              pg_relation_size(c.oid) AS data_bytes,
              pg_indexes_size(c.oid) AS index_bytes,
              COALESCE(s.n_live_tup, 0) AS rows,
              COALESCE(s.n_dead_tup, 0) AS dead_rows,
              s.last_vacuum,
              s.last_autovacuum,
              s.last_analyze,
              s.last_autoanalyze,
              COALESCE(s.seq_scan, 0) AS seq_scan,
              COALESCE(s.idx_scan, 0) AS idx_scan
            FROM pg_class c
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_stat_user_tables s
              ON s.schemaname = n.nspname AND s.relname = c.relname
            WHERE c.relkind = 'r'
              AND n.nspname IN ('public', 'fusions')
            ORDER BY pg_total_relation_size(c.oid) DESC
            LIMIT %s
        """, (limit,))

        rows: list[TableStat] = []
        for r in cur.fetchall():
            (schema, name, total_b, data_b, idx_b, n_rows, dead, lv, lav, la, laa, ssc, isc) = r
            total_scans = (ssc or 0) + (isc or 0)
            seq_pct = round((ssc or 0) / max(1, total_scans) * 100, 1) if total_scans else 0.0
            dead_pct = round((dead or 0) / max(1, (n_rows or 0) + (dead or 0)) * 100, 1)
            rows.append(TableStat(
                schema=schema,
                name=name,
                plugin=ownership.get(name),
                total_size_mb=_bytes_to_mb(total_b),
                data_mb=_bytes_to_mb(data_b),
                index_mb=_bytes_to_mb(idx_b),
                rows=int(n_rows or 0),
                dead_rows=int(dead or 0),
                dead_pct=dead_pct,
                last_vacuum=_ts_to_iso(lv) or _ts_to_iso(lav),
                last_analyze=_ts_to_iso(la) or _ts_to_iso(laa),
                seq_scan_count=int(ssc or 0),
                idx_scan_count=int(isc or 0),
                seq_scan_pct=seq_pct,
            ))
    return rows


def get_per_plugin_summary() -> list[PluginStat]:
    """Aggregate table sizes + sync schedule per plugin. Tables not
    claimed by any manifest go under id='<host>'."""
    ownership = _build_plugin_ownership_map()
    tables = get_top_tables(limit=500)  # most installs have < 200 tables

    by_plugin: dict[str, list[TableStat]] = {}
    for t in tables:
        key = t.plugin or "<host>"
        by_plugin.setdefault(key, []).append(t)

    # Pull sync schedules in one query
    schedules: dict[str, dict] = {}
    with get_pg_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT plugin_id, cron_expression, last_enqueued_at
                FROM sync_schedule_registry
            """)
            for plugin_id, cron, last_at in cur.fetchall():
                schedules[plugin_id] = {
                    "cron": cron,
                    "last_at": _ts_to_iso(last_at),
                }
        except Exception as exc:
            logger.warning(f"postgres_resources: sync_schedule_registry read failed — {exc}")

    out: list[PluginStat] = []
    for plugin_id, plugin_tables in by_plugin.items():
        total_size = sum(t.total_size_mb for t in plugin_tables)
        total_rows = sum(t.rows for t in plugin_tables)
        sched = schedules.get(plugin_id, {})
        out.append(PluginStat(
            id=plugin_id,
            table_count=len(plugin_tables),
            total_size_mb=round(total_size, 1),
            total_rows=total_rows,
            last_sync_at=sched.get("last_at"),
            sync_schedule_cron=sched.get("cron"),
        ))
    out.sort(key=lambda p: p.total_size_mb, reverse=True)
    return out


def get_sync_summary() -> list[SyncStat]:
    """Per sync: schedule + 24h activity + cpu_load_pct_estimate.

    cpu_load_pct_estimate = (avg_duration_ms × runs_24h) / 86_400_000 × 100
    Capped at 100. This is "% of one CPU continuously consumed by this sync"
    — the audit's headline metric.
    """
    out: list[SyncStat] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                WITH agg AS (
                  SELECT
                    SUBSTRING(job_id FROM 'sync:(.*)$') AS plugin_id,
                    job_id,
                    COUNT(*) AS runs,
                    COUNT(*) FILTER (WHERE status = 'error') AS errors,
                    AVG(duration_ms)::INT AS avg_ms,
                    MAX(duration_ms)::INT AS max_ms
                  FROM job_runs
                  WHERE started_at > now() - interval '24 hours'
                    AND job_id LIKE 'sync:%%'
                  GROUP BY job_id
                )
                SELECT
                  COALESCE(agg.plugin_id, ssr.plugin_id) AS plugin_id,
                  ssr.cron_expression,
                  COALESCE(agg.runs, 0),
                  COALESCE(agg.errors, 0),
                  agg.avg_ms,
                  agg.max_ms
                FROM sync_schedule_registry ssr
                FULL OUTER JOIN agg ON agg.plugin_id = ssr.plugin_id
                ORDER BY plugin_id
            """)
            for plugin_id, cron, runs, errors, avg_ms, max_ms in cur.fetchall():
                interval_s = _cron_to_interval_seconds(cron or "")
                if avg_ms and runs > 0:
                    load_pct = round(min(100.0, (avg_ms * runs) / 86_400_000 * 100), 1)
                else:
                    load_pct = 0.0
                out.append(SyncStat(
                    plugin_id=plugin_id or "(unknown)",
                    schedule_cron=cron or "",
                    schedule_interval_seconds=interval_s,
                    runs_24h=int(runs or 0),
                    errors_24h=int(errors or 0),
                    avg_duration_ms=int(avg_ms) if avg_ms is not None else None,
                    max_duration_ms=int(max_ms) if max_ms is not None else None,
                    cpu_load_pct_estimate=load_pct,
                ))
        except Exception as exc:
            logger.warning(f"postgres_resources: sync summary failed — {exc}")
    out.sort(key=lambda s: s.cpu_load_pct_estimate, reverse=True)
    return out


def get_largest_indexes(limit: int = 20) -> list[IndexStat]:
    out: list[IndexStat] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
              n.nspname AS schema,
              t.relname AS table_name,
              c.relname AS index_name,
              pg_relation_size(c.oid) AS size_bytes,
              COALESCE(s.idx_scan, 0) AS scans,
              COALESCE(s.idx_tup_read, 0) AS tuples_read,
              i.indisprimary AS is_primary,
              i.indisunique AS is_unique
            FROM pg_class c
            JOIN pg_index i ON i.indexrelid = c.oid
            JOIN pg_class t ON t.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = c.oid
            WHERE n.nspname IN ('public', 'fusions')
              AND c.relkind = 'i'
            ORDER BY pg_relation_size(c.oid) DESC
            LIMIT %s
        """, (limit,))
        for row in cur.fetchall():
            (schema, table, name, size_b, scans, reads,
             is_primary, is_unique) = row
            out.append(IndexStat(
                schema=schema,
                table=table,
                name=name,
                size_mb=_bytes_to_mb(size_b),
                scans_lifetime=int(scans or 0),
                tuples_read=int(reads or 0),
                is_primary=bool(is_primary),
                is_unique=bool(is_unique),
            ))
    return out


def get_all() -> dict:
    """One-call collection. Returns dict-shaped (not dataclass) for direct
    JSON serialization through FastAPI."""
    return {
        "postgres": asdict(get_database_summary()),
        "tables": [asdict(t) for t in get_top_tables(limit=50)],
        "plugins": [asdict(p) for p in get_per_plugin_summary()],
        "syncs": [asdict(s) for s in get_sync_summary()],
        "indexes_largest": [asdict(i) for i in get_largest_indexes(limit=20)],
    }
