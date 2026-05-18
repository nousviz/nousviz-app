"""
Catalog API endpoints (B170-rev2 / v0.9.5.3).

Exposes the discovery module at apps/api/src/catalog.py over HTTP.
The host introspects information_schema as the source of truth for
"what tables exist"; these endpoints surface that to the frontend
(Datasets page, Dataset detail page) and to downstream consumers
(future fusion refactor, widget data hooks).

Auth: all endpoints require analyst-or-admin role. Defense in depth:
the underlying catalog module only enumerates tables granted to
nousviz_plugin (so even if a bug in this layer leaked, the role
boundary still protects credentials/users/api_keys).

Backward compat: /api/data-port/* endpoints remain in place. They
have their own eligibility gate (plugin must ship dataport.yaml) and
are kept untouched in v0.9.5.3 — any third-party code calling them
keeps working.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import catalog
from ..rbac import requires, register_route, requires_plugin_access, user_can_access_plugin
from ..models import ErrorDetail, RBACErrorDetail
from ..models.catalog import (
    CatalogPluginTablesResponse,
    CatalogTable,
    CatalogTableRowsResponse,
    CatalogTablesGroupedResponse,
)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

# B228: register all catalog routes (datasets.read tier).
register_route("GET", "/api/catalog/tables", "datasets.read")
register_route("GET", "/api/catalog/plugins/{plugin_id}/tables", "datasets.read")
register_route("GET", "/api/catalog/plugins/{plugin_id}/tables/{table_name}", "datasets.read")
register_route("GET", "/api/catalog/plugins/{plugin_id}/tables/{table_name}/rows", "datasets.read")

logger = logging.getLogger("nousviz.routes.catalog")


@router.get(
    "/tables",
    operation_id="catalog.tables.grouped",
    response_model=CatalogTablesGroupedResponse,
    response_model_exclude_none=True,
    summary="All discovered plugin tables, grouped by plugin",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
    },
)
async def list_all_tables(
    request: Request,
    _: None = Depends(requires("datasets.read")),
) -> dict:
    # B305.1: filter the grouped result so a restricted viewer only
    # sees plugins they're allowed to access. Admin/superadmin bypass.
    from .auth import get_me

    _current_user = get_me(request)
    """All discovered plugin tables, grouped by plugin.

    Powers the Datasets page. Replaces the manifest-aggregation flow
    in DatasetsPage.tsx that read from /api/plugins.

    Response shape:
        {
          "plugins": [
            {
              "id": "example-plugin",
              "tables": [
                {
                  "name": "example_brands",
                  "plugin_id": "example-plugin",
                  "table_type": "BASE TABLE",
                  "row_count_estimate": 7068,
                  "columns": [{"name": "id", "data_type": "bigint", ...}, ...],
                },
                ...
              ]
            },
            ...
          ]
        }
    """
    grouped = catalog.list_all_tables_grouped_by_plugin()
    return {
        "plugins": [
            {
                "id": plugin_id,
                "tables": [t.to_dict() for t in tables],
            }
            for plugin_id, tables in sorted(grouped.items())
            if user_can_access_plugin(
                _current_user.get("id"), _current_user.get("role"), plugin_id
            )
        ]
    }


@router.get(
    "/plugins/{plugin_id}/tables",
    operation_id="catalog.plugin_tables.list",
    response_model=CatalogPluginTablesResponse,
    response_model_exclude_none=True,
    summary="Discovered tables for one plugin (with manifest drift)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
    },
)
async def list_plugin_tables(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("datasets.read")),
    _gate: None = Depends(requires_plugin_access()),  # B305.1
) -> dict:
    """All discovered tables for a single plugin.

    Returns empty `tables` list (not 404) if the plugin has no
    discovered tables, so the frontend can render an empty state
    cleanly without distinguishing "plugin not installed" from
    "plugin owns nothing."
    """
    tables = catalog.list_tables_for_plugin(plugin_id)
    return {
        "plugin_id": plugin_id,
        "tables": [t.to_dict() for t in tables],
        "manifest_drift": catalog.detect_manifest_drift(plugin_id),
    }


@router.get(
    "/plugins/{plugin_id}/tables/{table_name}",
    operation_id="catalog.plugin_table.detail",
    response_model=CatalogTable,
    response_model_exclude_none=True,
    summary="Schema + metadata for one (plugin, table) pair",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed, manifest doesn't declare table, or table missing."},
    },
)
async def get_plugin_table(
    plugin_id: str,
    table_name: str,
    request: Request,
    _: None = Depends(requires("datasets.read")),
    _gate: None = Depends(requires_plugin_access()),  # B305.1
) -> dict:
    """Schema and metadata for one specific (plugin, table)."""
    table = catalog.get_table(plugin_id, table_name)
    if not table:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Table {table_name!r} not found for plugin {plugin_id!r}. "
                "Either the plugin is not installed, the manifest doesn't "
                "declare this table, or the table doesn't exist in the database."
            ),
        )
    return table.to_dict()


# B262 (v0.9.11.5): caps for server-side row filtering. Mirror the
# defense-in-depth caps in catalog._build_where so 400-vs-500 split
# stays clean (route enforces; catalog asserts).
_MAX_FILTERS = 8
_MAX_Q_LENGTH = 100


def _parse_filter_param(raw: str) -> tuple[str, str, str | None]:
    """Parse a `?filter=col:op:value` string into (col, op, value).

    For null operators (`is_null`, `not_null`), value is None and the
    trailing `:` is optional.

    Raises ValueError with a user-facing message on malformed input.
    The caller (route handler) catches and maps to 400.
    """
    if not raw or ":" not in raw:
        raise ValueError(
            f"invalid filter format: {raw!r}; expected col:op:value"
        )

    # Split with maxsplit=2 so values containing colons survive.
    parts = raw.split(":", 2)
    col = parts[0].strip()
    op = parts[1].strip() if len(parts) > 1 else ""
    value: str | None = parts[2] if len(parts) > 2 else None

    if not col:
        raise ValueError(f"invalid filter format: {raw!r}; column is empty")
    if not op:
        raise ValueError(f"invalid filter format: {raw!r}; operator is empty")

    if op in ("is_null", "not_null"):
        # Null ops don't carry a value; ignore anything after the second colon.
        value = None
    elif value is None:
        raise ValueError(
            f"invalid filter format: {raw!r}; expected col:op:value (or "
            f"col:is_null / col:not_null without value)"
        )

    return (col, op, value)


@router.get(
    "/plugins/{plugin_id}/tables/{table_name}/rows",
    operation_id="catalog.plugin_table.rows",
    response_model=CatalogTableRowsResponse,
    summary="Paginated rows from a discovered plugin table (B262: server-side filters + search)",
    responses={
        400: {"model": ErrorDetail, "description": "Malformed filter, unknown column/operator, q too long, or too many filters."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
        404: {"model": ErrorDetail, "description": "Table not owned by plugin or doesn't exist."},
        500: {"model": ErrorDetail, "description": "Internal — fetch_rows raised. Check API logs."},
    },
)
async def get_plugin_table_rows(
    plugin_id: str,
    table_name: str,
    request: Request,
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(50, ge=1, le=500),
    sort: str | None = Query(None, max_length=200),
    q: str | None = Query(
        None,
        max_length=_MAX_Q_LENGTH,
        description=(
            "Full-dataset substring search (B262). Matches via ILIKE %q% "
            "across text-coercible columns (text, varchar, json, jsonb, uuid). "
            f"Capped at {_MAX_Q_LENGTH} characters."
        ),
    ),
    filter: list[str] = Query(
        [],
        description=(
            "Per-column predicate filter (B262). Repeatable. Each filter is "
            "`col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, "
            f"startswith, is_null, not_null. Up to {_MAX_FILTERS} per request. "
            "Filters compose with AND."
        ),
    ),
    _: None = Depends(requires("datasets.read")),
    _gate: None = Depends(requires_plugin_access()),  # B305.1
) -> dict:
    """Paginated rows from a discovered plugin table.

    The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
    Works for every plugin's every granted table — no `dataport.yaml`
    opt-in required.

    `sort` accepts "column" or "column desc" / "column asc". Invalid
    sort (column not in table) is silently dropped (no-sort fallback)
    rather than 400-erroring; pagination still works.

    `q` is a server-side substring search. Casts text-coercible columns
    to text and matches via ILIKE. Empty q is treated as no q.

    `filter` is repeatable. Each value is `col:op:value` (or
    `col:is_null` / `col:not_null` for null checks). Filters AND together;
    the response's `total` reflects the filtered count.

    Response:
        {
          "rows": [{...}, {...}, ...],
          "total": 7068,    # filtered count when q/filter present
          "page": 1,
          "limit": 50
        }
    """
    # B262: parse + validate filters in the route. Errors here are
    # user-correctable → 400. catalog.fetch_rows still cap-asserts as
    # defense in depth, but those paths should be unreachable from here.
    if len(filter) > _MAX_FILTERS:
        raise HTTPException(
            status_code=400,
            detail=f"too many filters (max {_MAX_FILTERS}; got {len(filter)})",
        )

    parsed_filters: list[tuple[str, str, str | None]] = []
    for raw in filter:
        try:
            parsed_filters.append(_parse_filter_param(raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # Empty q normalises to None so catalog.fetch_rows skips the WHERE
    # branch entirely (cheaper for unfiltered queries).
    q_clean = q if q else None

    try:
        return catalog.fetch_rows(
            plugin_id=plugin_id,
            table_name=table_name,
            page=page,
            limit=limit,
            sort=sort,
            q=q_clean,
            filters=parsed_filters or None,
        )
    except ValueError as exc:
        msg = str(exc)
        # B262: distinguish ownership/existence errors (404) from
        # filter-validation errors (400). _build_where raises with
        # specific prefixes; ownership errors mention "not owned" /
        # "not installed" / "not granted".
        if any(kw in msg for kw in ("unknown column", "unknown operator", "too many filters", "q too long")):
            raise HTTPException(status_code=400, detail=msg)
        # Default: ownership/existence failure → 404.
        raise HTTPException(status_code=404, detail=msg)
    except Exception:
        logger.exception(
            f"catalog: fetch_rows failed for {plugin_id}/{table_name}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch rows. Check API logs.",
        )
