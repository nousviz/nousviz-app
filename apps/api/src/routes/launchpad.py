"""
/api/launchpad — Aggregated overview data for the operator's daily landing page.

Single endpoint that returns everything the launchpad needs in one call:
health status, recent activity, recent plugin data changes, alerts summary,
and system-level needs-attention items. Saves the frontend from making
6+ parallel requests on every page load.

v0.10.0.6.2 (Phase 12 §I5): per-plugin row counts now use
`pg_class.reltuples` row estimates batched into one query instead of
N×5 unbounded `count(*)` calls. Plugin manifest reads consume the
mtime-aware catalog cache (Keystone A) shipped in v0.10.0.5.6.
Module-level 30s response cache absorbs the 60s polling cadence from
the Overview page.
"""
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from ..db import get_pg_conn, rows_as_dicts
from .plugins import _installed_slugs, _load_plugin  # B226 + v0.10.0.6.2
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.launchpad import LaunchpadResponse

logger = logging.getLogger("nousviz.launchpad")

router = APIRouter(prefix="/api/launchpad", tags=["launchpad"])

# ── Response cache (v0.10.0.6.2) ──────────────────────────────────────
# The Overview page polls /api/launchpad every 60s. Cache the response
# for 30s so back-to-back requests within one polling cycle are served
# from memory. Cache is shared across all requests (no per-user data in
# the response — it's system-level aggregates).
_LAUNCHPAD_CACHE_TTL_SEC = 30.0
_launchpad_cache: dict = {"data": None, "expires_at": 0.0}
_launchpad_cache_lock = threading.Lock()


def _get_cached_response():
    """Return cached response if still fresh, else None."""
    with _launchpad_cache_lock:
        if _launchpad_cache["data"] is not None and time.monotonic() < _launchpad_cache["expires_at"]:
            return _launchpad_cache["data"]
        return None


def _set_cached_response(data):
    with _launchpad_cache_lock:
        _launchpad_cache["data"] = data
        _launchpad_cache["expires_at"] = time.monotonic() + _LAUNCHPAD_CACHE_TTL_SEC


def invalidate_launchpad_cache():
    """Explicit cache invalidation. Called from tests and (optionally)
    from plugin install/uninstall handlers if they want immediate refresh."""
    with _launchpad_cache_lock:
        _launchpad_cache["data"] = None
        _launchpad_cache["expires_at"] = 0.0


def _build_plugin_tables_map() -> dict[str, list[str]]:
    """Return ``{plugin_id: [table_names]}`` for every installed plugin.

    Reads from the catalog cache shipped in v0.10.0.5.6 — the underlying
    `_build_plugin_ownership_map()` is mtime-aware and invalidates when
    plugin.yaml files change. Free between requests.
    """
    from .. import catalog as catalog_mod
    ownership = catalog_mod._build_plugin_ownership_map()  # cached
    out: dict[str, list[str]] = {}
    for table, plugin_id in ownership.items():
        out.setdefault(plugin_id, []).append(table)
    return out


def _build_plugin_display_names(plugin_ids: list[str]) -> dict[str, str]:
    """Return ``{plugin_id: display_name}`` via the catalog's manifest
    cache. Falls back to the plugin_id when display_name is unset."""
    out: dict[str, str] = {}
    for pid in plugin_ids:
        try:
            data = _load_plugin(pid, installed_only=True) or {}
            out[pid] = data.get("display_name") or pid
        except Exception:
            out[pid] = pid
    return out

# B228: register launchpad routes (silent-leak fix).
register_route("GET", "/api/launchpad", "dashboards.read")


