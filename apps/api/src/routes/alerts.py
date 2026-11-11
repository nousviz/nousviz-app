"""
/api/alerts — Alert management

Handles pre-built plugin alerts (toggle on/off with config) and
custom user-created alerts.

Storage: Postgres `alert_rules` table (migration 025).
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..db import get_pg_conn, rows_as_dicts
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.alerts import (
    AlertDeleteResponse,
    AlertPreviewResponse,
    AlertRow,
    AlertSourceColumnsResponse,
    AlertSourcesResponse,
    AlertSourceTablesResponse,
    AlertSourceValuesResponse,
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
# P230: column mapping and preview.
register_route("GET", "/api/alerts/sources/columns", "alerts.read")
register_route("GET", "/api/alerts/sources/tables", "alerts.read")
register_route("GET", "/api/alerts/sources/values", "alerts.read")
register_route("POST", "/api/alerts/preview", "alerts.write")


# ── Models ────────────────────────────────────────────────────────────

class AlertMapping(BaseModel):
    """P230: where the data is and how the user mapped its columns.

    Send `source_id` (from /api/alerts/sources); the server works out the
    engine, connection, table and plugin from it. `table` is only needed for
    a connection source.
    """
    source_id: str | None = Field(default=None, description="pg:<table> | plugin:<id>:<dataset> | conn:<uuid> | query:<plugin>:<id>.")
    table: str | None = Field(default=None, description="For conn: sources only — a table on that connection.")
    date_column: str | None = None
    value_kind: str | None = Field(default=None, description="'column' | 'count' | 'ratio'.")
    denominator: str | None = None
    denominator_aggregation: str | None = None
    group_by_columns: list[str] | None = None
    filters: list[dict] | None = Field(default=None, description="[{column, op, value}]; op: eq neq in not_in gt gte lt lte contains empty not_empty.")
    min_volume_column: str | None = None
    min_volume: float | None = None
    currency_column: str | None = None
    query_params: dict | None = None


class AlertCreate(AlertMapping):
    name: str
    label: str
    description: str | None = None
    plugin_id: str = "core"
    dataset: str = ""
    metric: str = ""
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
    # P215: "log" by default; email only when the client asks for it.
    notify_channels: list[str] = ["log"]
    enabled: bool = True
    is_template: bool = False


class AlertPreview(AlertCreate):
    """An unsaved alert, for POST /api/alerts/preview."""
    name: str = "preview"
    label: str = "Preview"


class AlertUpdate(AlertMapping):
    label: str | None = None
    description: str | None = None
    enabled: bool | None = None
    metric: str | None = None
    aggregation: str | None = None
    condition_type: str | None = None
    threshold: float | None = None
    compare_to: str | None = None
    check_frequency: str | None = None
    check_period: str | None = None
    group_by: str | None = None
    scope_filters: dict | None = None
    cooldown_hours: int | None = None
    min_baseline: float | None = None
    notify_channels: list[str] | None = None


# Columns a create/update may write. Source fields come from the resolver.
_MAPPING_COLS = ("date_column", "value_kind", "denominator", "denominator_aggregation", "group_by_columns",
                 "filters", "min_volume_column", "min_volume", "currency_column", "query_params")
_JSON_COLS = ("scope_filters", "filters", "query_params")


def _apply_source(alert: dict, source_id: str | None, table: str | None, cur=None) -> None:
    """Fill engine / connection / dataset / plugin from the source id (server-side)."""
    from ..alert_sources import SourceError, resolve
    if not source_id:
        alert.setdefault("source_kind", "table")
        alert.setdefault("db_engine", "postgres")
        return
    try:
        src = resolve(source_id, table=table, pg_cursor=cur)
    except SourceError as e:
        raise HTTPException(422, str(e))
    if src.source_kind == "plugin_dataset" and not src.alertable:
        raise HTTPException(422, f"{src.plugin_id} keeps '{src.table}' out of direct alerts. "
                                 "Use one of its ready-made alerts instead.")
    if src.source_kind == "connection_table" and not src.table:
        raise HTTPException(422, "Choose a table on this connection.")
    alert.update(src.alert_fields())
    if src.source_kind == "plugin_query":
        alert["metric"] = alert.get("metric") or "*"
        alert["value_kind"] = "column"
    else:
        alert.setdefault("date_column", None)
        if not alert.get("date_column") and src.date_column:
            alert["date_column"] = src.date_column


def _check_alert(alert: dict, cur=None) -> None:
    """Refuse a mapping that can't run: unknown columns, wrong kinds, bad params."""
    from ..alert_engine import AlertConfigError, resolve_table, spec_from_alert, validate
    from ..query_drivers import ConnectionMissing, QueryError, get_driver
    spec = spec_from_alert(alert)
    try:
        if spec.source_kind == "plugin_query":
            from ..alert_queries import find_query, render
            from ..query_drivers import dialect_for
            q = find_query(spec.plugin_id or "", spec.query_id or "")
            if q is None or q.error:
                raise AlertConfigError(q.error if q else "Ready-made alert not found.")
            from datetime import date as _d
            render(q, dialect_for(q.engine), spec.query_params,
                   {k: _d.today() for k in ("period_start", "period_end", "baseline_start", "baseline_end")})
            return
        driver = get_driver(spec.engine, connection_id=spec.connection_id, pg_cursor=cur)
        table = resolve_table(driver, spec)
        validate(spec, {c.name: c for c in driver.columns(table)})
    except (AlertConfigError, ValueError) as e:
        raise HTTPException(422, str(e))
    except (ConnectionMissing, QueryError) as e:
        raise HTTPException(422, f"Can't reach the data: {e}")


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
    "rolling_30d":        "checks the last 30 days",
    "this_month":         "checks this month",
    "last_month":         "checks the last full month",
}


