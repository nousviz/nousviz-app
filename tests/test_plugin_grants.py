"""
Tests for plugin_grants — P203 grant/revoke helper.

The DB role and grant behaviour itself is tested end-to-end in the
integration-test phase (against a real Postgres). These unit tests
cover the pure-Python logic: manifest parsing, identifier safety,
and the no-op-on-missing-role path.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Identifier safety ────────────────────────────────────────────────


def test_safe_identifier_accepts_snake_case():
    from apps.api.src.plugin_grants import _is_safe_identifier
    assert _is_safe_identifier("hello_items")
    assert _is_safe_identifier("sd_sync_checkpoints")
    assert _is_safe_identifier("_internal")
    assert _is_safe_identifier("abc123")


def test_safe_identifier_rejects_malicious():
    from apps.api.src.plugin_grants import _is_safe_identifier
    assert not _is_safe_identifier("")
    assert not _is_safe_identifier("1starts_with_digit")
    assert not _is_safe_identifier("has space")
    assert not _is_safe_identifier("has;semicolon")
    assert not _is_safe_identifier('"quoted"')
    assert not _is_safe_identifier("has-dash")  # dashes not valid Postgres
    assert not _is_safe_identifier("has.dot")


# ── Manifest parsing ─────────────────────────────────────────────────


def test_iter_declared_tables_happy():
    from apps.api.src.plugin_grants import _iter_declared_tables
    manifest = {
        "databases": {
            "postgres": {
                "tables": ["hello_items", "hello_events"],
            }
        }
    }
    assert list(_iter_declared_tables(manifest)) == ["hello_items", "hello_events"]


def test_iter_declared_tables_empty_manifest():
    from apps.api.src.plugin_grants import _iter_declared_tables
    assert list(_iter_declared_tables({})) == []
    assert list(_iter_declared_tables({"databases": {}})) == []
    assert list(_iter_declared_tables({"databases": {"postgres": {}}})) == []


def test_iter_declared_tables_filters_unsafe(caplog):
    """A plugin manifest declaring a malicious table name must be
    filtered out, not allowed to reach GRANT statements."""
    from apps.api.src.plugin_grants import _iter_declared_tables

    manifest = {
        "databases": {
            "postgres": {
                "tables": [
                    "safe_table",
                    "bad; DROP TABLE users",
                    "also_safe",
                    '"quoted"',
                    "has space",
                ],
            }
        }
    }
    with caplog.at_level("WARNING"):
        result = list(_iter_declared_tables(manifest))
    assert result == ["safe_table", "also_safe"]


def test_iter_declared_tables_ignores_non_strings():
    from apps.api.src.plugin_grants import _iter_declared_tables
    manifest = {
        "databases": {"postgres": {"tables": ["ok", 123, None, {"dict": "entry"}]}}
    }
    assert list(_iter_declared_tables(manifest)) == ["ok"]


# ── No-op when role missing ──────────────────────────────────────────


@pytest.fixture
def stub_role_missing(monkeypatch):
    """Stub _role_exists to return False. grant_plugin_tables should
    then skip everything and not attempt any SQL."""
    from apps.api.src import plugin_grants as pg

    monkeypatch.setattr(pg, "_role_exists", lambda: False)

    # Also stub get_pg_conn to blow up if it's actually called
    @contextmanager
    def _should_not_call():
        raise AssertionError("get_pg_conn called even though role doesn't exist")
        yield  # pragma: no cover

    monkeypatch.setattr(pg, "get_pg_conn", _should_not_call)


def test_grant_skips_when_role_missing(stub_role_missing):
    from apps.api.src.plugin_grants import grant_plugin_tables
    manifest = {"databases": {"postgres": {"tables": ["hello_items"]}}}
    # Must not raise; returns empty list
    assert grant_plugin_tables("hello", manifest) == []


def test_revoke_skips_when_role_missing(stub_role_missing):
    from apps.api.src.plugin_grants import revoke_plugin_tables
    manifest = {"databases": {"postgres": {"tables": ["hello_items"]}}}
    assert revoke_plugin_tables("hello", manifest) == []


# ── Grant happy path (stubbed DB) ────────────────────────────────────


@pytest.fixture
def stub_role_present(monkeypatch):
    """Stub _role_exists to True + provide a MagicMock cursor that
    answers `table_exists` queries with True."""
    from apps.api.src import plugin_grants as pg

    monkeypatch.setattr(pg, "_role_exists", lambda: True)

    cursor = MagicMock()
    # First fetchone is for information_schema.tables existence check
    # (returns (1,) when exists). Subsequent calls cycle through.
    # We use fetchone to answer both table-existence AND to drive
    # fetchall for the sequence-lookup query.
    cursor.fetchone.return_value = (1,)   # table exists
    cursor.fetchall.return_value = []      # no sequences

    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pg, "get_pg_conn", fake_pg)
    return {"cursor": cursor, "conn": conn}


def test_grant_issues_grant_per_table(stub_role_present):
    from apps.api.src.plugin_grants import grant_plugin_tables
    manifest = {"databases": {"postgres": {"tables": ["t_alpha", "t_beta"]}}}

    granted = grant_plugin_tables("my-plugin", manifest)
    assert granted == ["t_alpha", "t_beta"]

    # Verify each GRANT was actually issued
    sql_calls = [call.args[0] for call in stub_role_present["cursor"].execute.call_args_list]
    assert any("GRANT SELECT, INSERT, UPDATE, DELETE ON t_alpha TO nousviz_plugin" in sql for sql in sql_calls)
    assert any("GRANT SELECT, INSERT, UPDATE, DELETE ON t_beta TO nousviz_plugin" in sql for sql in sql_calls)


def test_grant_skips_table_that_does_not_exist(monkeypatch):
    """If a plugin declares a table but migrations haven't created it yet,
    the grant should skip without erroring."""
    from apps.api.src import plugin_grants as pg

    monkeypatch.setattr(pg, "_role_exists", lambda: True)

    cursor = MagicMock()
    # Table does NOT exist → fetchone returns None
    cursor.fetchone.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pg, "get_pg_conn", fake_pg)

    manifest = {"databases": {"postgres": {"tables": ["not_yet_created"]}}}
    granted = pg.grant_plugin_tables("my-plugin", manifest)
    assert granted == []

    # Must not have issued any GRANT
    sql_calls = [call.args[0] for call in cursor.execute.call_args_list]
    assert not any("GRANT" in sql for sql in sql_calls)


def test_grant_handles_empty_manifest(stub_role_present):
    from apps.api.src.plugin_grants import grant_plugin_tables
    assert grant_plugin_tables("my-plugin", {}) == []


def test_revoke_issues_revoke_per_table(stub_role_present):
    from apps.api.src.plugin_grants import revoke_plugin_tables
    manifest = {"databases": {"postgres": {"tables": ["t_alpha", "t_beta"]}}}

    revoked = revoke_plugin_tables("my-plugin", manifest)
    assert revoked == ["t_alpha", "t_beta"]

    sql_calls = [call.args[0] for call in stub_role_present["cursor"].execute.call_args_list]
    assert any("REVOKE ALL ON t_alpha FROM nousviz_plugin" in sql for sql in sql_calls)
    assert any("REVOKE ALL ON t_beta FROM nousviz_plugin" in sql for sql in sql_calls)


def test_revoke_skips_already_dropped_table(monkeypatch):
    """On uninstall with remove_data=True, down-migrations may run first
    and drop tables. The REVOKE must then be a no-op."""
    from apps.api.src import plugin_grants as pg

    monkeypatch.setattr(pg, "_role_exists", lambda: True)

    cursor = MagicMock()
    cursor.fetchone.return_value = None  # table gone

    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pg, "get_pg_conn", fake_pg)

    manifest = {"databases": {"postgres": {"tables": ["already_dropped"]}}}
    assert pg.revoke_plugin_tables("x", manifest) == []
    sql_calls = [call.args[0] for call in cursor.execute.call_args_list]
    assert not any("REVOKE" in sql for sql in sql_calls)
