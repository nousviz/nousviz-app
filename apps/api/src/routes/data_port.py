"""
Data Port API — serves plugin data port tab configurations.
Plugins opt in by placing a dataport.yaml in their package root.
No plugin is hardcoded here.
"""
import logging

import yaml
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..db import get_pg_conn
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.data_port import (
    DataportPluginConfigResponse,
    DataportPluginsListResponse,
    DataportTabRowsResponse,
)

logger = logging.getLogger("nousviz.api.data_port")

router = APIRouter(prefix="/api/data-port", tags=["data-port"])

# B228: register data-port routes (silent-leak fix). Reads use datasets.read.
register_route("GET", "/api/data-port/plugins", "datasets.read")
register_route("GET", "/api/data-port/plugins/{plugin_slug}", "datasets.read")
register_route("GET", "/api/data-port/plugins/{plugin_slug}/tab/{tab_id}", "datasets.read")

PLUGINS_INSTALLED = Path(__file__).resolve().parents[4] / "plugins" / "installed"


def _load_dataport(plugin_slug: str) -> dict | None:
    path = PLUGINS_INSTALLED / plugin_slug / "dataport.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


@router.get(
    "/plugins",
    operation_id="data_port.plugins.list",
    response_model=DataportPluginsListResponse,
    summary="Installed plugins that ship dataport.yaml",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
    },
)
def list_dataport_plugins(_: None = Depends(requires("datasets.read"))):
    """List all installed plugins that have a dataport.yaml."""
    plugins = []
    for path in sorted(PLUGINS_INSTALLED.glob("*/dataport.yaml")):
        try:
            cfg = yaml.safe_load(path.read_text())
            plugins.append({
                "slug": path.parent.name,
                "tabs": [{"id": t["id"], "label": t["label"]} for t in cfg.get("tabs", [])],
            })
        except Exception:
            pass
    return {"plugins": plugins}


@router.get(
    "/plugins/{plugin_slug}",
    operation_id="data_port.plugin.config",
    response_model=DataportPluginConfigResponse,
    summary="Full dataport.yaml config for a plugin (verbatim)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin has no dataport.yaml."},
    },
)
def get_dataport_config(
    plugin_slug: str,
    _: None = Depends(requires("datasets.read")),
):
    """Return the full dataport.yaml config for a plugin.

    Schema is plugin-author-defined; we return it verbatim and let
    the frontend render whatever the plugin declared.
    """
    cfg = _load_dataport(plugin_slug)
    if not cfg:
        raise HTTPException(404, f"No dataport config for plugin: {plugin_slug}")
    return cfg


