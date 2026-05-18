"""
Unit tests for B130 — plugin_config module.

Covers DB-first read, env fallback, self-heal, list helper, and the
_conn.* key namespace.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def stub_db(monkeypatch):
    """Stub plugin_config.get_pg_conn with a MagicMock connection.
    Also clears the legacy-warned set so each test is independent.
    """
    from apps.api.src import plugin_config as pc

    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pc, "get_pg_conn", fake_pg)
    pc._legacy_warned.clear()
    return {"cursor": cursor, "conn": conn, "module": pc}


# ── Namespace ────────────────────────────────────────────────────────


def test_conn_key_prefixes_correctly():
    from apps.api.src.plugin_config import _conn_key, CONN_KEY_PREFIX
    assert _conn_key("host") == f"{CONN_KEY_PREFIX}host"
    assert CONN_KEY_PREFIX == "_conn."


# ── upsert_config_field ──────────────────────────────────────────────


def test_upsert_writes_jsonb_with_conn_prefix(stub_db):
    from apps.api.src.plugin_config import upsert_config_field

    upsert_config_field("my-plugin", "host", "mysql.example.com")

    stub_db["cursor"].execute.assert_called_once()
    sql, params = stub_db["cursor"].execute.call_args[0]
    assert "INSERT INTO plugin_settings" in sql
    assert "ON CONFLICT" in sql
    assert params[0] == "my-plugin"
    assert params[1] == "_conn.host"
    # Third arg is JSON-encoded string value
    assert params[2] == '"mysql.example.com"'


def test_upsert_handles_integer_value(stub_db):
    from apps.api.src.plugin_config import upsert_config_field

    upsert_config_field("p", "port", 3306)
    _, params = stub_db["cursor"].execute.call_args[0]
    assert params[2] == "3306"


# ── get_config_field: DB-first ───────────────────────────────────────


def test_get_reads_from_db_first(stub_db, monkeypatch):
    from apps.api.src.plugin_config import get_config_field

    stub_db["cursor"].fetchone.return_value = ("mysql.example.com",)
    monkeypatch.setenv("EXAMPLE_HOST", "different-env-value")

    val = get_config_field("example-mysql", "host", env_prefix="EXAMPLE_", default="")
    assert val == "mysql.example.com"

    monkeypatch.delenv("EXAMPLE_HOST", raising=False)


def test_get_falls_back_to_env_when_db_empty(stub_db, monkeypatch):
    from apps.api.src.plugin_config import get_config_field

    stub_db["cursor"].fetchone.return_value = None
    monkeypatch.setenv("LEGACY_HOST", "from-env")

    val = get_config_field("plug", "host", env_prefix="LEGACY_", default="")
    assert val == "from-env"

    monkeypatch.delenv("LEGACY_HOST", raising=False)


def test_get_returns_default_when_neither_db_nor_env(stub_db, monkeypatch):
    from apps.api.src.plugin_config import get_config_field

    stub_db["cursor"].fetchone.return_value = None
    monkeypatch.delenv("WHATEVER_HOST", raising=False)

    val = get_config_field("plug", "host", env_prefix="WHATEVER_", default="fallback.default")
    assert val == "fallback.default"


def test_get_swallows_db_errors_and_falls_back(monkeypatch):
    """If the DB read raises, get_config_field should fall back to env
    rather than 500 the endpoint."""
    from apps.api.src import plugin_config as pc

    @contextmanager
    def broken_pg():
        raise RuntimeError("DB down")
        yield  # pragma: no cover

    monkeypatch.setattr(pc, "get_pg_conn", broken_pg)
    monkeypatch.setenv("LEGACY_X", "env-recovery")

    val = pc.get_config_field("plug", "x", env_prefix="LEGACY_", default="")
    assert val == "env-recovery"

    monkeypatch.delenv("LEGACY_X", raising=False)


# ── Legacy fallback self-heal ────────────────────────────────────────


def test_env_fallback_triggers_self_heal(monkeypatch):
    """When DB has no row but env does, get_config_field should write
    the env value back to DB for next time."""
    from apps.api.src import plugin_config as pc

    writes = []

    def fake_upsert(plugin_id, field_name, value):
        writes.append((plugin_id, field_name, value))

    monkeypatch.setattr(pc, "upsert_config_field", fake_upsert)

    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pc, "get_pg_conn", fake_pg)
    pc._legacy_warned.clear()
    monkeypatch.setenv("LEGACY_HOST", "legacy-value")

    val = pc.get_config_field("plug", "host", env_prefix="LEGACY_", default="")
    assert val == "legacy-value"
    assert writes == [("plug", "host", "legacy-value")]

    monkeypatch.delenv("LEGACY_HOST", raising=False)


def test_legacy_warning_only_fires_once_per_pair(monkeypatch, caplog):
    from apps.api.src import plugin_config as pc

    monkeypatch.setattr(pc, "upsert_config_field", lambda *a, **k: None)

    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(pc, "get_pg_conn", fake_pg)
    pc._legacy_warned.clear()
    monkeypatch.setenv("LEGACY_HOST", "x")

    with caplog.at_level("WARNING"):
        pc.get_config_field("plug", "host", env_prefix="LEGACY_")
        pc.get_config_field("plug", "host", env_prefix="LEGACY_")
        pc.get_config_field("plug", "host", env_prefix="LEGACY_")

    # Count matching log records — should be exactly 1
    legacy_warns = [r for r in caplog.records if "read from .env/os.environ fallback" in r.message]
    assert len(legacy_warns) == 1

    monkeypatch.delenv("LEGACY_HOST", raising=False)


# ── list_config_fields ───────────────────────────────────────────────


def test_list_strips_conn_prefix(stub_db):
    from apps.api.src.plugin_config import list_config_fields

    stub_db["cursor"].fetchall.return_value = [
        ("_conn.host", "mysql.example.com"),
        ("_conn.port", "3306"),
        ("_conn.database", "replica"),
    ]
    result = list_config_fields("my-plugin")
    assert result == {"host": "mysql.example.com", "port": "3306", "database": "replica"}


def test_list_filters_by_conn_prefix_in_sql(stub_db):
    from apps.api.src.plugin_config import list_config_fields
    stub_db["cursor"].fetchall.return_value = []
    list_config_fields("plug")

    sql, params = stub_db["cursor"].execute.call_args[0]
    assert "key LIKE" in sql
    assert params[1] == "_conn.%"


def test_list_handles_db_error_gracefully(monkeypatch):
    from apps.api.src import plugin_config as pc

    @contextmanager
    def broken_pg():
        raise RuntimeError("DB down")
        yield  # pragma: no cover

    monkeypatch.setattr(pc, "get_pg_conn", broken_pg)
    assert pc.list_config_fields("plug") == {}


# ── inject_config_env ─────────────────────────────────────────────────


def test_inject_sets_non_secret_values(monkeypatch):
    """inject_config_env should set os.environ for each non-secret field
    by reading plugin_settings."""
    from apps.api.src import plugin_config as pc

    # Stub: `get_config_field` returns a known value for each field
    def fake_get(plugin_id, field_name, env_prefix="", default=""):
        return {"host": "mysql.host", "port": "3306"}.get(field_name, default)

    def fake_cred(plugin_id, field_name, env_prefix="", performed_by=""):
        return None  # no secrets for this test

    monkeypatch.setattr(pc, "get_config_field", fake_get)
    monkeypatch.setattr(
        "apps.api.src.plugin_credentials.get_plugin_credential", fake_cred
    )

    for k in ("EXAMPLE_HOST", "EXAMPLE_PORT"):
        monkeypatch.delenv(k, raising=False)

    manifest = {
        "connections": [{
            "env_prefix": "EXAMPLE_",
            "fields": [
                {"name": "host", "type": "text"},
                {"name": "port", "type": "port"},
            ],
        }]
    }
    pc.inject_config_env("example-mysql", manifest)

    assert os.environ.get("EXAMPLE_HOST") == "mysql.host"
    assert os.environ.get("EXAMPLE_PORT") == "3306"

    monkeypatch.delenv("EXAMPLE_HOST", raising=False)
    monkeypatch.delenv("EXAMPLE_PORT", raising=False)


def test_inject_skips_empty_values(monkeypatch):
    from apps.api.src import plugin_config as pc

    monkeypatch.setattr(pc, "get_config_field", lambda *a, **k: "")
    monkeypatch.setattr(
        "apps.api.src.plugin_credentials.get_plugin_credential", lambda *a, **k: None
    )
    monkeypatch.delenv("X_HOST", raising=False)

    manifest = {
        "connections": [{
            "env_prefix": "X_",
            "fields": [{"name": "host", "type": "text"}],
        }]
    }
    pc.inject_config_env("plug", manifest)

    assert os.environ.get("X_HOST") is None
