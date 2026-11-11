"""
P230: what an alert source id means, decided on the server.

The builder sends a source id; the server works out the engine, the
connection, the table and whether the source may be alerted on. A request
can't point an alert at an arbitrary connection or table, or around a
plugin's `alertable: false`.

Source ids:

  pg:<table>                         a table in core Postgres
  plugin:<plugin_id>:<dataset>       a dataset a plugin declares (`datasets:`)
  conn:<connection_uuid>             a registered connection; the table is
                                     chosen separately and must exist there
  query:<plugin_id>:<query_id>       a ready-made query from a plugin's alerts.yaml
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .query_drivers import DRIVERS, valid_ident

_UUID = re.compile(r"^[0-9a-fA-F-]{32,36}$")
_SLUG = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


class SourceError(ValueError):
    """The source id or table is not usable. The message is shown to the user."""


@dataclass
class ResolvedSource:
    source_id: str
    source_kind: str               # table | plugin_dataset | connection_table | plugin_query
    engine: str
    connection_id: Optional[str]
    plugin_id: str
    table: str                     # may be "" for a connection until a table is chosen
    database: Optional[str]
    alertable: bool = True
    date_column: Optional[str] = None
    currency_column: Optional[str] = None
    query_id: Optional[str] = None

    @property
    def dataset(self) -> str:
        return f"{self.database}.{self.table}" if self.database else self.table

    def alert_fields(self) -> dict:
        """Columns of alert_rules this source decides."""
        return {"source_kind": self.source_kind, "db_engine": self.engine, "connection_id": self.connection_id,
                "plugin_id": self.plugin_id, "dataset": self.dataset or (self.query_id or ""),
                "query_id": self.query_id}


def plugin_dataset(plugin_id: str, name: str) -> Optional[dict]:
    from .routes.plugins import _load_plugin
    manifest = _load_plugin(plugin_id, installed_only=True) or {}
    for ds in manifest.get("datasets", []) or []:
        if (ds.get("name") or ds.get("table")) == name:
            return ds
    return None


def resolve(source_id: str, *, table: Optional[str] = None, pg_cursor=None) -> ResolvedSource:
    sid = (source_id or "").strip()
    kind, _, rest = sid.partition(":")

    if kind == "pg":
        if not valid_ident(rest):
            raise SourceError("Invalid table.")
        return ResolvedSource(sid, "table", "postgres", None, "core", rest, None)

    if kind == "plugin":
        plugin_id, _, name = rest.partition(":")
        if not (_SLUG.match(plugin_id or "") and valid_ident(name)):
            raise SourceError("Invalid plugin dataset.")
        ds = plugin_dataset(plugin_id, name)
        if ds is None:
            raise SourceError(f"{plugin_id} has no dataset '{name}' (is the plugin installed?).")
        engine = str(ds.get("db") or "postgres").lower()
        if engine not in DRIVERS:
            raise SourceError(f"No driver for database type '{engine}'.")
        database = ds.get("database") or None
        if database and not valid_ident(str(database)):
            raise SourceError("Invalid dataset database.")
        table_name = ds.get("table") or name
        if not valid_ident(table_name):
            raise SourceError("Invalid dataset table.")
        return ResolvedSource(sid, "plugin_dataset", engine, None, plugin_id, table_name, database,
                              alertable=ds.get("alertable", True) is not False,
                              date_column=ds.get("date_column"), currency_column=ds.get("currency_column"))

    if kind == "conn":
        if not _UUID.match(rest):
            raise SourceError("Invalid connection.")
        engine = _connection_engine(rest, pg_cursor)
        database, tname = None, ""
        if table:
            if "." in table:
                database, _, tname = table.partition(".")
            else:
                tname = table
            if not valid_ident(tname) or (database and not valid_ident(database)):
                raise SourceError("Invalid table.")
        return ResolvedSource(sid, "connection_table", engine, rest, "core", tname, database)

    if kind == "query":
        plugin_id, _, query_id = rest.partition(":")
        if not (_SLUG.match(plugin_id or "") and valid_ident(query_id)):
            raise SourceError("Invalid ready-made alert.")
        from .alert_queries import find_query
        q = find_query(plugin_id, query_id)
        if q is None:
            raise SourceError(f"{plugin_id} has no ready-made alert '{query_id}'.")
        return ResolvedSource(sid, "plugin_query", q.engine, None, plugin_id, "", None, query_id=query_id)

    raise SourceError("Unknown source.")


def _connection_engine(connection_id: str, pg_cursor) -> str:
    def look(cur):
        cur.execute("SELECT type, name FROM connections WHERE id::text = %s", (connection_id,))
        return cur.fetchone()

    if pg_cursor is not None:
        row = look(pg_cursor)
    else:
        from .db import get_pg_conn
        with get_pg_conn() as conn:
            row = look(conn.cursor())
    if not row:
        raise SourceError("That connection no longer exists.")
    engine = str(row[0]).lower()
    if engine not in DRIVERS:
        raise SourceError(f"Alerts can't read {engine} connections yet.")
    return engine


def source_id_for_alert(alert: dict) -> Optional[str]:
    """Rebuild the source id of a saved alert (for the editor)."""
    kind = alert.get("source_kind") or "table"
    if kind == "plugin_dataset":
        name = (alert.get("dataset") or "").split(".")[-1]
        return f"plugin:{alert.get('plugin_id')}:{name}"
    if kind == "connection_table" and alert.get("connection_id"):
        return f"conn:{alert['connection_id']}"
    if kind == "plugin_query":
        return f"query:{alert.get('plugin_id')}:{alert.get('query_id')}"
    return f"pg:{alert.get('dataset')}"


__all__ = ["ResolvedSource", "SourceError", "plugin_dataset", "resolve", "source_id_for_alert"]
