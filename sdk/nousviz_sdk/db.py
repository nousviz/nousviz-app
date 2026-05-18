"""
Postgres connection helper for NousViz plugins (P202 / P208, v0.9.0).

Usage:
    from nousviz_sdk import get_pg_conn, dict_cursor

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM my_table")
        rows = cur.fetchall()

    # With dict-style rows:
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM my_table WHERE id = %s", (42,))
        rows = cur.fetchall()   # list of dicts

# How the connection is authenticated

The SDK connects as the `nousviz_plugin` Postgres role introduced in
v0.9.0 (migration 047). The role has:
  - full CRUD on the plugin's own tables
  - read-only access to a small set of core reference tables
  - no access to credentials, users, api_keys, or other core secrets

**The DB password is fetched from the credential broker** (not env).
Host, port, and database name come from env (they're non-secrets).

This means standalone usage — running a sync script outside the NousViz
worker — raises `CredentialBrokerUnavailable`. Use the NousViz dev
harness for local testing; production plugin code is always spawned by
the worker with a broker token.

P202 (v0.9.0): this module used to delegate to apps.api.src.db and read
the password from POSTGRES_PASSWORD env. Both paths are removed.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from ._broker_client import get_cached, CredentialBrokerUnavailable


@contextmanager
def get_pg_conn():
    """
    Context manager that yields a psycopg2 connection authenticated as
    the `nousviz_plugin` role.

    Raises `CredentialBrokerUnavailable` if not running inside a
    NousViz-spawned subprocess (the broker socket / token env vars
    must be set).
    """
    import psycopg2

    # Broker delivers the nousviz_plugin role credentials under the
    # special `__db__` key.
    creds = get_cached()
    db_info = creds.get("__db__")
    if not db_info or not db_info.get("password"):
        raise CredentialBrokerUnavailable(
            "Broker response missing __db__ credentials. This usually "
            "means the worker's NOUSVIZ_PLUGIN_PASSWORD is not set — "
            "run scripts/setup.sh or check your .env."
        )

    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "nousviz"),
        user=db_info["user"],
        password=db_info["password"],
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class DictCursor:
    """
    Thin wrapper around psycopg2's cursor that returns rows as dicts.

    Usage:
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute("SELECT id, name FROM things")
            for row in cur.fetchall():
                print(row["name"])
    """

    def __init__(self, cursor):
        self._cur = cursor

    def execute(self, query, params=None):
        self._cur.execute(query, params)
        return self

    def executemany(self, query, params_seq):
        self._cur.executemany(query, params_seq)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return dict(zip(cols, row))

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description]
        return [dict(zip(cols, r)) for r in rows]

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description]
        return [dict(zip(cols, r)) for r in rows]

    def close(self):
        self._cur.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description


def dict_cursor(conn) -> DictCursor:
    """Create a DictCursor from a psycopg2 connection."""
    return DictCursor(conn.cursor())