@router.get(
    "",
    operation_id="launchpad.feed",
    response_model=LaunchpadResponse,
    response_model_exclude_none=True,
    summary="Single-call aggregate data feed for the Overview page",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.read permission."},
    },
)
async def launchpad(_: None = Depends(requires("dashboards.read"))):
    """Single-call data feed for the Overview page.

    Each block is fetched in its own savepoint — failures roll back
    that block only and leave the rest of the response intact. The
    frontend receives partial data rather than a 500 when one of the
    underlying queries hits a missing table or stale schema.

    Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
    so the cache absorbs back-to-back requests without staleness anyone
    notices.
    """
    cached = _get_cached_response()
    if cached is not None:
        return cached

    result: dict = {
        "recent_activity": [],
        "recent_data_changes": [],
        "alerts_summary": {"total": 0, "enabled": 0, "triggered_24h": 0, "recent_triggers": []},
        "health_snapshot": None,
        "needs_attention": [],
        "stats": {},
    }

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # ── Recent activity (last 20 non-page-view events) ────────
            try:
                cur.execute("""
                    SELECT a.action, a.page_path, a.plugin_id, a.detail AS details, a.ip_address,
                           to_char(a.created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
                           u.name AS user_name
                    FROM activity_events a
                    LEFT JOIN users u ON u.id = a.user_id
                    WHERE a.action != 'page_view'
                    ORDER BY a.created_at DESC
                    LIMIT 20
                """)
                result["recent_activity"] = rows_as_dicts(cur)
            except Exception:
                conn.rollback()

            # ── Recent plugin data changes (last sync times + row counts) ──
            # Union of job_runs (new contract) and plugin_settings._last_sync
            # (legacy contract) so plugins that haven't migrated still appear.
            try:
                cur.execute("""
                    WITH jr AS (
                        SELECT split_part(job_id, ':', 2) AS plugin_id,
                               MAX(completed_at)::text AS last_sync
                        FROM job_runs
                        WHERE job_id LIKE 'sync:%'
                          AND status = 'success'
                          AND completed_at IS NOT NULL
                        GROUP BY job_id
                    ),
                    leg AS (
                        SELECT plugin_id,
                               (value->>'timestamp')::text AS last_sync
                        FROM plugin_settings
                        WHERE key = '_last_sync'
                          AND value->>'timestamp' IS NOT NULL
                    ),
                    merged AS (
                        SELECT plugin_id, last_sync FROM jr
                        UNION ALL
                        SELECT plugin_id, last_sync FROM leg
                    )
                    SELECT plugin_id, MAX(last_sync) AS last_sync
                    FROM merged
                    GROUP BY plugin_id
                    ORDER BY MAX(last_sync) DESC NULLS LAST
                    LIMIT 10
                """)
                syncs = rows_as_dicts(cur)

                # v0.10.0.6.2 — batched approach replaces the per-plugin
                # manifest-walk + N×5 count(*) loop:
                #   1. Catalog cache supplies plugin → table list (free).
                #   2. ONE pg_class.reltuples query covers every plugin's
                #      tables across all top-10-recent plugins.
                #   3. Display names fetched from the catalog manifest cache.
                # Cost dropped from ~50 unbounded count(*) on shared conn
                # to ~3 indexed catalog reads + 1 pg_class scan.
                plugin_ids_with_syncs = [s.get("plugin_id") for s in syncs if s.get("plugin_id")]
                plugin_tables_map = _build_plugin_tables_map()
                display_names = _build_plugin_display_names(plugin_ids_with_syncs)

                # Flat list of every table we need a row estimate for,
                # capped to 5 tables per plugin to match the original behaviour.
                all_tables: list[str] = []
                table_to_plugin: dict[str, str] = {}
                for pid in plugin_ids_with_syncs:
                    tables = plugin_tables_map.get(pid, [])[:5]
                    for t in tables:
                        all_tables.append(t)
                        table_to_plugin[t] = pid

                # One batched query for ALL row estimates.
                row_estimates: dict[str, int] = {}
                if all_tables:
                    try:
                        cur.execute("""
                            SELECT c.relname, GREATEST(c.reltuples::bigint, 0) AS est
                            FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'public'
                              AND c.relname = ANY(%s)
                              AND c.relkind IN ('r', 'p')
                        """, (all_tables,))
                        for row in cur.fetchall():
                            row_estimates[row[0]] = int(row[1])
                    except Exception:
                        conn.rollback()

                # Aggregate per plugin
                per_plugin_totals: dict[str, dict[str, int]] = {}
                for pid in plugin_ids_with_syncs:
                    tables = plugin_tables_map.get(pid, [])[:5]
                    per_plugin_totals[pid] = {
                        "total_rows": sum(row_estimates.get(t, 0) for t in tables),
                        "tables": len(plugin_tables_map.get(pid, [])),
                    }

                changes = []
                for s in syncs:
                    pid = s.get("plugin_id")
                    if not pid:
                        continue
                    totals = per_plugin_totals.get(pid, {})
                    changes.append({
                        "plugin_id": pid,
                        "display_name": display_names.get(pid, pid),
                        "last_sync": s.get("last_sync"),
                        "total_rows": totals.get("total_rows", 0),
                        "tables": totals.get("tables", 0),
                    })
                result["recent_data_changes"] = changes
            except Exception:
                conn.rollback()

            # ── Alerts summary ────────────────────────────────────────
            try:
                cur.execute("SELECT count(*) FROM alert_rules")
                total = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM alert_rules WHERE enabled = true")
                enabled = cur.fetchone()[0]
                cur.execute("""
                    SELECT count(*) FROM alert_triggers
                    WHERE triggered_at > now() - interval '24 hours'
                """)
                triggered_24h = cur.fetchone()[0]

                recent_triggers = []
                try:
                    cur.execute("""
                        SELECT alert_name, plugin_id,
                               to_char(triggered_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS triggered_at
                        FROM alert_triggers
                        ORDER BY triggered_at DESC
                        LIMIT 5
                    """)
                    recent_triggers = rows_as_dicts(cur)
                except Exception:
                    conn.rollback()

                result["alerts_summary"] = {
                    "total": total,
                    "enabled": enabled,
                    "triggered_24h": triggered_24h,
                    "recent_triggers": recent_triggers,
                }
            except Exception:
                conn.rollback()

            # ── Latest health snapshot ────────────────────────────────
            try:
                cur.execute("""
                    SELECT level, checks, version,
                           to_char(created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at
                    FROM health_log
                    ORDER BY id DESC
                    LIMIT 1
                """)
                rows = rows_as_dicts(cur)
                if rows:
                    result["health_snapshot"] = rows[0]
            except Exception:
                conn.rollback()

            # ── Needs-attention items ─────────────────────────────────
            attention: list[dict] = []

            # Overdue plugin syncs (2x schedule threshold)
            # Union as above so legacy _last_sync plugins are checked too.
            # B226: filter to currently-installed plugins. Without this,
            # rows in job_runs / plugin_settings._last_sync that survive
            # plugin uninstall produce "X sync hasn't run" warnings forever
            # (e.g. hello-nousviz, scrubbed in v0.9.5.5).
            try:
                try:
                    installed = _installed_slugs()
                except Exception:
                    installed = set()  # fail-open: behave like pre-B226 if filesystem read fails
                cur.execute("""
                    WITH jr AS (
                        SELECT split_part(job_id, ':', 2) AS plugin_id,
                               MAX(completed_at)::text AS last_sync
                        FROM job_runs
                        WHERE job_id LIKE 'sync:%'
                          AND status = 'success'
                          AND completed_at IS NOT NULL
                        GROUP BY job_id
                    ),
                    leg AS (
                        SELECT plugin_id,
                               (value->>'timestamp')::text AS last_sync
                        FROM plugin_settings
                        WHERE key = '_last_sync'
                          AND value->>'timestamp' IS NOT NULL
                    ),
                    merged AS (
                        SELECT plugin_id, last_sync FROM jr
                        UNION ALL
                        SELECT plugin_id, last_sync FROM leg
                    )
                    SELECT plugin_id, MAX(last_sync) AS last_sync
                    FROM merged
                    GROUP BY plugin_id
                """)
                for row in rows_as_dicts(cur):
                    plugin_id = row.get("plugin_id")
                    if not plugin_id or (installed and plugin_id not in installed):
                        continue
                    ts = row.get("last_sync")
                    if not ts:
                        continue
                    try:
                        last = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                        if last.tzinfo is None:
                            last = last.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) - last > timedelta(hours=8):
                            attention.append({
                                "type": "overdue_sync",
                                "severity": "warning",
                                "message": f"{plugin_id} sync hasn't run in over 8 hours",
                                "plugin_id": plugin_id,
                                "last_sync": ts,
                            })
                    except Exception:
                        pass
            except Exception:
                conn.rollback()

            # Shares expiring soon (within 24h)
            try:
                cur.execute("""
                    SELECT share_id, title, expires_at
                    FROM shared_links
                    WHERE revoked = false
                      AND expires_at BETWEEN now() AND now() + interval '24 hours'
                    ORDER BY expires_at
                    LIMIT 5
                """)
                for row in rows_as_dicts(cur):
                    exp = row.get("expires_at")
                    if exp and hasattr(exp, "isoformat"):
                        exp = exp.isoformat()
                    attention.append({
                        "type": "share_expiring",
                        "severity": "info",
                        "message": f"Share '{row.get('title', '')}' expires soon",
                        "share_id": row.get("share_id"),
                        "expires_at": exp,
                    })
            except Exception:
                conn.rollback()

            result["needs_attention"] = attention

            # ── Quick stats ───────────────────────────────────────────
            try:
                cur.execute("""
                    SELECT
                        (SELECT count(*) FROM annotations WHERE archived = false) AS annotations,
                        (SELECT count(*) FROM shared_links WHERE revoked = false AND expires_at > now()) AS active_shares
                """)
                stats_row = rows_as_dicts(cur)
                if stats_row:
                    result["stats"] = stats_row[0]
            except Exception:
                conn.rollback()

    except Exception as e:
        logger.error(f"Launchpad data fetch failed: {e}")

    _set_cached_response(result)
    return result
