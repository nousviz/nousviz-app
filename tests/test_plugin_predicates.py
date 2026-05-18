"""
Unit tests for the shared plugin predicate resolver (P118/P119/P121 shared).

The resolver queries the DB, so these tests stub `get_pg_conn` with a
MagicMock that returns canned cursor results. Goal: every predicate in
ALLOWED_PREDICATES has at least one assertion for each of the true/false
branches of its SQL.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def stub_db(monkeypatch):
    """Patches plugin_predicates.get_pg_conn with a context-manager MagicMock.

    Usage:
        def test_foo(stub_db):
            stub_db["cursor"].fetchone.return_value = (True,)
            ...
    """
    from apps.api.src import plugin_predicates as pp

    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_get_pg_conn():
        yield conn

    monkeypatch.setattr(pp, "get_pg_conn", fake_get_pg_conn)
    return {"cursor": cursor, "conn": conn}


# ── has_credentials / no_credentials ──────────────────────────────────


def test_has_credentials_true(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (True,)
    assert resolve("my-plugin", "has_credentials") is True


def test_has_credentials_false(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (False,)
    assert resolve("my-plugin", "has_credentials") is False


def test_no_credentials_is_inverse(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (False,)
    assert resolve("my-plugin", "no_credentials") is True


def test_credentials_saved_alias_matches_has_credentials(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (True,)
    assert resolve("my-plugin", "credentials_saved") is True


# ── sync_in_progress / backfill_running ───────────────────────────────


def test_sync_in_progress_true(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (True,)
    assert resolve("my-plugin", "sync_in_progress") is True


def test_sync_in_progress_false(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (False,)
    assert resolve("my-plugin", "sync_in_progress") is False


def test_backfill_running_is_alias(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (True,)
    assert resolve("my-plugin", "backfill_running") is True


# ── first_sync_success / no_prior_sync ────────────────────────────────


def test_first_sync_success_true(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (True,)
    assert resolve("my-plugin", "first_sync_success") is True


def test_no_prior_sync_is_inverse(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = (False,)
    assert resolve("my-plugin", "no_prior_sync") is True


# ── last_test_success ─────────────────────────────────────────────────


def test_last_test_success_true_when_most_recent_is_success(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = ("success",)
    assert resolve("my-plugin", "last_test_success") is True


def test_last_test_success_false_when_most_recent_is_error(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = ("error",)
    assert resolve("my-plugin", "last_test_success") is False


def test_last_test_success_false_when_no_rows(stub_db):
    from apps.api.src.plugin_predicates import resolve
    stub_db["cursor"].fetchone.return_value = None
    assert resolve("my-plugin", "last_test_success") is False


# ── schedule_active (integrates with jobs.py) ─────────────────────────


def _make_fake_pg_conn(query_result):
    """Helper: build a context-manager-style get_pg_conn stub that returns
    a single row for any query. Used by the schedule_active tests below
    to simulate sync_schedule_registry rows."""
    from unittest.mock import MagicMock

    cur = MagicMock()
    cur.fetchone.return_value = query_result
    conn = MagicMock()
    conn.cursor.return_value = cur

    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=conn)
    fake_ctx.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=fake_ctx)


# B147 (v0.9.3): schedule_active reads sync_schedule_registry.
# Predicate is true iff a row exists, updated_at is fresh (<5 min),
# and last_error is null.


def test_schedule_active_true_when_registry_row_is_fresh(monkeypatch):
    """Row present, updated_at recent, no error → predicate true."""
    from datetime import datetime, timezone, timedelta
    from apps.api.src import plugin_predicates as pp

    fresh = datetime.now(timezone.utc) - timedelta(seconds=10)
    monkeypatch.setattr(pp, "get_pg_conn", _make_fake_pg_conn((fresh, None)))

    assert pp.resolve("my-plugin", "schedule_active") is True


def test_schedule_active_false_when_no_registry_row(monkeypatch):
    """Plugin not in sync_schedule_registry → predicate false (scheduler
    hasn't claimed this plugin yet, or it's been reaped after uninstall)."""
    from apps.api.src import plugin_predicates as pp

    monkeypatch.setattr(pp, "get_pg_conn", _make_fake_pg_conn(None))

    assert pp.resolve("my-plugin", "schedule_active") is False


def test_schedule_active_false_when_row_is_stale(monkeypatch):
    """updated_at >5 min ago → scheduler probably dead → predicate false."""
    from datetime import datetime, timezone, timedelta
    from apps.api.src import plugin_predicates as pp

    stale = datetime.now(timezone.utc) - timedelta(minutes=10)
    monkeypatch.setattr(pp, "get_pg_conn", _make_fake_pg_conn((stale, None)))

    assert pp.resolve("my-plugin", "schedule_active") is False


def test_schedule_active_false_when_last_error_set(monkeypatch):
    """Row has a last_error (e.g. invalid cron) → predicate false even if
    updated_at is fresh. Honest signal that scheduling isn't actually working."""
    from datetime import datetime, timezone, timedelta
    from apps.api.src import plugin_predicates as pp

    fresh = datetime.now(timezone.utc) - timedelta(seconds=10)
    monkeypatch.setattr(
        pp, "get_pg_conn",
        _make_fake_pg_conn((fresh, "Invalid cron expression: every monday")),
    )

    assert pp.resolve("my-plugin", "schedule_active") is False


# ── Allowlist + unknown predicates ────────────────────────────────────


def test_allowed_predicates_contains_all_documented():
    from apps.api.src.plugin_predicates import ALLOWED_PREDICATES

    expected = {
        "no_credentials", "has_credentials",
        "sync_in_progress", "no_prior_sync", "first_sync_success",
        "backfill_running",
        "credentials_saved", "last_test_success", "schedule_active",
    }
    assert expected.issubset(ALLOWED_PREDICATES)


def test_is_valid_predicate_allowlist():
    from apps.api.src.plugin_predicates import is_valid_predicate

    assert is_valid_predicate("has_credentials")
    assert not is_valid_predicate("arbitrary_code_execution")
    assert not is_valid_predicate("")


def test_resolve_unknown_predicate_returns_false(stub_db):
    from apps.api.src.plugin_predicates import resolve
    # Unknown name never hits the DB stub, just returns False defensively.
    assert resolve("my-plugin", "not_a_real_predicate") is False


def test_resolve_swallows_db_errors(monkeypatch):
    """A failing predicate should return False, not bubble — plugins detail
    response must never 500 because one predicate couldn't be resolved."""
    from apps.api.src import plugin_predicates as pp

    @contextmanager
    def broken_conn():
        raise RuntimeError("DB is down")
        yield  # pragma: no cover

    monkeypatch.setattr(pp, "get_pg_conn", broken_conn)
    assert pp.resolve("my-plugin", "has_credentials") is False


# ── resolve_all ───────────────────────────────────────────────────────


def test_resolve_all_deduplicates(stub_db):
    from apps.api.src.plugin_predicates import resolve_all

    stub_db["cursor"].fetchone.return_value = (True,)
    result = resolve_all("my-plugin", ["has_credentials", "credentials_saved", "has_credentials"])

    # Two distinct predicate names → two cache keys
    assert set(result.keys()) == {"has_credentials", "credentials_saved"}
    assert result["has_credentials"] is True
    assert result["credentials_saved"] is True
