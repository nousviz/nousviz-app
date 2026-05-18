"""
/api/connections — Named connection management (P101).

Operators create named connections (MySQL, Postgres, ClickHouse) that
plugins reference by ID or inherit the default for their required type.
Includes health checks, credential rotation, and MySQL init flow.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn, dict_cursor
from .auth import get_me
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from .. import connection_catalog
from ..models.settings import (
    ConnectionDeleteResponse,
    ConnectionHealthCheckResponse,
    ConnectionHealthHistoryResponse,
    ConnectionRow,
    ConnectionTestResponse,
    ConnectionsListResponse,
    MysqlInitDefaultResponse,
)

logger = logging.getLogger("nousviz.connections")
router = APIRouter(prefix="/api/connections", tags=["connections"])

# B228: register connections routes. Connections hold credentials, so
# everything is mapped to plugins.configure (admin+) to match the existing
# _require_admin behaviour. connections.read / connections.write exist in
# the catalog (analyst+) for future use but aren't applied to these
# admin-managed routes — operators can broaden via the v0.9.9 matrix UI.
register_route("GET", "/api/connections", "plugins.configure")
register_route("GET", "/api/connections/by-type/{conn_type}", "plugins.configure")
register_route("GET", "/api/connections/default/{conn_type}", "plugins.configure")
register_route("POST", "/api/connections", "plugins.configure")
register_route("PATCH", "/api/connections/{conn_id}", "plugins.configure")
register_route("DELETE", "/api/connections/{conn_id}", "plugins.configure")
register_route("POST", "/api/connections/{conn_id}/test", "plugins.configure")
register_route("POST", "/api/connections/{conn_id}/health-check", "plugins.configure")
register_route("GET", "/api/connections/{conn_id}/health-history", "plugins.configure")
register_route("POST", "/api/connections/mysql/init-default", "plugins.configure")
register_route("GET", "/api/connections/{conn_id}/tables", "plugins.configure")
register_route("GET", "/api/connections/{conn_id}/tables/{schema}/{table}", "plugins.configure")
register_route("GET", "/api/connections/{conn_id}/tables/{schema}/{table}/rows", "plugins.configure")


def _serialize(row):
    d = dict(row)
    for k in ("created_at", "updated_at", "last_health_check"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    # Mask password in config
    cfg = d.get("config", {})
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    if cfg.get("password"):
        cfg["password"] = "••••••••"
    d["config"] = cfg
    # Parse health_history if string
    hh = d.get("health_history")
    if isinstance(hh, str):
        d["health_history"] = json.loads(hh)
    return d


# ── List ─────────────────────────────────────────────────────────────

@router.get(
    "",
    operation_id="connections.list",
    response_model=ConnectionsListResponse,
    response_model_exclude_none=True,
    summary="List all named connections (passwords masked)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
    },
)
async def list_connections(_: None = Depends(requires("plugins.configure"))):
    """List every operator-managed connection. Plugin-managed connections
    (`name='plugin:<slug>'`) appear here too; their config password
    field is replaced with the constant '••••••••'.
    """
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM connections ORDER BY type, is_default DESC, name")
        return {"connections": [_serialize(r) for r in cur.fetchall()]}


@router.get(
    "/by-type/{conn_type}",
    operation_id="connections.list_by_type",
    response_model=ConnectionsListResponse,
    response_model_exclude_none=True,
    summary="List connections of a specific type (postgres/mysql/clickhouse)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
    },
)
async def list_by_type(conn_type: str, _: None = Depends(requires("plugins.configure"))):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM connections WHERE type = %s ORDER BY is_default DESC, name", (conn_type,))
        return {"connections": [_serialize(r) for r in cur.fetchall()]}


@router.get(
    "/default/{conn_type}",
    operation_id="connections.default",
    response_model=ConnectionRow,
    response_model_exclude_none=True,
    summary="Get the default connection of a type (404 if none)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "No default connection of that type."},
    },
)
async def get_default(conn_type: str, _: None = Depends(requires("plugins.configure"))):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM connections WHERE type = %s AND is_default = true", (conn_type,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"No default {conn_type} connection configured")
    return _serialize(row)


# ── Create ───────────────────────────────────────────────────────────

class CreateConnection(BaseModel):
    name: str
    type: str
    config: dict
    is_default: bool = False
    description: str = ""
    tags: list[str] = []


@router.post(
    "",
    operation_id="connections.create",
    response_model=ConnectionRow,
    response_model_exclude_none=True,
    summary="Create a named connection",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid type, or name is empty."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
    },
)
async def create_connection(
    body: CreateConnection,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    admin = get_me(request)
    if body.type not in ("postgres", "mysql", "clickhouse"):
        raise HTTPException(400, f"Invalid type: {body.type}. Use postgres, mysql, or clickhouse.")
    if not body.name.strip():
        raise HTTPException(400, "Name is required")

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        # If marking as default, unset existing default for this type
        if body.is_default:
            cur.execute("UPDATE connections SET is_default = false WHERE type = %s", (body.type,))
        cur.execute("""
            INSERT INTO connections (name, type, config, is_default, description, tags, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (body.name.strip(), body.type, json.dumps(body.config), body.is_default, body.description, body.tags, admin.get("id")))
        row = cur.fetchone()

    return _serialize(row)


