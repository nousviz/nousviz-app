"""
Plugin-scoped DB grants for the `nousviz_plugin` role (P203 / v0.9.0).

When a plugin is installed, we enumerate the tables it declares (in
`databases.postgres.tables` in plugin.yaml) and grant `nousviz_plugin`
full CRUD on each. When a plugin is uninstalled, we revoke.

This module is the single source of truth for "what privileges does a
plugin get on its own tables." Install/uninstall flows and the setup.sh
backfill loop all route through here.

## Security model

Grants are ONLY applied to tables the plugin itself declares. A plugin
cannot declare a table belonging to another plugin (the install-time
validator catches that). A plugin that later tries to `SELECT` from
another plugin's table hits Postgres's `permission denied`.

The `nousviz_plugin` role is intentionally not a superuser. These
GRANT / REVOKE statements are issued by the app user (`nousviz`), which
is the owner of plugin tables and therefore authorised to grant them.
"""

from __future__ import annotations

import logging
from typing import Iterable

from .db import get_pg_conn

logger = logging.getLogger("nousviz.api.plugin_grants")

PLUGIN_ROLE = "nousviz_plugin"


def _iter_declared_tables(manifest: dict) -> Iterable[str]:
    """Yield each table name a plugin declares in its manifest.

    Reads `databases.postgres.tables` (a list of strings). Ignores any
    entry that isn't a clean identifier — we refuse to issue GRANT on
    a name containing quotes/semicolons (defense-in-depth against a
    malicious manifest).
    """
    databases = manifest.get("databases") or {}
    postgres_cfg = databases.get("postgres") or {}
    tables = postgres_cfg.get("tables") or []
    for t in tables:
        if not isinstance(t, str):
            continue
        if not t or not _is_safe_identifier(t):
            logger.warning(
                "plugin_grants: refusing unsafe table identifier %r — "
                "must match [a-z_][a-z0-9_]*",
                t,
            )
            continue
        yield t


def _is_safe_identifier(name: str) -> bool:
    """Very conservative check. Postgres table names allow far more,
    but v0.9.0 plugins stick to snake_case ASCII."""
    if not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    return all(c.isalnum() or c == "_" for c in name)


def _role_exists() -> bool:
    """Return True if the nousviz_plugin role exists. On servers that
    haven't run the P203 setup.sh path yet, we skip grants silently
    instead of erroring — the server is in transition."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (PLUGIN_ROLE,))
            return cur.fetchone() is not None
    except Exception as exc:
        logger.warning("plugin_grants: role check failed: %s", exc)
        return False


def grant_plugin_tables(plugin_id: str, manifest: dict) -> list[str]:
    """Grant nousviz_plugin full CRUD on every table this plugin declares.

    Returns the list of tables granted (for logging / activity trails).
    Missing tables (declared in manifest but not yet created) are
    skipped silently — migrations may run after install, and repeating
    the grant after migration is idempotent.
    """
    if not _role_exists():
        logger.info(
            f"plugin_grants: skipping grants for {plugin_id} — "
            f"{PLUGIN_ROLE} role does not exist. Run setup.sh."
        )
        return []

    granted: list[str] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        for table in _iter_declared_tables(manifest):
            # Only grant on tables that actually exist. A plugin can
            # declare tables that its migrations haven't created yet;
            # we re-run grants after each install step so the final
            # state is consistent.
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            )
            if not cur.fetchone():
                logger.info(
                    f"plugin_grants: table {table!r} not yet created for {plugin_id} — skipping grant"
                )
                continue

            # Identifier already validated by _iter_declared_tables;
            # f-string here is safe.
            cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {PLUGIN_ROLE}")

            # Grant on the primary-key sequence too if it exists.
            # Standard Postgres naming: <table>_<col>_seq for SERIAL/BIGSERIAL.
            cur.execute(
                """
                SELECT pg_get_serial_sequence(%s, column_name)
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                  AND column_default LIKE 'nextval%%'
                """,
                (table, table),
            )
            for row in cur.fetchall():
                seq = row[0]
                if seq:
                    # seq comes back fully-qualified ("public.<name>")
                    seq_name = seq.split(".", 1)[-1]
                    if _is_safe_identifier(seq_name):
                        cur.execute(f"GRANT USAGE, SELECT ON SEQUENCE {seq_name} TO {PLUGIN_ROLE}")

            granted.append(table)
        conn.commit()

    if granted:
        logger.info(f"plugin_grants: {plugin_id} -> {PLUGIN_ROLE} granted on {granted}")
    return granted


def revoke_plugin_tables(plugin_id: str, manifest: dict) -> list[str]:
    """Revoke nousviz_plugin's access to this plugin's declared tables.

    Called at uninstall BEFORE tables are dropped. If tables are already
    gone (down-migration ran first), REVOKE is a no-op on missing tables.
    """
    if not _role_exists():
        return []

    revoked: list[str] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        for table in _iter_declared_tables(manifest):
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            )
            if not cur.fetchone():
                continue
            cur.execute(f"REVOKE ALL ON {table} FROM {PLUGIN_ROLE}")
            revoked.append(table)
        conn.commit()

    if revoked:
        logger.info(f"plugin_grants: revoked {PLUGIN_ROLE} access to {plugin_id} -> {revoked}")
    return revoked
