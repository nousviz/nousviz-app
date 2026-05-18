"""
/api/query — SQL query proxy (Postgres)

Accepts SQL queries from the frontend and returns JSON results.
Includes guardrails to prevent slow queries, excessive data, and writes.
"""

import os
import re
import logging
import time

import yaml
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn
from ..rbac import requires, register_route

# When true, verbose Postgres error detail is returned to the client. Off by default
# so error messages don't leak table/column/constraint names to query callers.
_DEBUG_QUERY_ERRORS = os.environ.get("NOUSVIZ_DEBUG_QUERY_ERRORS", "false").lower() == "true"

# Build allowlist of tables that can be queried without authentication
# (plugin-declared tables only — core tables require auth)
_PLUGINS_DIR = Path(__file__).resolve().parents[4] / "plugins" / "installed"
def _get_allowed_tables() -> set[str]:
    """Tables declared in installed plugin manifests — safe for unauthenticated queries.
    Rebuilt on every call so install/uninstall takes effect without restart."""
    tables = set()
    if _PLUGINS_DIR.exists():
        for manifest in _PLUGINS_DIR.glob("*/plugin.yaml"):
            try:
                data = yaml.safe_load(manifest.read_text())
                for db in (data.get("databases") or {}).values():
                    for t in (db.get("tables") or []):
                        tables.add(t.lower())
            except Exception:
                pass
    return tables

def _get_plugin_tables(plugin_id: str) -> set[str]:
    """Tables declared by a specific plugin — used for per-plugin access boundaries."""
    tables = set()
    manifest = _PLUGINS_DIR / plugin_id / "plugin.yaml"
    if manifest.exists():
        try:
            data = yaml.safe_load(manifest.read_text())
            for db in (data.get("databases") or {}).values():
                for t in (db.get("tables") or []):
                    tables.add(t.lower())
        except Exception:
            pass
    return tables


logger = logging.getLogger("nousviz.api.query")


def _registered_capabilities_cache() -> set[str]:
    """Check registered capabilities from installed utility plugins."""
    caps = set()
    if _PLUGINS_DIR.exists():
        for manifest in _PLUGINS_DIR.glob("*/plugin.yaml"):
            try:
                data = yaml.safe_load(manifest.read_text())
                if data.get("type") == "utility":
                    for c in (data.get("provides") or []):
                        caps.add(c)
            except Exception:
                pass
    return caps


async def _query_external(engine: str, req: "QueryRequest") -> "QueryResponse":
    """Route query to an external database (ClickHouse, MySQL) via named connections."""
    import json as _json
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT config FROM connections WHERE type = %s AND is_default = true", (engine,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(503, f"No default {engine} connection configured. Add one on the Connections page.")

    cfg = row[0] if isinstance(row[0], dict) else _json.loads(row[0])

    if engine == "clickhouse":
        import urllib.request
        host = cfg.get("host", "localhost")
        port = cfg.get("port", 8123)
        sql = req.sql.strip().rstrip(";")
        url = f"http://{host}:{port}/?query={urllib.parse.quote(sql + ' FORMAT JSON')}"
        if cfg.get("user"):
            url += f"&user={cfg['user']}"
        if cfg.get("password"):
            url += f"&password={cfg['password']}"
        if cfg.get("database"):
            url += f"&database={cfg['database']}"
        try:
            import time
            start = time.time()
            res = urllib.request.urlopen(url, timeout=30)
            data = _json.loads(res.read())
            elapsed = (time.time() - start) * 1000
            rows = data.get("data", [])
            columns = [m["name"] for m in data.get("meta", [])]
            types = [m["type"] for m in data.get("meta", [])]
            return QueryResponse(
                columns=columns, types=types, rows=rows,
                row_count=len(rows), elapsed_ms=round(elapsed, 2),
                db_engine=engine,
            )
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:500]
            raise HTTPException(400, f"ClickHouse error: {detail}")

    elif engine == "mysql":
        try:
            import pymysql
        except ImportError:
            raise HTTPException(503, "pymysql not installed. Run: pip install pymysql")
        import time
        start = time.time()
        c = pymysql.connect(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 3306)),
            user=cfg.get("user", ""),
            password=cfg.get("password", ""),
            database=cfg.get("database", ""),
            connect_timeout=5,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = c.cursor()
        cur.execute(req.sql.strip().rstrip(";"))
        rows = cur.fetchall()
        elapsed = (time.time() - start) * 1000
        columns = [d[0] for d in cur.description] if cur.description else []
        types = [str(d[1]) for d in cur.description] if cur.description else []
        c.close()
        return QueryResponse(
            columns=columns, types=types, rows=list(rows),
            row_count=len(rows), elapsed_ms=round(elapsed, 2),
            db_engine=engine,
        )

    raise HTTPException(400, f"Engine {engine} not implemented")

