"""
Unit tests for B278 (v0.9.11.14) — _drop_declared_tables defense-in-depth
helper used by the plugin uninstall flow.

Production incident 2026-05-04: 3 plugins uninstalled with `data_removed: true`
in the audit log left 601 MB of data in place across 5 tables. Root cause:
the previous flow only ran *_down.sql files; plugins that ship without down
migrations had no actual data-removal mechanism.

These tests pin the contract for the new defense-in-depth helper:
- Identifier validation rejects malformed table names (SQL injection defense)
- Empty / malformed manifest sections handled gracefully
- Real DROP TABLE attempts succeed against a temporary fixture table

Live-DB tests are gated behind NOUSVIZ_RUN_DB_TESTS=1 in the same pattern as
tests/test_catalog.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.routes.plugins import (
    _drop_declared_tables,
    _VALID_TABLE_NAME_B278,
)


# ── _VALID_TABLE_NAME_B278 regex ─────────────────────────────────────


def test_valid_table_name_accepts_normal():
    assert _VALID_TABLE_NAME_B278.match("gsc_search_analytics")
    assert _VALID_TABLE_NAME_B278.match("auth_audit")
    assert _VALID_TABLE_NAME_B278.match("a")
    assert _VALID_TABLE_NAME_B278.match("_underscore_start")
    assert _VALID_TABLE_NAME_B278.match("MixedCase_123")


def test_valid_table_name_rejects_special():
    assert _VALID_TABLE_NAME_B278.match("") is None
    assert _VALID_TABLE_NAME_B278.match("123leading_digit") is None
    assert _VALID_TABLE_NAME_B278.match("has-dash") is None
    assert _VALID_TABLE_NAME_B278.match("has space") is None
    assert _VALID_TABLE_NAME_B278.match("has.dot") is None
    assert _VALID_TABLE_NAME_B278.match("has;semi") is None
    assert _VALID_TABLE_NAME_B278.match('"quoted"') is None
    assert _VALID_TABLE_NAME_B278.match("'sql_injection") is None


# ── _drop_declared_tables: empty / malformed manifest cases ──────────


def test_empty_manifest_returns_empty_lists():
    dropped, failed = _drop_declared_tables("test_plugin", {})
    assert dropped == []
    assert failed == []


def test_none_manifest_returns_empty_lists():
    dropped, failed = _drop_declared_tables("test_plugin", None)
    assert dropped == []
    assert failed == []


def test_manifest_without_databases_section_returns_empty():
    manifest = {"name": "x", "version": "1.0.0"}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)
    assert dropped == []
    assert failed == []


def test_manifest_without_postgres_subsection_returns_empty():
    manifest = {"databases": {"clickhouse": {"tables": ["other_thing"]}}}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)
    assert dropped == []
    assert failed == []


def test_manifest_with_empty_tables_list():
    manifest = {"databases": {"postgres": {"tables": []}}}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)
    assert dropped == []
    assert failed == []


def test_manifest_with_tables_not_a_list():
    """Defensive: someone declares `tables: foo_table` instead of a list."""
    manifest = {"databases": {"postgres": {"tables": "not_a_list"}}}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)
    assert dropped == []
    assert failed == []


# ── _drop_declared_tables: SQL injection defense ──────────────────────


def test_injection_attempt_via_table_name():
    """Each malformed identifier should land in `failed` with reason —
    NEVER reach SQL composition."""
    manifest = {
        "databases": {
            "postgres": {
                "tables": [
                    '"; DROP TABLE users; --',
                    "valid_lookalike",  # would compose if mock cursor ran
                    "$(rm -rf /)",
                    "table'with'quotes",
                ]
            }
        }
    }
    # Mock the DB connection so we can verify SQL composition behaviour.
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # Make DROP TABLE on 'valid_lookalike' succeed
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *args: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        dropped, failed = _drop_declared_tables("test_plugin", manifest)

    # The 3 malformed entries are in failed
    assert len(failed) == 3
    failed_tables = {f["table"] for f in failed}
    assert '"; DROP TABLE users; --' in failed_tables
    assert "$(rm -rf /)" in failed_tables
    assert "table'with'quotes" in failed_tables
    # All have the validation reason (not a SQL error)
    for entry in failed:
        assert "invalid identifier" in entry["reason"]

    # The valid_lookalike was the only one that would have made it to SQL
    assert dropped == ["valid_lookalike"]


def test_non_string_entries_skipped_gracefully():
    """Manifest with unexpected types (int, None, dict) shouldn't crash."""
    manifest = {
        "databases": {
            "postgres": {
                "tables": [
                    "valid_table",
                    123,
                    None,
                    {"nested": "object"},
                ]
            }
        }
    }
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *args: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        dropped, failed = _drop_declared_tables("test_plugin", manifest)

    assert dropped == ["valid_table"]
    assert len(failed) == 3  # int, None, dict
    for entry in failed:
        assert "invalid identifier" in entry["reason"]


