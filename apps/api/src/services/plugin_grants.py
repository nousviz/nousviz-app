"""B294 (v0.10.0.3): plugin → nousviz_query grant management.

Centralizes the "plugin tables must be readable by the read-only query
role" guarantee that the fusion sandbox depends on. Replaces the
f-string inline grant block previously in routes/plugins.py with an
identifier-safe, idempotent, unconditional helper that runs on every
plugin install + Update — closing the gap where Update on a plugin
with no new migrations (e.g. B285's stale-tracking-row scenario) used
to skip the grant block entirely.

Pairs with the fusion save/publish pre-flight check in routes/fusions.py
which surfaces missing grants as actionable 422s instead of silent
`InsufficientPrivilege` at execute time.
"""

from __future__ import annotations

import logging
from typing import Optional

import yaml
from psycopg2 import sql as pg_sql

from ..db import get_pg_conn

logger = logging.getLogger(__name__)


def ensure_plugin_query_grants(plugin_id: str, *, conn=None) -> list[str]:
    """Grant SELECT on every table declared in the plugin's manifest
    `databases.postgres.tables[]` to `nousviz_query`. Idempotent —
    Postgres ignores re-grants, so re-running is a no-op.

    Returns the list of tables for which a GRANT was attempted (the
    full manifest list, modulo skips for non-string entries). Doesn't
    return only-newly-granted tables because GRANT is idempotent and
    we don't have a cheap way to introspect prior state without an
    extra round trip per table — the audit log treats this as
    informational.

    `conn` lets callers batch this with other DB work; when None, a
    short-lived connection is opened.
    """
    from ..routes.plugins import INSTALLED_DIR  # late import — avoids circular
    manifest_path = INSTALLED_DIR / plugin_id / "plugin.yaml"
    if not manifest_path.exists():
        return []
    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning(f"plugin_grants: could not read manifest for {plugin_id} — {exc}")
        return []
    tables = (manifest.get("databases") or {}).get("postgres", {}).get("tables") or []
    tables = [t for t in tables if isinstance(t, str)]
    if not tables:
        return []

    def _do_grant(c) -> list[str]:
        cur = c.cursor()
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_query'")
        if not cur.fetchone():
            logger.warning(
                f"plugin_grants: nousviz_query role missing; cannot grant for {plugin_id}"
            )
            return []
        granted: list[str] = []
        for table in tables:
            try:
                cur.execute(
                    pg_sql.SQL("GRANT SELECT ON {schema}.{table} TO nousviz_query").format(
                        schema=pg_sql.Identifier("public"),
                        table=pg_sql.Identifier(table),
                    )
                )
                granted.append(table)
            except Exception as exc:
                logger.warning(
                    f"plugin_grants: GRANT failed on {plugin_id}.{table} — {exc}"
                )
        c.commit()
        return granted

    if conn is not None:
        return _do_grant(conn)
    with get_pg_conn() as own_conn:
        return _do_grant(own_conn)


def check_table_grants(tables: list[str], *, conn=None) -> dict[str, bool]:
    """For each table name (assumed to live in schema `public`), return
    whether `nousviz_query` has SELECT privilege.

    Returns a `{table: bool}` dict. Tables that don't exist in
    `pg_class` and tables where the privilege query errors both map
    to `False` — caller treats either as "needs attention" and
    surfaces the same actionable message.
    """
    if not tables:
        return {}

    def _do_check(c) -> dict[str, bool]:
        cur = c.cursor()
        result: dict[str, bool] = {}
        for table in tables:
            try:
                cur.execute(
                    "SELECT has_table_privilege('nousviz_query', %s, 'SELECT')",
                    (f"public.{table}",),
                )
                row = cur.fetchone()
                result[table] = bool(row and row[0])
            except Exception:
                result[table] = False
        return result

    if conn is not None:
        return _do_check(conn)
    with get_pg_conn() as own_conn:
        return _do_check(own_conn)