# ── Update ───────────────────────────────────────────────────────────

class UpdateConnection(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


@router.patch(
    "/{conn_id}",
    operation_id="connections.update",
    response_model=ConnectionRow,
    response_model_exclude_none=True,
    summary="Patch a connection (password preserved when masked)",
    responses={
        400: {"model": ErrorDetail, "description": "Empty body."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
    },
)
async def update_connection(
    conn_id: str,
    body: UpdateConnection,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        # If setting as default, unset existing
        if updates.get("is_default"):
            cur.execute("SELECT type FROM connections WHERE id = %s", (conn_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE connections SET is_default = false WHERE type = %s AND id != %s", (row["type"], conn_id))

        if "config" in updates:
            # Merge password — if masked, keep existing
            cur.execute("SELECT config FROM connections WHERE id = %s", (conn_id,))
            existing = cur.fetchone()
            if existing:
                old_cfg = existing["config"] if isinstance(existing["config"], dict) else json.loads(existing["config"])
                new_cfg = updates["config"]
                if new_cfg.get("password") == "••••••••":
                    new_cfg["password"] = old_cfg.get("password", "")
                updates["config"] = json.dumps(new_cfg)
            else:
                updates["config"] = json.dumps(updates["config"])

        set_parts = [f"{k} = %s" for k in updates] + ["updated_at = now()"]
        vals = list(updates.values()) + [conn_id]
        cur.execute(f"UPDATE connections SET {', '.join(set_parts)} WHERE id = %s RETURNING *", vals)
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Connection not found")

    return _serialize(row)


# ── Delete ───────────────────────────────────────────────────────────

@router.delete(
    "/{conn_id}",
    operation_id="connections.delete",
    response_model=ConnectionDeleteResponse,
    summary="Delete a connection",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
    },
)
async def delete_connection(
    conn_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM connections WHERE id = %s RETURNING id", (conn_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Connection not found")
    return {"deleted": True}


# ── Test ─────────────────────────────────────────────────────────────

@router.post(
    "/{conn_id}/test",
    operation_id="connections.test",
    response_model=ConnectionTestResponse,
    response_model_exclude_none=True,
    summary="Probe connectivity using stored credentials (no persist)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
    },
)
async def test_connection(
    conn_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT name, type, config FROM connections WHERE id = %s", (conn_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Connection not found")

    # B181 (v0.9.5.3): plugin synthetic connections (`name` starts with
    # `plugin:`) store credentials in the credentials table via the
    # plugin broker, not in `config`. Testing them through this endpoint
    # always failed with `fe_sendauth: no password supplied`. Return a
    # clear, actionable message instead. The UI also gates these — this
    # is defense in depth for any direct API caller.
    if row["name"] and row["name"].startswith("plugin:"):
        plugin_slug = row["name"][len("plugin:"):]
        return {
            "ok": False,
            "error": (
                f"Plugin-managed connection. Credentials live in the plugin's "
                f"settings, not here. Open /plugin/{plugin_slug}/settings to test "
                f"or update its credentials."
            ),
        }

    cfg = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])
    conn_type = row["type"]

    try:
        if conn_type == "postgres":
            import psycopg2
            c = psycopg2.connect(
                host=cfg.get("host", "localhost"),
                port=int(cfg.get("port", 5432)),
                user=cfg.get("user", ""),
                password=cfg.get("password", ""),
                dbname=cfg.get("database", ""),
                connect_timeout=5,
            )
            cur = c.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0].split(" on ")[0]
            c.close()
            return {"ok": True, "detail": version}

        elif conn_type == "mysql":
            try:
                import pymysql
                c = pymysql.connect(
                    host=cfg.get("host", "localhost"),
                    port=int(cfg.get("port", 3306)),
                    user=cfg.get("user", ""),
                    password=cfg.get("password", ""),
                    database=cfg.get("database", ""),
                    connect_timeout=5,
                )
                cur = c.cursor()
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
                c.close()
                return {"ok": True, "detail": f"MySQL {version}"}
            except ImportError:
                return {"ok": False, "error": "pymysql not installed. Run: pip install pymysql"}

        elif conn_type == "clickhouse":
            import urllib.request
            url = f"http://{cfg.get('host', 'localhost')}:{cfg.get('port', 8123)}/?query=SELECT+version()"
            res = urllib.request.urlopen(url, timeout=5)
            version = res.read().decode().strip()
            return {"ok": True, "detail": f"ClickHouse {version}"}

        return {"ok": False, "error": f"Unknown type: {conn_type}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Health check (run + store result) ────────────────────────────────

@router.post(
    "/{conn_id}/health-check",
    operation_id="connections.health_check",
    response_model=ConnectionHealthCheckResponse,
    summary="Probe + persist (last 20 entries kept in health_history)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
    },
)
async def run_health_check(
    conn_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Run a health check and store the result in health_history."""

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT id, type, config, health_history FROM connections WHERE id = %s", (conn_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Connection not found")

    cfg = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])
    conn_type = row["type"]
    history = row["health_history"] if isinstance(row["health_history"], list) else json.loads(row["health_history"] or "[]")

    # Run the actual check
    status = "connected"
    detail = ""
    try:
        if conn_type == "postgres":
            import psycopg2
            c = psycopg2.connect(
                host=cfg.get("host", "localhost"),
                port=int(cfg.get("port", 5432)),
                user=cfg.get("user", ""),
                password=cfg.get("password", ""),
                dbname=cfg.get("database", ""),
                connect_timeout=5,
            )
            cur2 = c.cursor()
            cur2.execute("SELECT version()")
            detail = cur2.fetchone()[0].split(" on ")[0]
            c.close()
        elif conn_type == "mysql":
            import pymysql
            c = pymysql.connect(
                host=cfg.get("host", "localhost"),
                port=int(cfg.get("port", 3306)),
                user=cfg.get("user", ""),
                password=cfg.get("password", ""),
                database=cfg.get("database", ""),
                connect_timeout=5,
            )
            cur2 = c.cursor()
            cur2.execute("SELECT VERSION()")
            detail = f"MySQL {cur2.fetchone()[0]}"
            c.close()
        elif conn_type == "clickhouse":
            import urllib.request
            url = f"http://{cfg.get('host', 'localhost')}:{cfg.get('port', 8123)}/?query=SELECT+version()"
            res = urllib.request.urlopen(url, timeout=5)
            detail = f"ClickHouse {res.read().decode().strip()}"
    except Exception as e:
        status = "error"
        detail = str(e)

    # Store result
    now = datetime.now(timezone.utc).isoformat()
    entry = {"status": status, "detail": detail, "checked_at": now}
    history = [entry] + history[:19]  # keep last 20

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE connections
            SET health_status = %s, last_health_check = now(), health_history = %s::jsonb, updated_at = now()
            WHERE id = %s
        """, (status, json.dumps(history), conn_id))

    return {"status": status, "detail": detail, "checked_at": now}


