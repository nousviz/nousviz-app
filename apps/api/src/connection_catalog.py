"""
Connection-keyed data catalog. Introspects operator-defined external
connections via stored credentials.

Mirrors apps/api/src/catalog.py's response shapes but keyed by
connection_id instead of plugin_id. Used by /api/connections/{conn_id}/tables/...
to power the Connection -> Table -> Row drilldown in the data explorer.

v1: Postgres connections only. MySQL/ClickHouse return None / empty
from list_tables; the route layer surfaces a clear 501 for those.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import psycopg2
from psycopg2 import sql as pg_sql

from .db import get_pg_conn, dict_cursor

logger = logging.getLogger("nousviz.connection_catalog")


_VALID_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_VALID_SCHEMA = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# System schemas hidden from the explorer. Match the spirit of the
# fusion query blocklist: surface what the operator owns, not the
# Postgres internals.
_HIDDEN_SCHEMAS = frozenset({
    "pg_catalog", "information_schema", "pg_toast",
})

# Mirror catalog.py defenses so the two endpoints behave identically.
_FILTER_OPS = frozenset({
    "eq", "neq", "gt", "lt", "gte", "lte",
    "contains", "startswith",
    "is_null", "not_null",
})
_OP_TO_SQL = {
    "eq": "=", "neq": "<>", "gt": ">", "lt": "<", "gte": ">=", "lte": "<=",
}
_TEXT_COERCIBLE_TYPES = frozenset({
    "text", "character varying", "varchar", "character", "char",
    "json", "jsonb", "uuid",
})
_MAX_FILTERS = 8
_MAX_Q_LENGTH = 100


class ConnectionCatalogError(Exception):
    """Raised when introspection fails for a reason worth surfacing
    (bad credentials, unreachable host, unsupported connection type).

    Carries a `status_code` hint so the route layer can map to the
    right HTTP status without leaking driver-specific exception types.
    """

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


# ── Connection resolution ────────────────────────────────────────────

def _load_connection(conn_id: str) -> dict:
    """Fetch a connection row with decrypted config. Raises if missing
    or if it's a plugin-managed synthetic connection (those have empty
    config and are not browsable through this path)."""
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT id, name, type, config FROM connections WHERE id = %s",
            (conn_id,),
        )
        row = cur.fetchone()

    if not row:
        raise ConnectionCatalogError("Connection not found", status_code=404)

    if row.get("name", "").startswith("plugin:"):
        slug = row["name"][len("plugin:"):]
        raise ConnectionCatalogError(
            f"Plugin-managed connection. Browse this plugin's tables at "
            f"/datasets?plugin={slug} instead.",
            status_code=400,
        )

    cfg = row["config"]
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    row["config"] = cfg or {}
    return row


def _open_external(conn_row: dict):
    """Open a psycopg2 connection to the external DB. Caller must close.

    Only postgres is supported in v1. Raises ConnectionCatalogError for
    other types so the route can map to 501.
    """
    if conn_row["type"] != "postgres":
        raise ConnectionCatalogError(
            f"Browsing tables for {conn_row['type']} connections is not "
            f"supported yet. Postgres connections only in v1.",
            status_code=501,
        )

    cfg = conn_row["config"]
    try:
        return psycopg2.connect(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 5432)),
            user=cfg.get("user", ""),
            password=cfg.get("password", ""),
            dbname=cfg.get("database", ""),
            connect_timeout=5,
        )
    except psycopg2.Error as exc:
        raise ConnectionCatalogError(
            f"Could not connect to {conn_row['name']}: {exc}",
            status_code=502,
        )


# ── Introspection ────────────────────────────────────────────────────

def list_tables(conn_id: str) -> dict:
    """List user tables for this connection grouped by schema.

    Returns:
        {
          "connection": {"id": "...", "name": "...", "type": "postgres", "database": "..."},
          "schemas": [
            {
              "name": "public",
              "tables": [
                {"name": "users", "table_type": "BASE TABLE", "row_count_estimate": 12345},
                ...
              ]
            },
            ...
          ]
        }
    """
    conn_row = _load_connection(conn_id)
    db = _open_external(conn_row)
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT t.table_schema, t.table_name, t.table_type,
                       c.reltuples::BIGINT AS row_est
                FROM information_schema.tables t
                LEFT JOIN pg_namespace n ON n.nspname = t.table_schema
                LEFT JOIN pg_class c
                  ON c.relname = t.table_name
                 AND c.relnamespace = n.oid
                 AND c.relkind IN ('r', 'v', 'm', 'p')
                WHERE t.table_schema NOT IN %s
                  AND t.table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY t.table_schema, t.table_name
                """,
                (tuple(_HIDDEN_SCHEMAS),),
            )
            rows = cur.fetchall()
    finally:
        db.close()

    grouped: dict[str, list[dict]] = {}
    for schema, name, ttype, row_est in rows:
        est = int(row_est) if row_est is not None else None
        if est is not None and est < 0:
            est = None
        grouped.setdefault(schema, []).append({
            "name": name,
            "table_type": ttype,
            "row_count_estimate": est,
        })

    return {
        "connection": {
            "id": conn_row["id"],
            "name": conn_row["name"],
            "type": conn_row["type"],
            "database": conn_row["config"].get("database", ""),
        },
        "schemas": [
            {"name": schema, "tables": grouped[schema]}
            for schema in sorted(grouped.keys())
        ],
    }