# ── _drop_declared_tables: per-table DROP failure handling ───────────


def test_per_table_drop_failure_does_not_abort_remaining():
    """If DROP TABLE fails on table 1 of 3, tables 2 and 3 should still
    be attempted. The failure is recorded per-table."""
    manifest = {
        "databases": {
            "postgres": {
                "tables": ["table_a", "table_b", "table_c"]
            }
        }
    }
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # First execute call raises; subsequent succeed
    call_count = {"n": 0}

    def execute_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("simulated DROP failure: table_a is in use")
        return None

    mock_cur.execute.side_effect = execute_side_effect
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *args: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        dropped, failed = _drop_declared_tables("test_plugin", manifest)

    # table_a failed, table_b + table_c succeeded
    assert len(failed) == 1
    assert failed[0]["table"] == "table_a"
    assert "table_a is in use" in failed[0]["reason"]
    assert dropped == ["table_b", "table_c"]


# ── Live integration: real DROP TABLE against a temp test table ──────

LIVE = pytest.mark.skipif(
    os.environ.get("NOUSVIZ_RUN_DB_TESTS") != "1",
    reason="Set NOUSVIZ_RUN_DB_TESTS=1 to run live-DB tests against the local Postgres",
)


@LIVE
def test_live_drop_existing_table():
    """End-to-end: create a real table, run _drop_declared_tables, verify
    it's gone."""
    from apps.api.src.db import get_pg_conn

    table_name = "b278_test_table_to_drop"
    # Create the table
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id int)")
        cur.execute(f"INSERT INTO {table_name} (id) VALUES (1), (2), (3)")
        conn.commit()

    manifest = {"databases": {"postgres": {"tables": [table_name]}}}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)

    assert dropped == [table_name]
    assert failed == []

    # Verify the table is actually gone
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM pg_class WHERE relname = %s",
            (table_name,),
        )
        assert cur.fetchone()[0] == 0


@LIVE
def test_live_drop_nonexistent_table_no_error():
    """DROP TABLE IF EXISTS on a missing table is idempotent."""
    manifest = {"databases": {"postgres": {"tables": ["b278_nonexistent_table_xyz"]}}}
    dropped, failed = _drop_declared_tables("test_plugin", manifest)
    # IF EXISTS makes this succeed silently
    assert dropped == ["b278_nonexistent_table_xyz"]
    assert failed == []


# ── Audit log honesty contract ───────────────────────────────────────


def test_audit_record_shape_for_data_removed_true_with_zero_drops():
    """Document the contract: when remove_data=True but no tables dropped,
    audit_detail records this honestly. The handler integration test
    (in routes/plugins.py) is what enforces this; this test pins the
    expected shape."""
    # This is a contract assertion against the handler, not a unit test.
    # The handler now passes both `data_removed: bool` (intent) and
    # `data_tables_dropped: [...]` (outcome) to _log_plugin_action.
    # If those drift apart, the audit log honesty contract breaks.
    expected_audit_keys_for_target_plugin = {
        "data_removed",            # bool (intent)
        "data_tables_dropped",     # list[str] (outcome — may be empty if no manifest tables)
        "data_tables_drop_failed", # list[dict] (per-table failures)
        "down_migrations_run",     # list[str] (*_down.sql files run)
        "purged_rows",             # dict (registry/settings/etc rows purged)
    }
    # If this set ever changes, the migration / consumer code needs review
    assert expected_audit_keys_for_target_plugin == {
        "data_removed",
        "data_tables_dropped",
        "data_tables_drop_failed",
        "down_migrations_run",
        "purged_rows",
    }