@router.get(
    "/plugins/{plugin_slug}/tab/{tab_id}",
    operation_id="data_port.tab.rows",
    response_model=DataportTabRowsResponse,
    summary="Paginated rows from a dataport tab's declared table",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid sort direction or column."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin has no dataport.yaml or tab not declared."},
    },
)
def get_tab_data(
    plugin_slug: str,
    tab_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    _: None = Depends(requires("datasets.read")),
    sort: str | None = None,
):
    """Query a plugin's dataport tab directly from its declared table.

    Sort/filter validation: column names and filter keys must appear in
    the plugin's `dataport.yaml`; any other keys are silently dropped.
    Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
    on every column reference (S106).
    """
    cfg = _load_dataport(plugin_slug)
    if not cfg:
        raise HTTPException(404, f"No dataport config for plugin: {plugin_slug}")

    tab = next((t for t in cfg.get("tabs", []) if t["id"] == tab_id), None)
    if not tab:
        raise HTTPException(404, f"Tab not found: {tab_id}")

    # S106: validate sort + use Identifier() everywhere.
    # `table` and `columns[].key` come from trusted plugin YAML but should
    # still use Identifier() to quote them properly (safe against unusual
    # identifiers). `sort` is a URL query parameter and MUST be validated
    # against the declared column list — previously it was unquoted raw
    # SQL via pg_sql.SQL().
    from psycopg2 import sql as pg_sql

    table = tab["table"]
    declared_cols = [c["key"] for c in tab.get("columns", [])]
    declared_col_set = set(declared_cols)

    if declared_cols:
        col_list_sql = pg_sql.SQL(", ").join(pg_sql.Identifier(c) for c in declared_cols)
    else:
        col_list_sql = pg_sql.SQL("*")

    # Parse and validate sort parameter. Accepted shapes:
    #   "col"         → ORDER BY col ASC
    #   "col ASC"     → ORDER BY col ASC
    #   "col DESC"    → ORDER BY col DESC
    # Fallback to default_sort from YAML when no user input.
    sort_raw = (sort or tab.get("default_sort") or "").strip()
    if sort_raw:
        parts = sort_raw.split()
        sort_col = parts[0]
        sort_dir = parts[1].upper() if len(parts) > 1 else "ASC"
        if sort_dir not in ("ASC", "DESC"):
            raise HTTPException(400, f"Invalid sort direction: {parts[1]!r}. Use ASC or DESC.")
        # default_sort may be a literal like "1" for positional; allow if no cols declared.
        if declared_col_set and sort_col not in declared_col_set:
            raise HTTPException(
                400,
                f"Invalid sort column: {sort_col!r}. "
                f"Must be one of: {sorted(declared_col_set)}",
            )
        # If declared_col_set is empty (plugin didn't declare cols), only
        # allow the literal positional "1" as a safe fallback.
        if not declared_col_set and sort_col != "1":
            raise HTTPException(400, "sort requires declared columns in the dataport config")
        if sort_col == "1":
            order_sql = pg_sql.SQL("1 {}").format(pg_sql.SQL(sort_dir))
        else:
            order_sql = pg_sql.SQL("{} {}").format(
                pg_sql.Identifier(sort_col),
                pg_sql.SQL(sort_dir),
            )
    else:
        order_sql = pg_sql.SQL("1")

    offset = (page - 1) * page_size

    # Build WHERE clause from declared filters + query params.
    # Each `key` is already validated by membership in declared_filters but
    # we additionally use Identifier() to quote safely.
    where_clauses = []
    params: list = []
    declared_filters = {f["key"]: f for f in tab.get("filters", [])}
    for key, val in request.query_params.items():
        if key in ("page", "page_size", "sort") or not val:
            continue
        if key not in declared_filters:
            continue
        filt = declared_filters[key]
        if filt["type"] == "select":
            where_clauses.append(pg_sql.SQL("{} = %s").format(pg_sql.Identifier(key)))
            params.append(val)
        elif filt["type"] == "text_search":
            where_clauses.append(pg_sql.SQL("{} ILIKE %s").format(pg_sql.Identifier(key)))
            params.append(f"%{val}%")

    if where_clauses:
        where_sql = pg_sql.SQL("WHERE ") + pg_sql.SQL(" AND ").join(where_clauses)
    else:
        where_sql = pg_sql.SQL("")

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            query = pg_sql.SQL("SELECT {} FROM {} {} ORDER BY {} LIMIT %s OFFSET %s").format(
                col_list_sql,
                pg_sql.Identifier(table),
                where_sql,
                order_sql,
            )
            cur.execute(query, params + [page_size, offset])
            col_names = [d[0] for d in cur.description]
            rows = []
            for row in cur.fetchall():
                r = {}
                for i, col in enumerate(col_names):
                    val = row[i]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    r[col] = val
                rows.append(r)
            count_q = pg_sql.SQL("SELECT count(*) FROM {} {}").format(
                pg_sql.Identifier(table), where_sql,
            )
            cur.execute(count_q, params)
            total = cur.fetchone()[0]
    except HTTPException:
        raise
    except Exception as e:
        if "UndefinedTable" in type(e).__name__ or "does not exist" in str(e):
            logger.info(f"Data Port: table '{table}' does not exist for plugin '{plugin_slug}' — returning empty")
        else:
            raise
        return {"rows": [], "total": 0, "page": page, "page_size": page_size}
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}
