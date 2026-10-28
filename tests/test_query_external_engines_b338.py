"""B338: /api/query must not run ClickHouse or MySQL SQL for anonymous callers.

Before the fix the non-Postgres branch returned before the auth check, the
write block and the row cap, and sent the ClickHouse password in the URL.

The handler is called directly with auth, capabilities and the database
layer stubbed. No live database is touched; the manual checks are in
nousviz-docs 1.0/testing/B338-test-plan.md.
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import apps.api.src.middleware.auth as auth_mw  # noqa: E402
import apps.api.src.routes.query as query_mod  # noqa: E402
from apps.api.src.routes.query import QueryRequest, execute_query  # noqa: E402

CH_CFG = {"host": "ch.internal", "port": 8123, "user": "nv", "password": "s3cret", "database": "plugins"}


class _Cursor:
    def __init__(self, cfg):
        self._cfg = cfg

    def execute(self, *a, **k):
        pass

    def fetchone(self):
        return (self._cfg,)


class _Conn:
    def __init__(self, cfg):
        self._cfg = cfg

    def cursor(self):
        return _Cursor(self._cfg)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch):
    """Stubbed environment; returns the list of ClickHouse requests sent."""
    state = {"authenticated": False}
    sent = []

    monkeypatch.setattr(
        auth_mw, "get_authenticated_identity",
        lambda request: {"user_id": "u1"} if state["authenticated"] else None,
    )
    monkeypatch.setattr(query_mod, "_registered_capabilities_cache", lambda: {"clickhouse", "mysql"})
    monkeypatch.setattr(query_mod, "get_pg_conn", lambda: _Conn(CH_CFG))

    def fake_urlopen(req, timeout=None):
        sent.append(req)
        body = {"meta": [{"name": "x", "type": "UInt8"}], "data": [{"x": 1}]}
        return io.BytesIO(json.dumps(body).encode())

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    state["sent"] = sent
    return state


def _run(sql, engine="clickhouse", **kw):
    return asyncio.run(execute_query(QueryRequest(sql=sql, db_engine=engine, **kw), request=None))


@pytest.mark.parametrize("engine", ["clickhouse", "mysql"])
def test_anonymous_external_query_is_rejected(env, engine):
    with pytest.raises(HTTPException) as exc:
        _run("SELECT 1", engine=engine)
    assert exc.value.status_code == 401
    assert env["sent"] == []


def test_anonymous_rejected_before_any_other_check(env):
    # A write from an anonymous caller still gets 401, and nothing is sent.
    with pytest.raises(HTTPException) as exc:
        _run("DROP TABLE t")
    assert exc.value.status_code == 401
    assert env["sent"] == []


def test_authenticated_clickhouse_query_runs(env):
    env["authenticated"] = True
    res = _run("SELECT 1")
    assert res.rows == [{"x": 1}]
    assert res.db_engine == "clickhouse"
    assert len(env["sent"]) == 1


@pytest.mark.parametrize("sql", [
    "INSERT INTO t VALUES (1)",
    "DROP TABLE t",
    "ALTER TABLE t DELETE WHERE 1",
    "CREATE USER x IDENTIFIED BY 'y'",
    "GRANT ALL ON *.* TO x",
])
def test_authenticated_writes_blocked_before_clickhouse(env, sql):
    env["authenticated"] = True
    with pytest.raises(HTTPException) as exc:
        _run(sql)
    assert exc.value.status_code == 403
    assert env["sent"] == []


@pytest.mark.parametrize("sql", [
    "SELECT * FROM system.users",
    "SELECT query FROM system.query_log",
    "SELECT * FROM system . grants",
    "SELECT * FROM mysql.user",
    "SELECT * FROM performance_schema.threads",
])
def test_authenticated_system_tables_blocked(env, sql):
    env["authenticated"] = True
    with pytest.raises(HTTPException) as exc:
        _run(sql)
    assert exc.value.status_code == 403
    assert env["sent"] == []


@pytest.mark.parametrize("sql", [
    "SELECT name FROM system.tables WHERE database = 'plugins'",
    "SELECT name, type FROM system.columns WHERE table = 't'",
    "SELECT name FROM system.databases",
])
def test_schema_browsing_still_allowed(env, sql):
    env["authenticated"] = True
    _run(sql)
    assert len(env["sent"]) == 1


def test_clickhouse_query_gets_a_limit(env):
    env["authenticated"] = True
    _run("SELECT * FROM t")
    import urllib.parse
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(env["sent"][0].full_url).query)["query"][0]
    assert f"LIMIT {query_mod.MAX_ROWS}" in q


def test_clickhouse_credentials_in_headers_not_url(env):
    env["authenticated"] = True
    _run("SELECT 1")
    req = env["sent"][0]
    assert req.get_method() == "GET"  # ClickHouse runs GET read-only
    assert "s3cret" not in req.full_url
    assert "password" not in req.full_url
    assert "user=" not in req.full_url
    headers = {k.lower(): v for k, v in req.header_items()}
    assert headers["x-clickhouse-user"] == "nv"
    assert headers["x-clickhouse-key"] == "s3cret"


def test_anonymous_postgres_path_unchanged(env, monkeypatch):
    # The anonymous Postgres path still reaches the plugin-table allowlist
    # (share viewers), rather than the new external-engine 401.
    monkeypatch.setattr(query_mod, "_get_allowed_tables", lambda: {"plugin_t"})
    with pytest.raises(HTTPException) as exc:
        _run("SELECT * FROM users", engine="postgres")
    assert exc.value.status_code == 403