def _validate_schema_table(schema: str, table: str) -> None:
    if not _VALID_SCHEMA.match(schema):
        raise ConnectionCatalogError(
            f"Invalid schema name {schema!r}", status_code=400,
        )
    if not _VALID_IDENT.match(table):
        raise ConnectionCatalogError(
            f"Invalid table name {table!r}", status_code=400,
        )
    if schema in _HIDDEN_SCHEMAS:
        raise ConnectionCatalogError(
            f"Schema {schema!r} is not browsable.", status_code=403,
        )


def get_table(conn_id: str, schema: str, table: str) -> dict:
    """Return schema + metadata for one (connection, schema, table).

    Response shape mirrors /api/catalog/plugins/.../tables/.../ so the
    frontend row browser can be parameterised on either route.
    """
    _validate_schema_table(schema, table)
    conn_row = _load_connection(conn_id)
    db = _open_external(conn_row)
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT t.table_type, c.reltuples::BIGINT AS row_est
                FROM information_schema.tables t
                LEFT JOIN pg_namespace n ON n.nspname = t.table_schema
                LEFT JOIN pg_class c
                  ON c.relname = t.table_name
                 AND c.relnamespace = n.oid
                WHERE t.table_schema = %s AND t.table_name = %s
                """,
                (schema, table),
            )
            row = cur.fetchone()
            if not row:
                raise ConnectionCatalogError(
                    f"Table {schema}.{table} not found on this connection.",
                    status_code=404,
                )
            table_type, row_est = row
            est = int(row_est) if row_est is not None else None
            if est is not None and est < 0:
                est = None

            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            columns = [
                {
                    "name": cname,
                    "data_type": dtype,
                    "is_nullable": nullable == "YES",
                    "ordinal_position": ord_pos,
                }
                for (cname, dtype, nullable, ord_pos) in cur.fetchall()
            ]
    finally:
        db.close()

    return {
        "name": table,
        "schema": schema,
        "connection_id": conn_id,
        "table_type": table_type,
        "row_count_estimate": est,
        "columns": columns,
    }


# ── Row fetching ─────────────────────────────────────────────────────

def _build_where(
    columns: list[dict],
    q: Optional[str],
    filters: Optional[list[tuple[str, str, Optional[str]]]],
) -> tuple[Optional[pg_sql.Composed], list]:
    """Mirror catalog._build_where but takes column dicts (the shape
    we return from get_table) instead of CatalogColumn dataclasses."""
    if q is None and not filters:
        return (None, [])
    if q is not None and len(q) > _MAX_Q_LENGTH:
        raise ValueError(f"q too long (max {_MAX_Q_LENGTH} chars)")
    if filters and len(filters) > _MAX_FILTERS:
        raise ValueError(f"too many filters (max {_MAX_FILTERS})")

    valid_cols = {c["name"]: c for c in columns}
    fragments: list[pg_sql.Composable] = []
    params: list = []

    if q:
        text_cols = [
            c["name"] for c in columns if c["data_type"] in _TEXT_COERCIBLE_TYPES
        ]
        if text_cols:
            wrapped = f"%{q}%"
            or_parts = pg_sql.SQL(" OR ").join(
                pg_sql.SQL("{}::text ILIKE %s").format(pg_sql.Identifier(c))
                for c in text_cols
            )
            fragments.append(pg_sql.SQL("(") + or_parts + pg_sql.SQL(")"))
            params.extend([wrapped] * len(text_cols))
        else:
            fragments.append(pg_sql.SQL("FALSE"))

    for col, op, value in (filters or []):
        if op not in _FILTER_OPS:
            raise ValueError(f"unknown operator {op!r}")
        if col not in valid_cols:
            raise ValueError(f"unknown column {col!r}")
        ident = pg_sql.Identifier(col)
        if op == "is_null":
            fragments.append(pg_sql.SQL("{} IS NULL").format(ident))
        elif op == "not_null":
            fragments.append(pg_sql.SQL("{} IS NOT NULL").format(ident))
        elif op == "contains":
            fragments.append(pg_sql.SQL("{}::text ILIKE %s").format(ident))
            params.append(f"%{value if value is not None else ''}%")
        elif op == "startswith":
            fragments.append(pg_sql.SQL("{}::text ILIKE %s").format(ident))
            params.append(f"{value if value is not None else ''}%")
        else:
            sql_op = _OP_TO_SQL[op]
            fragments.append(pg_sql.SQL("{} " + sql_op + " %s").format(ident))
            params.append(value)

    if not fragments:
        return (None, [])
    return (pg_sql.SQL(" AND ").join(fragments), params)


def _parse_sort(sort: Optional[str], columns: list[dict]) -> tuple[Optional[str], str]:
    if not sort:
        return (None, "ASC")
    parts = sort.strip().split()
    if not parts:
        return (None, "ASC")
    col = parts[0]
    direction = (
        "DESC" if len(parts) > 1 and parts[1].lower().startswith("desc") else "ASC"
    )
    if col not in {c["name"] for c in columns}:
        return (None, "ASC")
    return (col, direction)


def fetch_rows(
    conn_id: str,
    schema: str,
    table: str,
    page: int = 1,
    limit: int = 50,
    sort: Optional[str] = None,
    q: Optional[str] = None,
    filters: Optional[list[tuple[str, str, Optional[str]]]] = None,
) -> dict:
    """Paginated rows from a (connection, schema, table). Same response
    shape as catalog.fetch_rows so the frontend can share state."""
    meta = get_table(conn_id, schema, table)
    conn_row = _load_connection(conn_id)
    page = max(1, page)
    limit = max(1, min(500, limit))
    offset = (page - 1) * limit

    sort_col, sort_dir = _parse_sort(sort, meta["columns"])
    where_fragment, where_params = _build_where(meta["columns"], q, filters)
    table_ref = pg_sql.Identifier(schema, table)

    db = _open_external(conn_row)
    try:
        with db.cursor() as cur:
            if where_fragment is not None:
                cur.execute(
                    pg_sql.SQL("SELECT COUNT(*) FROM {} WHERE ").format(table_ref)
                    + where_fragment,
                    where_params,
                )
            else:
                cur.execute(
                    pg_sql.SQL("SELECT COUNT(*) FROM {}").format(table_ref)
                )
            total = cur.fetchone()[0]

            pieces = [pg_sql.SQL("SELECT * FROM {}").format(table_ref)]
            params: list = []
            if where_fragment is not None:
                pieces.append(pg_sql.SQL(" WHERE ") + where_fragment)
                params.extend(where_params)
            if sort_col:
                pieces.append(
                    pg_sql.SQL(" ORDER BY {} {}").format(
                        pg_sql.Identifier(sort_col),
                        pg_sql.SQL(sort_dir),
                    )
                )
            pieces.append(pg_sql.SQL(" LIMIT %s OFFSET %s"))
            params.extend([limit, offset])

            cur.execute(pg_sql.Composed(pieces), params)
            col_names = [d[0] for d in cur.description]
            rows = [dict(zip(col_names, r)) for r in cur.fetchall()]
    finally:
        db.close()

    return {"rows": rows, "total": total, "page": page, "limit": limit}