# ── Health history ───────────────────────────────────────────────────

@router.get(
    "/{conn_id}/health-history",
    operation_id="connections.health_history",
    response_model=ConnectionHealthHistoryResponse,
    response_model_exclude_none=True,
    summary="Last-stored health status + history JSONB",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
    },
)
async def get_health_history(
    conn_id: str,
    _: None = Depends(requires("plugins.configure")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT health_status, last_health_check, health_history FROM connections WHERE id = %s", (conn_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Connection not found")

    history = row["health_history"]
    if isinstance(history, str):
        history = json.loads(history)

    return {
        "status": row["health_status"],
        "last_check": row["last_health_check"].isoformat() if row["last_health_check"] else None,
        "history": history or [],
    }


# ── MySQL default database init ──────────────────────────────────────

@router.post(
    "/mysql/init-default",
    operation_id="connections.mysql.init_default",
    response_model=MysqlInitDefaultResponse,
    summary="Create the default MySQL 'nousviz' database",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "No default MySQL connection."},
        500: {"model": ErrorDetail, "description": "pymysql missing or CREATE DATABASE failed."},
    },
)
async def mysql_init_default(
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Create a default MySQL 'nousviz' database using existing default MySQL connection."""

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT id, config FROM connections WHERE type = 'mysql' AND is_default = true")
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "No default MySQL connection. Create one first.")

    cfg = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])

    try:
        import pymysql
        c = pymysql.connect(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 3306)),
            user=cfg.get("user", ""),
            password=cfg.get("password", ""),
            connect_timeout=5,
        )
        cur2 = c.cursor()
        cur2.execute("CREATE DATABASE IF NOT EXISTS nousviz CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        c.close()

        # Update the connection config to include the database
        cfg["database"] = "nousviz"
        with get_pg_conn() as conn:
            cur3 = conn.cursor()
            cur3.execute("UPDATE connections SET config = %s::jsonb, updated_at = now() WHERE id = %s",
                         (json.dumps(cfg), row["id"]))

        return {"ok": True, "detail": "Created database 'nousviz' and set as default"}
    except ImportError:
        raise HTTPException(500, "pymysql not installed")
    except Exception as e:
        raise HTTPException(500, f"Failed to create database: {e}")


# ── Data explorer: Connection → Table → Row drilldown ────────────────
#
# These endpoints open the EXTERNAL connection using stored credentials
# and introspect its information_schema. v1 supports postgres only;
# mysql/clickhouse return 501 (handled in connection_catalog._open_external).


@router.get(
    "/{conn_id}/tables",
    operation_id="connections.tables.list",
    summary="List tables for this connection's database (grouped by schema)",
    responses={
        400: {"model": ErrorDetail, "description": "Synthetic plugin connection; browse via /datasets instead."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection not found."},
        501: {"model": ErrorDetail, "description": "Connection type not supported for browsing yet."},
        502: {"model": ErrorDetail, "description": "Could not connect to the external database."},
    },
)
async def list_connection_tables(
    conn_id: str,
    _: None = Depends(requires("plugins.configure")),
):
    try:
        return connection_catalog.list_tables(conn_id)
    except connection_catalog.ConnectionCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get(
    "/{conn_id}/tables/{schema}/{table}",
    operation_id="connections.table.detail",
    summary="Schema + metadata for one (connection, schema, table)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid schema/table name or synthetic plugin connection."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission, or schema is hidden."},
        404: {"model": ErrorDetail, "description": "Connection or table not found."},
        501: {"model": ErrorDetail, "description": "Connection type not supported for browsing yet."},
        502: {"model": ErrorDetail, "description": "Could not connect to the external database."},
    },
)
async def get_connection_table(
    conn_id: str,
    schema: str,
    table: str,
    _: None = Depends(requires("plugins.configure")),
):
    try:
        return connection_catalog.get_table(conn_id, schema, table)
    except connection_catalog.ConnectionCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


# Same filter parser shape as catalog.py for client-frontend parity.
def _parse_conn_filter(raw: str) -> tuple[str, str, str | None]:
    if not raw or ":" not in raw:
        raise ValueError(f"invalid filter format: {raw!r}; expected col:op:value")
    parts = raw.split(":", 2)
    col = parts[0].strip()
    op = parts[1].strip() if len(parts) > 1 else ""
    value: str | None = parts[2] if len(parts) > 2 else None
    if not col:
        raise ValueError(f"invalid filter format: {raw!r}; column is empty")
    if not op:
        raise ValueError(f"invalid filter format: {raw!r}; operator is empty")
    if op in ("is_null", "not_null"):
        value = None
    elif value is None:
        raise ValueError(
            f"invalid filter format: {raw!r}; expected col:op:value (or "
            f"col:is_null / col:not_null without value)"
        )
    return (col, op, value)


@router.get(
    "/{conn_id}/tables/{schema}/{table}/rows",
    operation_id="connections.table.rows",
    summary="Paginated rows for a (connection, schema, table)",
    responses={
        400: {"model": ErrorDetail, "description": "Malformed filter, unknown column/operator, q too long, or too many filters."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Connection or table not found."},
        501: {"model": ErrorDetail, "description": "Connection type not supported for browsing yet."},
        502: {"model": ErrorDetail, "description": "Could not connect to the external database."},
    },
)
async def get_connection_table_rows(
    conn_id: str,
    schema: str,
    table: str,
    page: int = 1,
    limit: int = 50,
    sort: Optional[str] = None,
    q: Optional[str] = None,
    filter: list[str] = [],
    _: None = Depends(requires("plugins.configure")),
):
    if len(filter) > 8:
        raise HTTPException(400, f"too many filters (max 8; got {len(filter)})")

    parsed: list[tuple[str, str, str | None]] = []
    for raw in filter:
        try:
            parsed.append(_parse_conn_filter(raw))
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    try:
        return connection_catalog.fetch_rows(
            conn_id=conn_id,
            schema=schema,
            table=table,
            page=max(1, page),
            limit=max(1, min(500, limit)),
            sort=sort,
            q=q if q else None,
            filters=parsed or None,
        )
    except connection_catalog.ConnectionCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception:
        logger.exception(f"connections.rows: fetch failed for {conn_id}/{schema}.{table}")
        raise HTTPException(500, "Failed to fetch rows. Check API logs.")