router = APIRouter(tags=["query"])

# B228: register the query endpoint (silent-leak fix).
register_route("POST", "/api/query", "query.run")

# ── Guardrails ────────────────────────────────────────────────────────

MAX_ROWS = 10_000           # Hard limit on rows returned
MAX_RESPONSE_ROWS = 10_000  # Same as MAX_ROWS for now
QUERY_TIMEOUT_SEC = 30      # Query timeout in seconds
MAX_EXPORT_ROWS = 100_000   # For explicit export queries
DEFAULT_LIMIT = 1_000       # Applied when no LIMIT in query

# Block destructive statements
BLOCKED_PATTERNS = re.compile(
    r"\b(DROP|TRUNCATE|ALTER|DELETE|INSERT|UPDATE|CREATE|ATTACH|DETACH|RENAME|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

# Postgres-only: block access to internal application tables regardless of operation
PG_BLOCKED_TABLES = re.compile(
    r"\b(users|user_sessions|user_activity|api_keys|alert_rules)\b",
    re.IGNORECASE,
)

# Detect if query already has a LIMIT
LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


class QueryRequest(BaseModel):
    sql: str
    database: str | None = None
    db_engine: str | None = None  # "postgres" (default), "clickhouse", "mysql"
    max_rows: int | None = None  # Client can request a specific limit (up to MAX_ROWS)


class QueryResponse(BaseModel):
    columns: list[str]
    types: list[str]
    rows: list[dict]
    row_count: int
    total_rows_available: int | None = None
    truncated: bool = False
    elapsed_ms: float
    db_engine: str = "postgres"
    guardrails: dict | None = None


def _enforce_limit(sql: str, max_rows: int) -> str:
    """Add LIMIT to queries that don't have one, or cap existing limits."""
    if LIMIT_PATTERN.search(sql):
        # Query has a LIMIT — check if it's too high
        def cap_limit(match: re.Match) -> str:
            existing = int(re.search(r"\d+", match.group()).group())
            return f"LIMIT {min(existing, max_rows)}"
        return LIMIT_PATTERN.sub(cap_limit, sql)
    else:
        # No LIMIT — add one
        return f"{sql} LIMIT {max_rows}"


@router.post("/query", response_model=QueryResponse, operation_id="query.execute")
async def execute_query(
    req: QueryRequest,
    request: Request,
    _: None = Depends(requires("query.run")),
):
    """Execute a read-only SQL query against the specified engine."""
    # Engine routing — default to postgres
    engine = (req.db_engine or "postgres").lower()
    if engine not in ("postgres", "clickhouse", "mysql"):
        raise HTTPException(400, f"Unknown db_engine: {engine}. Use postgres, clickhouse, or mysql.")
    if engine != "postgres":
        # Check if the capability is registered
        if engine not in _registered_capabilities_cache():
            raise HTTPException(503, f"{engine} is not installed. Install the {engine.title()} utility plugin first.")
        # Route to the appropriate connection
        try:
            return await _query_external(engine, req)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"{engine} query failed: {e}")
            raise HTTPException(400, f"Query failed on {engine}. Check server logs.")

    sql = req.sql.strip().rstrip(";")

    if not sql:
        raise HTTPException(status_code=400, detail="Empty query")

    # Block writes
    if BLOCKED_PATTERNS.search(sql):
        raise HTTPException(
            status_code=403,
            detail="Write operations are not allowed through the query API",
        )

    # S101: validate the token, don't just check header presence. Previously,
    # sending any fake `X-Session-Token: garbage` bypassed the unauthenticated
    # table allowlist. Now only callers with valid session tokens or valid API
    # keys are treated as authenticated.
    from ..middleware.auth import get_authenticated_identity
    is_authenticated = get_authenticated_identity(request) is not None
    if not is_authenticated:
        allowed = _get_allowed_tables()
        if allowed:
            sql_lower = sql.lower()
            # Extract all table references — FROM, JOIN, subqueries, CTEs, schema-qualified
            # Pattern catches: FROM table, JOIN table, FROM public.table, FROM (SELECT...FROM table)
            from_tables = re.findall(r'\bfrom\s+(?:public\.)?([\w]+)|\bjoin\s+(?:public\.)?([\w]+)', sql_lower)
            referenced = {t for pair in from_tables for t in pair if t}
            # Also check the PG_BLOCKED_TABLES as second defense
            if PG_BLOCKED_TABLES.search(sql):
                raise HTTPException(
                    status_code=403,
                    detail="Access to internal application tables is not permitted",
                )
            disallowed = referenced - allowed - {"information_schema", "pg_catalog"}
            if disallowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthenticated queries can only access plugin tables. Blocked: {', '.join(disallowed)}",
                )

    # B305.1 (v0.10.0.6.1): authenticated viewers / analysts with a
    # per-user plugin allowlist must not be able to query tables owned
    # by plugins they cannot see. Admins/superadmins bypass; users with
    # no ACL rows pass through. Reuses the same regex as the
    # unauthenticated branch above.
    if is_authenticated:
        from .auth import get_me
        from .. import catalog as _catalog
        from ..rbac import user_can_access_plugin

        try:
            current_user = get_me(request)
        except HTTPException:
            current_user = None
        if current_user and current_user.get("role") not in ("admin", "superadmin"):
            sql_lower = sql.lower()
            from_tables = re.findall(
                r'\bfrom\s+(?:public\.)?([\w]+)|\bjoin\s+(?:public\.)?([\w]+)',
                sql_lower,
            )
            referenced = {t for pair in from_tables for t in pair if t}
            if referenced:
                try:
                    ownership = _catalog._build_plugin_ownership_map()
                except Exception:
                    ownership = {}
                disallowed_plugins: set[str] = set()
                for tbl in referenced:
                    owner = ownership.get(tbl)
                    if not owner:
                        continue  # core / information_schema / pg_catalog
                    if not user_can_access_plugin(
                        current_user.get("id"), current_user.get("role"), owner
                    ):
                        disallowed_plugins.add(owner)
                if disallowed_plugins:
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Query references plugin tables you do not have "
                            f"access to: {', '.join(sorted(disallowed_plugins))}"
                        ),
                    )

    # Determine row limit
    requested_max = min(max(req.max_rows or MAX_ROWS, 1), MAX_ROWS)

    # Enforce LIMIT on the query
    safe_sql = _enforce_limit(sql, requested_max)

    guardrails_applied = {}
    if safe_sql != sql:
        guardrails_applied["limit_enforced"] = requested_max

    # ── Postgres query ─────────────────────────────────────────────────
    if PG_BLOCKED_TABLES.search(sql):
        raise HTTPException(
            status_code=403,
            detail="Access to internal application tables is not permitted through the query API",
        )
    try:
        start_time = time.time()
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SET statement_timeout = '{QUERY_TIMEOUT_SEC}s'")
            cur.execute("SET search_path = public")

            # Unauthenticated queries run under the nousviz_query role which
            # has SELECT-only grants on plugin tables. Startup check in main.py
            # (S104) guarantees the role exists — if this SET fails, fail the
            # request rather than silently falling back to regex-only guards
            # (bypassable via CTEs / information_schema / UNION).
            use_readonly = not is_authenticated
            role_set = False
            if use_readonly:
                cur.execute("SET LOCAL ROLE nousviz_query")
                role_set = True

            cur.execute(safe_sql)

            elapsed = (time.time() - start_time) * 1000

            columns = [d[0] for d in cur.description]
            types = [str(d[1]) for d in cur.description]

            rows = []
            for row_data in cur.fetchall():
                row = {}
                for i, col in enumerate(columns):
                    val = row_data[i]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif isinstance(val, (bytes, memoryview)):
                        val = str(val)
                    from decimal import Decimal
                    if isinstance(val, Decimal):
                        val = float(val)
                    row[col] = val
                rows.append(row)

            truncated = len(rows) >= requested_max
            if elapsed > 5000:
                guardrails_applied["slow_query_ms"] = round(elapsed, 1)

            return QueryResponse(
                columns=columns,
                types=types,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                elapsed_ms=round(elapsed, 2),
                guardrails=guardrails_applied if guardrails_applied else None,
            )
    except Exception as e:
        logger.error(f"Postgres query failed: {e}", exc_info=True)
        detail = str(e) if _DEBUG_QUERY_ERRORS else "Query failed. See server logs for details."
        raise HTTPException(status_code=400, detail=detail)
