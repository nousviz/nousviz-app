"""Tests for B277 (v0.9.11.16) — centralized job state dashboard.

The dashboard composes 4 SQL queries against job_runs +
sync_schedule_registry. The queries themselves are exercised by the
manual walkthrough on dev / production; these tests pin the shape of
the response, the inline math (`will_overlap_next`, `may_overlap`),
and the section composition.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Fake pg connection ──────────────────────────────────────────────


class _FakeCursor:
    """Minimal cursor: returns successive row sets per execute() call."""

    def __init__(self, results: list[list[tuple]]):
        self._results = list(results)
        self._current: list[tuple] = []

    def execute(self, _sql: Any, _params: Any = None) -> None:
        self._current = self._results.pop(0) if self._results else []

    def fetchall(self) -> list[tuple]:
        return list(self._current)


class _FakeConn:
    def __init__(self, results: list[list[tuple]]):
        self._cursor = _FakeCursor(results)

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _fake_pg(results: list[list[tuple]]):
    """Return a callable suitable for monkeypatching get_pg_conn().

    Each entry in `results` is the row list for one execute() call —
    in dashboard order: now / recent / upcoming / failing.
    """
    def _factory():
        return _FakeConn(results)
    return _factory


# ── will_overlap_next math (inline in get_now_runs) ─────────────────


def test_get_now_runs_will_overlap_next_when_elapsed_exceeds_window(monkeypatch):
    """A 90-minute-elapsed run with next_fire 30 minutes after start
    has elapsed > window → will_overlap_next True."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
    next_fire = started + timedelta(minutes=30)
    elapsed_ms = 90 * 60 * 1000  # 90 minutes — past next_fire

    rows = [(
        1, "sync:overdue", "running", started, elapsed_ms,
        "*/30 * * * *", next_fire,
        None,  # heartbeat_at
        None,  # heartbeat_age_sec
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert len(result) == 1
    assert result[0].will_overlap_next is True


def test_get_now_runs_no_overlap_when_inside_window(monkeypatch):
    """A 5-minute-elapsed run with next_fire 30m after start →
    elapsed < window, will_overlap_next False."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
    next_fire = started + timedelta(minutes=30)
    elapsed_ms = 5 * 60 * 1000

    rows = [(
        2, "sync:fast", "running", started, elapsed_ms,
        "*/30 * * * *", next_fire,
        started + timedelta(seconds=30),  # heartbeat 30s after start
        15,  # heartbeat_age_sec — fresh
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].will_overlap_next is False


def test_get_now_runs_no_overlap_without_next_fire(monkeypatch):
    """Plugin without a sync_schedule_registry row (next_fire_at=None)
    can't be predicted — will_overlap_next must be False, not crash."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
    rows = [(3, "sync:adhoc", "running", started, 60_000, None, None, None, None)]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].will_overlap_next is False
    assert result[0].schedule_cron is None
    assert result[0].next_fire_at is None


# ── worker_alive computed from heartbeat_age_sec ────────────────────


def test_get_now_runs_worker_alive_when_heartbeat_fresh(monkeypatch):
    """v0.9.11.16.4: heartbeat_age_sec < 90 → worker_alive True for running."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
    rows = [(
        10, "sync:live", "running", started, 60_000,
        None, None,
        started + timedelta(seconds=55),  # heartbeat_at
        15,  # heartbeat_age_sec — fresh
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].worker_alive is True
    assert result[0].heartbeat_age_sec == 15


def test_get_now_runs_worker_dead_when_heartbeat_stale(monkeypatch):
    """v0.9.11.16.4: heartbeat_age_sec > 90 → worker_alive False (dead)."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 9, 0, 0, tzinfo=timezone.utc)
    rows = [(
        11, "sync:dead", "running", started, 7200_000,
        None, None,
        started + timedelta(seconds=10),
        500,  # heartbeat_age_sec — way over the 90s threshold
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].worker_alive is False
    assert result[0].heartbeat_age_sec == 500


def test_get_now_runs_worker_alive_false_when_heartbeat_null(monkeypatch):
    """v0.9.11.16.4: heartbeat_at is null → worker_alive False (no signal)."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 9, 0, 0, tzinfo=timezone.utc)
    rows = [(
        12, "sync:never-claimed", "running", started, 60_000,
        None, None,
        None,  # heartbeat_at null — pre-claim or migration artifact
        None,
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].worker_alive is False
    assert result[0].heartbeat_at is None


def test_get_now_runs_queued_row_not_alive_even_with_heartbeat(monkeypatch):
    """v0.9.11.16.4: a queued row hasn't been claimed → worker_alive False
    regardless of heartbeat (queued rows are pre-worker)."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
    rows = [(
        13, "sync:waiting", "queued", started, 5_000,
        None, None,
        None, None,
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_now_runs()
    assert result[0].worker_alive is False


# ── may_overlap math (inline in get_upcoming_runs) ──────────────────


def test_get_upcoming_may_overlap_when_avg_exceeds_90pct(monkeypatch):
    """avg_duration 580s, ms_until_fire 600s → 580/600 = 96.6% > 90% threshold."""
    from apps.api.src.services import job_dashboard as dash

    next_fire = datetime(2026, 5, 4, 11, 30, 0, tzinfo=timezone.utc)
    ms_until = 10 * 60 * 1000  # 10 min
    avg_dur = int(ms_until * 0.96)

    rows = [(
        "example-customers", "*/30 * * * *", next_fire,
        ms_until, avg_dur,
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_upcoming_runs(hours=6)
    assert result[0].may_overlap is True


def test_get_upcoming_no_overlap_when_avg_well_under(monkeypatch):
    """avg_duration is 30% of ms_until_fire → may_overlap False."""
    from apps.api.src.services import job_dashboard as dash

    next_fire = datetime(2026, 5, 4, 11, 30, 0, tzinfo=timezone.utc)
    ms_until = 10 * 60 * 1000
    avg_dur = int(ms_until * 0.3)

    rows = [(
        "fastsync", "0 * * * *", next_fire, ms_until, avg_dur,
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_upcoming_runs()
    assert result[0].may_overlap is False


def test_get_upcoming_no_overlap_when_avg_unknown(monkeypatch):
    """A plugin with no successful runs in 24h has avg_duration_ms=None
    — may_overlap must be False (we can't predict)."""
    from apps.api.src.services import job_dashboard as dash

    next_fire = datetime(2026, 5, 4, 11, 30, 0, tzinfo=timezone.utc)
    rows = [("newplugin", "0 * * * *", next_fire, 600_000, None)]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_upcoming_runs()
    assert result[0].may_overlap is False
    assert result[0].avg_duration_ms is None


# ── get_dashboard composition ───────────────────────────────────────


def test_get_dashboard_returns_four_sections_shape(monkeypatch):
    """Top-level get_dashboard() composes 4 section calls into one dict
    with collected_at + the 4 keys, even when every section is empty."""
    from apps.api.src.services import job_dashboard as dash

    # 4 empty result sets — one per section query.
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([[], [], [], []]))

    result = dash.get_dashboard()
    assert set(result.keys()) == {"collected_at", "now", "recent", "upcoming", "failing"}
    assert result["now"] == []
    assert result["recent"] == []
    assert result["upcoming"] == []
    assert result["failing"] == []
    # collected_at is an ISO-8601 string ending in +00:00 / Z (UTC)
    assert isinstance(result["collected_at"], str)
    assert "T" in result["collected_at"]


def test_get_recent_runs_truncates_error_to_dataclass(monkeypatch):
    """error_short comes back as the second-to-last selected column;
    the dataclass should preserve it intact."""
    from apps.api.src.services import job_dashboard as dash

    started = datetime(2026, 5, 4, 10, 0, 0, tzinfo=timezone.utc)
    completed = started + timedelta(seconds=32)
    rows = [(
        99, "sync:quickbooks", "error", started, completed, 32_000,
        "Missing OAuth credentials in vault",
    )]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_recent_runs(hours=12)
    assert len(result) == 1
    item = result[0]
    assert item.status == "error"
    assert item.duration_ms == 32_000
    assert item.error_short == "Missing OAuth credentials in vault"


def test_get_failing_jobs_shape(monkeypatch):
    """get_failing_jobs assembles (job_id, runs, errors, error_rate_pct,
    last_error, last_error_at) tuples into FailingItem dataclasses.

    v0.9.11.16.1: the SQL no longer applies the >50% threshold (any
    errors qualify); this test pins the row → dataclass mapping.
    """
    from apps.api.src.services import job_dashboard as dash

    last_err_a = datetime(2026, 5, 4, 10, 30, 0, tzinfo=timezone.utc)
    last_err_b = datetime(2026, 5, 4, 9, 15, 0, tzinfo=timezone.utc)
    rows = [
        ("sync:quickbooks", 24, 24, 100.0, "Missing OAuth", last_err_a),
        ("sync:example-mysql", 12, 8, 66.7, "psycopg2 OperationalError", last_err_b),
    ]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_failing_jobs()
    assert [r.job_id for r in result] == ["sync:quickbooks", "sync:example-mysql"]
    assert result[0].error_rate_pct == 100.0
    assert result[0].last_error_at == last_err_a.isoformat()
    assert result[1].errors_24h == 8
    assert result[1].last_error.startswith("psycopg2")
    assert result[1].last_error_at == last_err_b.isoformat()


def test_get_failing_jobs_includes_sporadic_errors(monkeypatch):
    """v0.9.11.16.1: a job with 1 error out of 50 runs (2%) must surface
    in the failing list — the >50% threshold previously hid it."""
    from apps.api.src.services import job_dashboard as dash

    last_err = datetime(2026, 5, 4, 10, 30, 0, tzinfo=timezone.utc)
    rows = [("sync:rare-fail", 50, 1, 2.0, "transient timeout", last_err)]
    monkeypatch.setattr(dash, "get_pg_conn", _fake_pg([rows]))

    result = dash.get_failing_jobs()
    assert len(result) == 1
    assert result[0].errors_24h == 1
    assert result[0].error_rate_pct == 2.0
    assert result[0].last_error_at is not None
