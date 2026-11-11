"""
P230 / P231: one read-only way to query every database NousViz reads.

Alerts, alert previews, the alert column pickers and insights all read data
that may live in Postgres, ClickHouse or MySQL. This module gives them one
interface per engine, so none of them writes engine-specific connection
code, and every read gets the same guarantees:

  * read-only, enforced by the engine itself, not only by our checks:
      - Postgres:   a READ ONLY transaction (plus the nousviz_query role
                    for SQL a plugin wrote: alerts.yaml, insights.yaml);
      - ClickHouse: HTTP GET, which ClickHouse always runs read-only;
      - MySQL:      START TRANSACTION READ ONLY;
  * a timeout and a row cap on every query;
  * values are bound parameters, never pasted into SQL;
  * credentials stay server-side: they are read from the `connections`
    table (or core's .env for core Postgres) and never returned.

Connection resolution (`resolve`):

  * core Postgres:          engine "postgres", no connection id;
  * a registered connection: its `type` and `config`;
  * a plugin dataset whose `db` isn't postgres: core's default connection
    of that engine. This is the convention dashboards already follow
    ("dashboards read through core's default ClickHouse connection").

ClickHouse tables are found by name across databases when the default
database doesn't hold them: each plugin keeps its own database
(e.g. `statsdrone_benchmark`), while the default connection points at
`default`. A plugin dataset can name its `database:` to remove any doubt.

Everything here is stdlib + psycopg2 (+ pymysql when MySQL is used), like
routes/query.py, so no new dependency is needed.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

logger = logging.getLogger("nousviz.query_drivers")

DEFAULT_TIMEOUT_S = 30
DEFAULT_MAX_ROWS = 10_000
ENGINES = ("postgres", "clickhouse", "mysql")

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


class QueryError(RuntimeError):
    """A query could not run. The message is safe to show to an operator."""


class ConnectionMissing(QueryError):
    """No usable connection for the engine (none configured, or not found)."""


# ── Column metadata ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    kind: str  # date | datetime | number | text | bool | other

    def as_dict(self) -> dict:
        return {"name": self.name, "type": self.type, "kind": self.kind}


def column_kind(type_name: str) -> str:
    """Map an engine type name to a coarse kind the builder and SQL use."""
    t = (type_name or "").lower()
    # ClickHouse wrappers: Nullable(T), LowCardinality(T), LowCardinality(Nullable(T))
    while True:
        m = re.match(r"^(nullable|lowcardinality)\((.*)\)$", t)
        if not m:
            break
        t = m.group(2)
    if t.startswith("datetime") or t.startswith("timestamp"):
        return "datetime"
    if t == "date" or t.startswith("date32") or t == "date":
        return "date"
    if t in ("bool", "boolean", "tinyint(1)"):
        return "bool"
    if re.match(r"^(u?int\d*|int|integer|bigint|smallint|tinyint|mediumint|serial|bigserial|"
                r"float\d*|double( precision)?|real|numeric|decimal|money)", t):
        return "number"
    if re.match(r"^(text|varchar|character varying|char|character|string|fixedstring|uuid|enum|"
                r"citext|name|tinytext|mediumtext|longtext)", t):
        return "text"
    return "other"


def valid_ident(name: str) -> bool:
    return bool(name) and bool(_IDENT.match(name))


# ── Dialects ────────────────────────────────────────────────────────────────

AGGREGATIONS = ("sum", "avg", "min", "max", "count", "count_distinct")


class Dialect:
    """How one engine spells the pieces the alert SQL builder needs."""

    engine = "postgres"

    def quote(self, ident: str) -> str:
        if not valid_ident(ident):
            raise QueryError(f"Invalid identifier: {ident!r}")
        return f'"{ident}"'

    def table(self, database: Optional[str], name: str) -> str:
        return (self.quote(database) + "." if database else "") + self.quote(name)

    def placeholder(self, name: str, kind: str) -> str:
        return f"%({name})s"

    def in_list(self, col_sql: str, ph: str, negate: bool = False) -> str:
        return f"{'NOT ' if negate else ''}({col_sql} = ANY({ph}))"

    def contains(self, col_sql: str, ph: str) -> str:
        return f"{col_sql}::text ILIKE {ph}"

    def as_date(self, col_sql: str, kind: str) -> str:
        return col_sql  # Postgres compares timestamps with dates directly

    def agg(self, fn: str, expr: Optional[str], cond: Optional[str] = None) -> str:
        if fn not in AGGREGATIONS:
            raise QueryError(f"Unsupported aggregation: {fn}")
        if fn == "count" and expr is None:
            inner = "count(*)"
        elif fn == "count_distinct":
            inner = f"count(DISTINCT {expr})"
        else:
            inner = f"{fn}({expr})"
        return f"{inner} FILTER (WHERE {cond})" if cond else inner

    def safe_div(self, a: str, b: str) -> str:
        return f"({a})::double precision / NULLIF({b}, 0)"

    def text_not_empty(self, col_sql: str) -> str:
        return f"{col_sql} IS NOT NULL AND {col_sql}::text <> ''"

    def is_empty(self, col_sql: str, negate: bool) -> str:
        if negate:
            return f"({col_sql} IS NOT NULL AND {col_sql}::text <> '')"
        return f"({col_sql} IS NULL OR {col_sql}::text = '')"

    def from_clause(self, table_sql: str, final: bool) -> str:
        return table_sql


class ClickHouseDialect(Dialect):
    engine = "clickhouse"

    _CH_TYPES = {"number": "Float64", "date": "Date", "datetime": "Date", "text": "String",
                 "bool": "UInt8", "other": "String", "int": "Int64",
                 "list_text": "Array(String)", "list_number": "Array(Float64)"}

    def quote(self, ident: str) -> str:
        if not valid_ident(ident):
            raise QueryError(f"Invalid identifier: {ident!r}")
        return f"`{ident}`"

    def placeholder(self, name: str, kind: str) -> str:
        return "{" + name + ":" + self._CH_TYPES.get(kind, "String") + "}"

    def in_list(self, col_sql: str, ph: str, negate: bool = False) -> str:
        return f"{'NOT ' if negate else ''}has({ph}, {col_sql})"

    def contains(self, col_sql: str, ph: str) -> str:
        return f"toString({col_sql}) ILIKE {ph}"

    def as_date(self, col_sql: str, kind: str) -> str:
        return f"toDate({col_sql})" if kind == "datetime" else col_sql

    def agg(self, fn: str, expr: Optional[str], cond: Optional[str] = None) -> str:
        if fn not in AGGREGATIONS:
            raise QueryError(f"Unsupported aggregation: {fn}")
        if fn == "count" and expr is None:
            return f"countIf({cond})" if cond else "count()"
        if fn == "count":
            return f"countIf({expr} IS NOT NULL AND ({cond}))" if cond else f"count({expr})"
        name = {"count_distinct": "uniqExact"}.get(fn, fn)
        return f"{name}If({expr}, {cond})" if cond else f"{name}({expr})"

    def safe_div(self, a: str, b: str) -> str:
        return f"toFloat64({a}) / nullIf(toFloat64({b}), 0)"

    def text_not_empty(self, col_sql: str) -> str:
        return f"{col_sql} IS NOT NULL AND toString({col_sql}) != ''"

    def is_empty(self, col_sql: str, negate: bool) -> str:
        if negate:
            return f"({col_sql} IS NOT NULL AND toString({col_sql}) != '')"
        return f"({col_sql} IS NULL OR toString({col_sql}) = '')"

    def from_clause(self, table_sql: str, final: bool) -> str:
        return f"{table_sql} FINAL" if final else table_sql


class MySQLDialect(Dialect):
    engine = "mysql"

    def quote(self, ident: str) -> str:
        if not valid_ident(ident):
            raise QueryError(f"Invalid identifier: {ident!r}")
        return f"`{ident}`"

    def in_list(self, col_sql: str, ph: str, negate: bool = False) -> str:
        # pymysql renders a tuple parameter as (a, b, c).
        return f"{col_sql} {'NOT ' if negate else ''}IN {ph}"

    def contains(self, col_sql: str, ph: str) -> str:
        return f"{col_sql} LIKE {ph}"

    def as_date(self, col_sql: str, kind: str) -> str:
        return f"DATE({col_sql})" if kind == "datetime" else col_sql

    def agg(self, fn: str, expr: Optional[str], cond: Optional[str] = None) -> str:
        if fn not in AGGREGATIONS:
            raise QueryError(f"Unsupported aggregation: {fn}")
        if fn == "count" and expr is None:
            return f"COUNT(CASE WHEN {cond} THEN 1 END)" if cond else "COUNT(*)"
        if fn == "count_distinct":
            return f"COUNT(DISTINCT CASE WHEN {cond} THEN {expr} END)" if cond else f"COUNT(DISTINCT {expr})"
        name = fn.upper()
        return f"{name}(CASE WHEN {cond} THEN {expr} END)" if cond else f"{name}({expr})"

    def safe_div(self, a: str, b: str) -> str:
        return f"({a}) / NULLIF({b}, 0)"

    def text_not_empty(self, col_sql: str) -> str:
        return f"{col_sql} IS NOT NULL AND {col_sql} <> ''"

    def is_empty(self, col_sql: str, negate: bool) -> str:
        if negate:
            return f"({col_sql} IS NOT NULL AND {col_sql} <> '')"
        return f"({col_sql} IS NULL OR {col_sql} = '')"


DIALECTS: dict[str, Dialect] = {
    "postgres": Dialect(),
    "clickhouse": ClickHouseDialect(),
    "mysql": MySQLDialect(),
}


def dialect_for(engine: str) -> Dialect:
    try:
        return DIALECTS[engine]
    except KeyError:
        raise QueryError(f"No driver for database type '{engine}'.")


# ── Drivers ─────────────────────────────────────────────────────────────────

@dataclass
class TableRef:
    """A resolved table: where it is and how to read it."""
    name: str
    database: Optional[str] = None
    engine_name: Optional[str] = None   # ClickHouse table engine, e.g. ReplacingMergeTree

    @property
    def needs_final(self) -> bool:
        e = (self.engine_name or "")
        return "ReplacingMergeTree" in e or "CollapsingMergeTree" in e or "SummingMergeTree" in e \
            or "AggregatingMergeTree" in e


class QueryDriver:
    engine = "postgres"

    def __init__(self, config: Optional[dict] = None, *, label: str = ""):
        self.config = dict(config or {})
        self.label = label
        self.dialect = dialect_for(self.engine)

    # Subclasses implement these three.
    def run(self, sql: str, params: Optional[dict] = None, *, timeout_s: int = DEFAULT_TIMEOUT_S,
            max_rows: int = DEFAULT_MAX_ROWS, sandbox_role: bool = False) -> list[dict]:
        raise NotImplementedError

    def columns(self, table: TableRef) -> list[ColumnInfo]:
        raise NotImplementedError

    def locate(self, name: str, database: Optional[str] = None) -> TableRef:
        raise NotImplementedError

    def list_tables(self, limit: int = 500) -> list[str]:
        raise NotImplementedError

    def distinct_values(self, table: TableRef, column: str, limit: int = 50) -> list[Any]:
        d = self.dialect
        col = d.quote(column)
        sql = (f"SELECT {col} AS v, count(*) AS n FROM {d.from_clause(d.table(table.database, table.name), table.needs_final)} "
               f"WHERE {d.text_not_empty(col)} GROUP BY {col} ORDER BY n DESC LIMIT {int(limit)}")
        return [r["v"] for r in self.run(sql, {}, timeout_s=10, max_rows=limit)]


def _jsonable(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if hasattr(v, "__float__") and not isinstance(v, (int, float, bool)):
        try:
            return float(v)
        except Exception:  # noqa: BLE001
            return str(v)
    return v


class PostgresDriver(QueryDriver):
    engine = "postgres"

    def _connect(self):
        import psycopg2
        cfg = self.config
        if cfg:   # a registered Postgres connection
            return psycopg2.connect(
                host=cfg.get("host", "localhost"), port=int(cfg.get("port", 5432)),
                dbname=cfg.get("database") or cfg.get("dbname") or "postgres",
                user=cfg.get("user", ""), password=cfg.get("password", ""),
                connect_timeout=5, sslmode=cfg.get("sslmode", "prefer"),
            )
        password = os.environ.get("POSTGRES_PASSWORD")
        if not password:
            raise ConnectionMissing("POSTGRES_PASSWORD is not set.")
        return psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "nousviz"),
            user=os.environ.get("POSTGRES_USER", "nousviz"),
            password=password, connect_timeout=5,
            sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
        )

    def run(self, sql, params=None, *, timeout_s=DEFAULT_TIMEOUT_S, max_rows=DEFAULT_MAX_ROWS,
            sandbox_role=False):
        conn = self._connect()
        try:
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("SET TRANSACTION READ ONLY")
            if sandbox_role and not self.config:
                cur.execute("SET LOCAL ROLE nousviz_query")
            cur.execute(f"SET LOCAL statement_timeout = '{int(timeout_s) * 1000}ms'")
            try:
                cur.execute(sql, _pg_params(params))
            except Exception as e:  # noqa: BLE001
                raise QueryError(_first_line(e)) from None
            cols = [c[0] for c in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows)
            return [{k: _jsonable(v) for k, v in zip(cols, r)} for r in rows]
        finally:
            try:
                conn.rollback()
            finally:
                conn.close()

    def locate(self, name, database=None):
        schema = database or "public"
        rows = self.run(
            "SELECT table_schema, table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = %(s)s AND table_name = %(t)s", {"s": schema, "t": name}, timeout_s=10)
        if not rows:
            raise QueryError(f"Table '{name}' not found in Postgres.")
        return TableRef(name=name, database=None if schema == "public" else schema,
                        engine_name=rows[0]["table_type"])

    def list_tables(self, limit=500):
        rows = self.run(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY 1, 2 LIMIT %(n)s",
            {"n": int(limit)}, timeout_s=10)
        return [r["table_name"] if r["table_schema"] == "public" else f"{r['table_schema']}.{r['table_name']}"
                for r in rows]

    def columns(self, table):
        rows = self.run(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %(s)s AND table_name = %(t)s ORDER BY ordinal_position",
            {"s": table.database or "public", "t": table.name}, timeout_s=10)
        return [ColumnInfo(r["column_name"], r["data_type"], column_kind(r["data_type"])) for r in rows]


def _pg_params(params: Optional[dict]) -> Optional[dict]:
    if not params:
        return None
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in params.items()}


class ClickHouseDriver(QueryDriver):
    engine = "clickhouse"

    def _request(self, sql: str, params: dict, settings: dict) -> urllib.request.Request:
        cfg = self.config
        q: dict[str, str] = {"query": sql.rstrip().rstrip(";") + "\nFORMAT JSON"}
        if cfg.get("database"):
            q["database"] = str(cfg["database"])
        for k, v in settings.items():
            q[k] = str(v)
        for k, v in (params or {}).items():
            q[f"param_{k}"] = _ch_param(v)
        headers = {}
        if cfg.get("user"):
            headers["X-ClickHouse-User"] = str(cfg["user"])
        if cfg.get("password"):
            headers["X-ClickHouse-Key"] = str(cfg["password"])   # never in the URL (B338)
        scheme = "https" if str(cfg.get("secure", "")).lower() in ("1", "true", "yes") else "http"
        url = f"{scheme}://{cfg.get('host', 'localhost')}:{int(cfg.get('port', 8123))}/?{urllib.parse.urlencode(q)}"
        # GET: ClickHouse runs every GET request read-only, whatever the user's grants.
        return urllib.request.Request(url, headers=headers, method="GET")

    def run(self, sql, params=None, *, timeout_s=DEFAULT_TIMEOUT_S, max_rows=DEFAULT_MAX_ROWS,
            sandbox_role=False):
        settings = {"max_execution_time": int(timeout_s), "max_result_rows": int(max_rows) + 1,
                    "result_overflow_mode": "break"}
        try:
            data = self._send(sql, params or {}, settings, timeout_s)
        except QueryError as e:
            # A user set to readonly=1 may not change any setting: retry once
            # without them; the socket timeout and the row slice still apply.
            if "readonly" in str(e).lower() and "setting" in str(e).lower():
                data = self._send(sql, params or {}, {}, timeout_s)
            else:
                raise
        return [{k: _jsonable(v) for k, v in row.items()} for row in data.get("data", [])[:max_rows]]

    def _send(self, sql, params, settings, timeout_s) -> dict:
        try:
            with urllib.request.urlopen(self._request(sql, params, settings), timeout=timeout_s + 5) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            raise QueryError(f"ClickHouse: {_first_line(detail)}") from None
        except urllib.error.URLError as e:
            raise ConnectionMissing(f"ClickHouse is not reachable ({getattr(e, 'reason', e)}).") from None
        except TimeoutError:
            raise QueryError(f"ClickHouse query took longer than {timeout_s}s.") from None

    def locate(self, name, database=None):
        if database:
            rows = self.run("SELECT database, name, engine FROM system.tables WHERE database = {d:String} "
                            "AND name = {t:String}", {"d": database, "t": name}, timeout_s=10)
        else:
            rows = self.run("SELECT database, name, engine FROM system.tables WHERE name = {t:String} "
                            "ORDER BY database = currentDatabase() DESC, database", {"t": name}, timeout_s=10)
        rows = [r for r in rows if r["database"] not in ("system", "INFORMATION_SCHEMA", "information_schema")]
        if not rows:
            raise QueryError(f"Table '{name}' not found in ClickHouse.")
        default_db = self.config.get("database") or "default"
        if not database and len(rows) > 1 and rows[0]["database"] != default_db:
            dbs = ", ".join(r["database"] for r in rows)
            raise QueryError(f"Table '{name}' exists in several ClickHouse databases ({dbs}); "
                             f"the dataset must name its database.")
        r = rows[0]
        return TableRef(name=name, database=r["database"], engine_name=r["engine"])

    def list_tables(self, limit=500):
        rows = self.run("SELECT database, name FROM system.tables WHERE database NOT IN "
                        "('system', 'INFORMATION_SCHEMA', 'information_schema') AND NOT is_temporary "
                        "ORDER BY database, name LIMIT {n:UInt32}", {"n": int(limit)}, timeout_s=10)
        return [f"{r['database']}.{r['name']}" for r in rows]

    def columns(self, table):
        rows = self.run("SELECT name, type FROM system.columns WHERE database = {d:String} AND table = {t:String} "
                        "ORDER BY position", {"d": table.database or "default", "t": table.name}, timeout_s=10)
        return [ColumnInfo(r["name"], r["type"], column_kind(r["type"])) for r in rows]


def _ch_param(v: Any) -> str:
    if isinstance(v, (list, tuple, set)):
        return "[" + ",".join(_ch_literal(x) for x in v) + "]"
    if isinstance(v, (datetime, date)):
        return v.isoformat()[:10] if isinstance(v, date) and not isinstance(v, datetime) else v.isoformat()
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def _ch_literal(x: Any) -> str:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return repr(x)
    s = str(x).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


class MySQLDriver(QueryDriver):
    engine = "mysql"

    def _connect(self, timeout_s: int):
        try:
            import pymysql
        except ImportError:
            raise ConnectionMissing("pymysql is not installed on this server (pip install pymysql).") from None
        cfg = self.config
        return pymysql.connect(
            host=cfg.get("host", "localhost"), port=int(cfg.get("port", 3306)),
            user=cfg.get("user", ""), password=cfg.get("password", ""), database=cfg.get("database", ""),
            connect_timeout=5, read_timeout=timeout_s + 5, cursorclass=pymysql.cursors.DictCursor,
        )

    def run(self, sql, params=None, *, timeout_s=DEFAULT_TIMEOUT_S, max_rows=DEFAULT_MAX_ROWS,
            sandbox_role=False):
        try:
            conn = self._connect(timeout_s)
        except ConnectionMissing:
            raise
        except Exception as e:  # noqa: BLE001
            raise ConnectionMissing(f"MySQL is not reachable ({_first_line(e)}).") from None
        try:
            cur = conn.cursor()
            try:
                cur.execute(f"SET SESSION max_execution_time = {int(timeout_s) * 1000}")
            except Exception:  # noqa: BLE001 — MariaDB spells it max_statement_time
                try:
                    cur.execute(f"SET SESSION max_statement_time = {int(timeout_s)}")
                except Exception:  # noqa: BLE001
                    pass
            cur.execute("START TRANSACTION READ ONLY")
            try:
                cur.execute(sql, {k: (tuple(v) if isinstance(v, (list, set)) else v)
                                  for k, v in (params or {}).items()} or None)
            except Exception as e:  # noqa: BLE001
                raise QueryError(f"MySQL: {_first_line(e)}") from None
            rows = cur.fetchmany(max_rows)
            return [{k: _jsonable(v) for k, v in r.items()} for r in rows]
        finally:
            try:
                conn.rollback()
            finally:
                conn.close()

    def locate(self, name, database=None):
        rows = self.run("SELECT table_schema, table_name, engine FROM information_schema.tables "
                        "WHERE table_schema = COALESCE(%(d)s, DATABASE()) AND table_name = %(t)s",
                        {"d": database, "t": name}, timeout_s=10)
        if not rows:
            raise QueryError(f"Table '{name}' not found in MySQL.")
        r = {k.lower(): v for k, v in rows[0].items()}
        return TableRef(name=name, database=database, engine_name=r.get("engine"))

    def list_tables(self, limit=500):
        rows = self.run("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() "
                        "ORDER BY table_name LIMIT %(n)s", {"n": int(limit)}, timeout_s=10)
        return [list(r.values())[0] for r in rows]

    def columns(self, table):
        rows = self.run("SELECT column_name, column_type FROM information_schema.columns "
                        "WHERE table_schema = COALESCE(%(d)s, DATABASE()) AND table_name = %(t)s "
                        "ORDER BY ordinal_position", {"d": table.database, "t": table.name}, timeout_s=10)
        out = []
        for r in rows:
            r = {k.lower(): v for k, v in r.items()}
            out.append(ColumnInfo(r["column_name"], r["column_type"], column_kind(r["column_type"])))
        return out


DRIVERS: dict[str, type[QueryDriver]] = {
    "postgres": PostgresDriver,
    "clickhouse": ClickHouseDriver,
    "mysql": MySQLDriver,
}


def register_driver(engine: str, cls: type[QueryDriver], dialect: Optional[Dialect] = None) -> None:
    """Let a utility plugin add an engine (phase 6 hook)."""
    DRIVERS[engine] = cls
    if dialect is not None:
        DIALECTS[engine] = dialect


def _first_line(e: Any) -> str:
    return str(e).strip().splitlines()[0][:300] if str(e).strip() else e.__class__.__name__


# ── Connection resolution ───────────────────────────────────────────────────

def _connection_row(cur, *, connection_id: Optional[str] = None, engine: Optional[str] = None):
    if connection_id:
        cur.execute("SELECT id, name, type, config, is_active FROM connections WHERE id::text = %s",
                    (str(connection_id),))
    else:
        cur.execute("SELECT id, name, type, config, is_active FROM connections WHERE type = %s "
                    "ORDER BY is_default DESC, created_at LIMIT 1", (engine,))
    return cur.fetchone()


def get_driver(engine: str, *, connection_id: Optional[str] = None, pg_cursor=None) -> QueryDriver:
    """A driver for `engine`, connected to `connection_id` or the engine's default.

    Core Postgres needs no connection row. Anything else reads the
    `connections` table through `pg_cursor` (or its own core connection).
    """
    engine = (engine or "postgres").lower()
    if engine not in DRIVERS:
        raise ConnectionMissing(f"No driver for database type '{engine}'.")
    if engine == "postgres" and not connection_id:
        return DRIVERS["postgres"]()

    def lookup(cur):
        return _connection_row(cur, connection_id=connection_id, engine=engine)

    if pg_cursor is not None:
        row = lookup(pg_cursor)
    else:
        conn = PostgresDriver()._connect()
        try:
            row = lookup(conn.cursor())
        finally:
            conn.close()
    if not row:
        what = "that connection" if connection_id else f"a {engine} connection"
        raise ConnectionMissing(f"No {engine} connection: add {what} on the Connections page"
                                + (" (or install the ClickHouse utility)." if engine == "clickhouse" else "."))
    _id, name, typ, cfg, is_active = row
    if is_active is False:
        raise ConnectionMissing(f"The connection '{name}' is switched off.")
    if typ != engine:
        raise ConnectionMissing(f"The connection '{name}' is {typ}, not {engine}.")
    if isinstance(cfg, str):
        cfg = json.loads(cfg or "{}")
    return DRIVERS[engine](cfg or {}, label=name)


def engine_available(engine: str, pg_cursor) -> tuple[bool, str]:
    """(available, reason) without running a query on the engine."""
    engine = (engine or "postgres").lower()
    if engine == "postgres":
        return True, ""
    if engine not in DRIVERS:
        return False, f"No driver for database type '{engine}'."
    try:
        row = _connection_row(pg_cursor, engine=engine)
    except Exception:  # noqa: BLE001
        return False, "Connections table is not readable."
    if not row:
        hint = " Install the ClickHouse utility or add a connection." if engine == "clickhouse" else \
            " Add one on the Connections page."
        return False, f"No {engine} connection.{hint}"
    if row[4] is False:
        return False, f"The {engine} connection '{row[1]}' is switched off."
    return True, ""


__all__ = [
    "AGGREGATIONS", "ColumnInfo", "ConnectionMissing", "DEFAULT_MAX_ROWS", "DEFAULT_TIMEOUT_S", "DIALECTS",
    "DRIVERS", "Dialect", "QueryDriver", "QueryError", "TableRef", "column_kind", "dialect_for",
    "engine_available", "get_driver", "register_driver", "valid_ident",
]
