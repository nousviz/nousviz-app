"""
Database — Postgres connection pool.
"""

import os
from contextlib import contextmanager

from psycopg2 import pool as pg_pool

_pg_pool = None


def _required_env(name: str) -> str:
    """Read a required environment variable or raise with a clear message.
    S108: removes the `nousviz_dev` default from POSTGRES_PASSWORD so
    installs can't silently run with a known password."""
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"{name} environment variable is required. "
            f"Set it in your .env file (or in your process manager config) "
            f"and restart. See docs/startup.md for setup guidance."
        )
    return val


def get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = pg_pool.ThreadedConnectionPool(
            minconn=1, maxconn=10,
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "nousviz"),
            user=os.environ.get("POSTGRES_USER", "nousviz"),
            password=_required_env("POSTGRES_PASSWORD"),
            sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
        )
    return _pg_pool


def reset_pg_pool():
    """Close the current pool so the next call to get_pg_pool() re-reads env vars."""
    global _pg_pool
    if _pg_pool is not None:
        try:
            _pg_pool.closeall()
        except Exception:
            pass
        _pg_pool = None


@contextmanager
def get_pg_conn():
    p = get_pg_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def rows_as_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


class DictCursor:
    """Lightweight cursor wrapper that returns dict rows via cur.description.
    Replaces psycopg2.extras.RealDictCursor without the direct psycopg2 dependency."""

    def __init__(self, cur):
        self._cur = cur

    def execute(self, *a, **kw):
        return self._cur.execute(*a, **kw)

    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return dict(zip([d[0] for d in self._cur.description], row))

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cur.description]
        return [dict(zip(cols, r)) for r in rows]


def dict_cursor(conn) -> DictCursor:
    """Create a DictCursor from a connection."""
    return DictCursor(conn.cursor())