def _serialize_alert(row: dict) -> dict:
    """Serialize a DB row for JSON response."""
    from ..alert_sources import source_id_for_alert
    for k in ("created_at", "updated_at", "last_triggered", "last_run_at"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()
    if row.get("connection_id") is not None:
        row["connection_id"] = str(row["connection_id"])
    row["source_id"] = source_id_for_alert(row)
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
    availability: dict = {}

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

            # P230: registered connections whose engine has a driver. The
            # `plugin:<id>` rows are each plugin's internal Postgres handle,
            # not a data source a user picks.
            try:
                from ..query_drivers import DRIVERS
                cur.execute("""
                    SELECT id, name, type, is_active
                    FROM connections
                    WHERE type = ANY(%s) AND name NOT LIKE 'plugin:%%'
                    ORDER BY is_default DESC, name
                """, (list(DRIVERS),))
                for cid, cname, ctype, active in cur.fetchall():
                    connections_list.append({
                        "id": f"conn:{cid}",
                        "connection_id": str(cid),
                        "label": cname,
                        "connection_type": ctype,
                        "source_type": "connection",
                        "source_label": cname,
                        "engine": ctype,
                        "columns": [],
                        "needs_table": True,
                        "available": active is not False,
                        "unavailable_reason": None if active is not False else "This connection is switched off.",
                    })
                # Availability per engine from the rows just read (no extra query).
                for e in DRIVERS:
                    rows_e = [c for c in connections_list if c["engine"] == e]
                    if e == "postgres" or any(c["available"] for c in rows_e):
                        availability[e] = (True, "")
                    elif rows_e:
                        availability[e] = (False, f"The {e} connection is switched off.")
                    else:
                        hint = " Install the ClickHouse utility or add a connection." if e == "clickhouse" \
                            else " Add one on the Connections page."
                        availability[e] = (False, f"No {e} connection.{hint}")
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
                engine = str(ds.get("db") or "postgres").lower()
                ok, reason = availability.get(engine, (engine == "postgres", f"No driver for '{engine}'."))
                if ok and ds.get("alertable", True) is False:
                    ok, reason = False, "This plugin keeps this dataset out of direct alerts; use its ready-made alerts."
                plugin_datasets.append({
                    "id": f"plugin:{plugin_id}:{ds_name}",
                    "label": ds.get("label") or ds_name,
                    "source_type": "plugin",
                    "source_label": plugin_label,
                    "plugin_id": plugin_id,
                    "table": ds_name,
                    "columns": columns,
                    "engine": engine,
                    "available": ok,
                    "unavailable_reason": None if ok else reason,
                })
        except Exception as e:
            logger.warning(f"Could not read manifest for {plugin_id}: {e}")

    pg_table_names = {t["table"] for t in postgres_tables}
    plugin_datasets_deduped = [ds for ds in plugin_datasets
                               if not (ds["engine"] == "postgres" and ds["table"] in pg_table_names)]

    # P230 §5: ready-made alerts from plugins' alerts.yaml.
    queries: list[dict] = []
    try:
        from ..alert_queries import list_queries
        for q in list_queries():
            entry = q.as_dict()
            ok, reason = availability.get(q.engine, (q.engine == "postgres", f"No driver for '{q.engine}'."))
            if q.error:
                ok, reason = False, f"alerts.yaml: {q.error}"
            entry.update(available=ok, unavailable_reason=None if ok else reason)
            queries.append(entry)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not read alerts.yaml files: {e}")

    return {
        "postgres": postgres_tables,
        "connections": connections_list,
        "plugins": plugin_datasets_deduped,
        "queries": queries,
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
    """Create a new alert.

    P230: send `source_id` (and `table` for a connection) plus the column
    mapping; the server resolves where the data is and refuses a mapping
    that can't run (422 with the reason).
    """
    alert = req.model_dump(exclude={"source_id", "table"})
    with get_pg_conn() as conn:
        cur = conn.cursor()
        _apply_source(alert, req.source_id, req.table, cur)
        if not alert.get("group_by_columns") and alert.get("group_by"):
            alert["group_by_columns"] = [alert["group_by"]]
        if alert.get("value_kind") == "count" and not alert.get("metric"):
            alert["metric"] = "*"
        _check_alert(alert, cur)

        cols = ["name", "label", "description", "plugin_id", "dataset", "metric", "aggregation", "condition_type",
                "threshold", "compare_to", "scope", "group_by", "scope_filters", "check_frequency", "check_period",
                "cooldown_hours", "min_baseline", "notify_channels", "enabled", "is_template",
                "source_kind", "db_engine", "connection_id", "query_id", *_MAPPING_COLS]
        values = []
        for c in cols:
            v = alert.get(c)
            if c in _JSON_COLS:
                v = json.dumps(v if v is not None else ([] if c == "filters" else {}))
            elif c == "group_by_columns":
                v = list(v or [])
            elif c == "denominator_aggregation":
                v = v or "sum"
            elif c == "value_kind":
                v = v or "column"
            elif c == "date_column":
                v = v or "date"
            values.append(v)
        cur.execute(
            f"INSERT INTO alert_rules ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING *",
            values,
        )
        row = rows_as_dicts(cur)[0]

    logger.info(f"Alert created: {req.label} ({alert.get('db_engine')})")
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
    """Update an alert (toggle, change threshold, mapping, source …).

    The merged alert is checked like a new one whenever its source or
    mapping changes.
    """
    updates = req.model_dump(exclude_none=True, exclude={"source_id", "table"})
    if not updates and not req.source_id:
        raise HTTPException(400, "Nothing to update")

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alert_rules WHERE id = %s", (alert_id,))
        found = rows_as_dicts(cur)
        if not found:
            raise HTTPException(404, "Alert not found")
        merged = {**found[0], **updates}
        if req.source_id:
            _apply_source(merged, req.source_id, req.table, cur)
            for k in ("source_kind", "db_engine", "connection_id", "plugin_id", "dataset", "query_id"):
                updates[k] = merged.get(k)
        if "group_by" in updates and "group_by_columns" not in updates:
            updates["group_by_columns"] = [updates["group_by"]] if updates["group_by"] else []
            merged["group_by_columns"] = updates["group_by_columns"]
        mapping_keys = {"metric", "aggregation", "condition_type", "compare_to", "check_period", "group_by",
                        "scope_filters", *_MAPPING_COLS}
        if req.source_id or mapping_keys & set(updates):
            _check_alert(merged, cur)

        for k in _JSON_COLS:
            if k in updates:
                updates[k] = json.dumps(updates[k])
        updates["updated_at"] = datetime.now(timezone.utc)
        set_parts = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(f"UPDATE alert_rules SET {set_parts} WHERE id = %s RETURNING *",
                    list(updates.values()) + [alert_id])
        rows = rows_as_dicts(cur)

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

    B345: uses the same evaluator as the scheduled run (apps/api/src/
    alert_engine.py), on whatever database the alert reads. Nothing is
    sent and no trigger is recorded.
    """
    from ..alert_engine import evaluate_alert

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alert_rules WHERE id = %s", (alert_id,))
        rows = rows_as_dicts(cur)
        if not rows:
            raise HTTPException(404, "Alert not found")
        ev = evaluate_alert(rows[0], pg_cursor=cur)

    out = ev.as_dict(limit=50)
    if ev.status == "error":
        return {"alert_id": alert_id, "error": ev.error, "status": "error", "engine": ev.engine, "sql": ev.sql,
                "elapsed_ms": ev.elapsed_ms}
    fired = ev.fired_rows
    if ev.status == "no_data":
        message = "No data for this alert's period and filters."
    elif fired:
        message = f"Would fire on {len(fired)} of {ev.rows_checked} group(s)"
    else:
        message = "Would not fire — all values within threshold"
    return {
        "alert_id": alert_id, "fired": bool(fired), "message": message, "rows_checked": ev.rows_checked,
        "triggered_rows": fired[:5], "status": ev.status, "engine": ev.engine, "sql": ev.sql,
        "elapsed_ms": ev.elapsed_ms, "rows": out["rows"],
    }


# ── P230: column mapping and preview ──────────────────────────────────

def _resolved_table(source_id: str, table: str | None, cur):
    from ..alert_sources import SourceError, resolve
    from ..query_drivers import ConnectionMissing, QueryError, get_driver
    try:
        src = resolve(source_id, table=table, pg_cursor=cur)
        if src.source_kind == "plugin_query":
            raise HTTPException(422, "Ready-made alerts have no columns to map.")
        if src.source_kind == "plugin_dataset" and not src.alertable:
            raise HTTPException(422, f"{src.plugin_id} keeps '{src.table}' out of direct alerts.")
        if not src.table:
            raise HTTPException(422, "Choose a table on this connection.")
        driver = get_driver(src.engine, connection_id=src.connection_id, pg_cursor=cur)
        return src, driver, driver.locate(src.table, src.database)
    except SourceError as e:
        raise HTTPException(422, str(e))
    except (ConnectionMissing, QueryError) as e:
        raise HTTPException(422, f"Can't reach the data: {e}")


@router.get(
    "/alerts/sources/columns",
    operation_id="alerts.sources.columns",
    response_model=AlertSourceColumnsResponse,
    response_model_exclude_none=True,
    summary="Real columns of an alert source table, with their kinds",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
        422: {"model": ErrorDetail, "description": "Unknown source, unreachable database or table not found."},
    },
)
def alert_source_columns(
    source_id: str = Query(..., description="A source id from /api/alerts/sources."),
    table: str | None = Query(None, description="For conn: sources — a table on that connection."),
    _: None = Depends(requires("alerts.read")),
):
    """List a source table's columns (name, engine type, kind) so the user can map them."""
    from ..query_drivers import ConnectionMissing, QueryError
    with get_pg_conn() as conn:
        cur = conn.cursor()
        src, driver, ref = _resolved_table(source_id, table, cur)
        try:
            cols = driver.columns(ref)
        except (ConnectionMissing, QueryError) as e:
            raise HTTPException(422, f"Can't read the columns: {e}")
    dates = [c.name for c in cols if c.kind in ("date", "datetime")]
    suggested = src.date_column if src.date_column in dates else next(
        (n for n in ("date", "day", "report_date", "event_date", "created_at", "ts") if n in dates),
        dates[0] if dates else None)
    texts = [c.name for c in cols if c.kind == "text"]
    currency = src.currency_column if src.currency_column in texts else ("currency" if "currency" in texts else None)
    return {"source_id": source_id, "engine": src.engine, "table": ref.name, "database": ref.database,
            "table_engine": ref.engine_name, "columns": [c.as_dict() for c in cols],
            "suggested_date_column": suggested, "suggested_currency_column": currency}


@router.get(
    "/alerts/sources/tables",
    operation_id="alerts.sources.tables",
    response_model=AlertSourceTablesResponse,
    summary="Tables on a registered connection",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
        422: {"model": ErrorDetail, "description": "Not a connection source, or the connection is unreachable."},
    },
)
def alert_source_tables(
    source_id: str = Query(..., description="A conn:<uuid> source id."),
    _: None = Depends(requires("alerts.read")),
):
    """List the tables an alert can read on a registered connection."""
    from ..alert_sources import SourceError, resolve
    from ..query_drivers import ConnectionMissing, QueryError, get_driver
    if not source_id.startswith("conn:"):
        raise HTTPException(422, "Only connection sources have a table list.")
    with get_pg_conn() as conn:
        cur = conn.cursor()
        try:
            src = resolve(source_id, pg_cursor=cur)
            driver = get_driver(src.engine, connection_id=src.connection_id, pg_cursor=cur)
            tables = driver.list_tables()
        except SourceError as e:
            raise HTTPException(422, str(e))
        except (ConnectionMissing, QueryError) as e:
            raise HTTPException(422, f"Can't reach the data: {e}")
    return {"source_id": source_id, "engine": src.engine, "tables": tables}


@router.get(
    "/alerts/sources/values",
    operation_id="alerts.sources.values",
    response_model=AlertSourceValuesResponse,
    summary="Most common values of a column, for filter suggestions",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.read permission."},
        422: {"model": ErrorDetail, "description": "Unknown source or column."},
    },
)
def alert_source_values(
    source_id: str = Query(...),
    column: str = Query(...),
    table: str | None = Query(None),
    _: None = Depends(requires("alerts.read")),
):
    """Return up to 50 of the most common values of one column."""
    from ..query_drivers import ConnectionMissing, QueryError
    with get_pg_conn() as conn:
        cur = conn.cursor()
        src, driver, ref = _resolved_table(source_id, table, cur)
        try:
            names = {c.name for c in driver.columns(ref)}
            if column not in names:
                raise HTTPException(422, f"'{column}' is not a column of {ref.name}.")
            values = driver.distinct_values(ref, column, 50)
        except (ConnectionMissing, QueryError) as e:
            raise HTTPException(422, f"Can't read the values: {e}")
    return {"column": column, "values": values}


@router.post(
    "/alerts/preview",
    operation_id="alerts.preview",
    response_model=AlertPreviewResponse,
    response_model_exclude_none=True,
    summary="Evaluate an unsaved alert (nothing is sent or recorded)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the alerts.write permission."},
        422: {"model": ErrorDetail, "description": "Unknown source or a dataset kept out of direct alerts."},
    },
)
def preview_alert(
    req: AlertPreview,
    _: None = Depends(requires("alerts.write")),
):
    """Run an alert as it is in the builder and show which groups would fire, and the SQL."""
    from ..alert_engine import evaluate_alert
    alert = req.model_dump(exclude={"source_id", "table"})
    with get_pg_conn() as conn:
        cur = conn.cursor()
        _apply_source(alert, req.source_id, req.table, cur)
        if not alert.get("group_by_columns") and alert.get("group_by"):
            alert["group_by_columns"] = [alert["group_by"]]
        ev = evaluate_alert(alert, pg_cursor=cur)
    return ev.as_dict(limit=200)


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
