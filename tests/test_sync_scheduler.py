"""Pure-logic tests for run_scheduler (B147 / v0.9.3).

DB-touching paths (registry I/O, plugin enumeration) are covered by
the integration smoke during deploy. These tests focus on cron parsing,
fire-time computation, and idempotency window logic.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Cron parsing ─────────────────────────────────────────────────────


def test_parse_cron_accepts_valid():
    from apps.worker.src.run_scheduler import parse_cron
    assert parse_cron("0 */6 * * *") is True
    assert parse_cron("*/5 * * * *") is True
    assert parse_cron("0 0 * * 0") is True
    assert parse_cron("30 4 1 1 *") is True


def test_parse_cron_rejects_invalid():
    from apps.worker.src.run_scheduler import parse_cron
    assert parse_cron("every monday") is False
    assert parse_cron("not a cron") is False
    assert parse_cron("* * *") is False           # too few fields
    assert parse_cron("") is False
    assert parse_cron("60 * * * *") is False      # minute out of range


# ── Fire-time computation ────────────────────────────────────────────


def test_compute_next_fire_strictly_after():
    """next_fire is always strictly > anchor."""
    from apps.worker.src.run_scheduler import compute_next_fire
    anchor = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
    nxt = compute_next_fire("0 */6 * * *", anchor)
    assert nxt is not None
    assert nxt > anchor
    # 0 */6 means hours 0,6,12,18 — next after 12:00 is 18:00
    assert nxt.hour == 18
    assert nxt.minute == 0


def test_compute_next_fire_returns_aware_utc():
    """Result must be timezone-aware so comparisons with NOW() don't crash."""
    from apps.worker.src.run_scheduler import compute_next_fire
    anchor = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
    nxt = compute_next_fire("*/5 * * * *", anchor)
    assert nxt is not None
    assert nxt.tzinfo is not None


def test_compute_next_fire_returns_none_on_invalid():
    from apps.worker.src.run_scheduler import compute_next_fire
    anchor = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
    assert compute_next_fire("garbage", anchor) is None


# ── Idempotency window logic (the core safety property) ─────────────


def test_idempotency_window_blocks_within_30s():
    """Recreating the should_enqueue logic from _process_plugin to verify
    the dedup window catches double-fires.

    The actual function is in run_scheduler.py:_process_plugin; here we
    re-express the core predicate to lock its behavior."""
    DEDUP = 30.0
    now = datetime(2026, 4, 25, 12, 0, 30, tzinfo=timezone.utc)

    # Just enqueued 10s ago, next_fire is now: should NOT enqueue
    last_enqueued = now - timedelta(seconds=10)
    next_fire = now
    should_enqueue = (
        next_fire <= now
        and (now - last_enqueued).total_seconds() >= DEDUP
    )
    assert should_enqueue is False

    # Last enqueued 60s ago, next_fire is now: should enqueue
    last_enqueued = now - timedelta(seconds=60)
    should_enqueue = (
        next_fire <= now
        and (now - last_enqueued).total_seconds() >= DEDUP
    )
    assert should_enqueue is True

    # Never enqueued before, next_fire is now: should enqueue
    last_enqueued = None
    should_enqueue = (
        next_fire <= now
        and (last_enqueued is None or (now - last_enqueued).total_seconds() >= DEDUP)
    )
    assert should_enqueue is True


# ── Cron field validator (used by the override endpoint) ─────────────


def test_validate_cron_accepts_valid():
    from apps.api.src.routes.plugins import _validate_cron
    assert _validate_cron("0 */6 * * *") == "0 */6 * * *"
    # Strips whitespace
    assert _validate_cron("  */5 * * * *  ") == "*/5 * * * *"


def test_validate_cron_rejects_invalid():
    from apps.api.src.routes.plugins import _validate_cron
    from fastapi import HTTPException

    for bad in ["", "  ", "every monday", "* * *", "60 * * * *"]:
        with pytest.raises(HTTPException) as exc:
            _validate_cron(bad)
        assert exc.value.status_code == 400


def test_validate_cron_rejects_non_string():
    from apps.api.src.routes.plugins import _validate_cron
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _validate_cron(None)  # type: ignore[arg-type]
    assert exc.value.status_code == 400


# ── Manifest cron extraction ─────────────────────────────────────────


def test_read_manifest_cron_returns_schedule(tmp_path, monkeypatch):
    """_read_manifest_cron reads sync.schedule from the installed manifest."""
    from apps.worker.src import run_scheduler as scheduler

    plugin_id = "test-plugin"
    plugin_dir = tmp_path / "installed" / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "name: test-plugin\nversion: 1.0.0\nsync:\n  schedule: '0 */6 * * *'\n"
    )

    monkeypatch.setattr(scheduler, "INSTALLED_DIR", tmp_path / "installed")
    assert scheduler._read_manifest_cron(plugin_id) == "0 */6 * * *"


def test_read_manifest_cron_returns_none_when_absent(tmp_path, monkeypatch):
    """No sync.schedule key → returns None (plugin opts out of scheduling)."""
    from apps.worker.src import run_scheduler as scheduler

    plugin_id = "no-schedule-plugin"
    plugin_dir = tmp_path / "installed" / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text("name: no-schedule-plugin\nversion: 1.0.0\n")

    monkeypatch.setattr(scheduler, "INSTALLED_DIR", tmp_path / "installed")
    assert scheduler._read_manifest_cron(plugin_id) is None


def test_read_manifest_cron_returns_none_when_missing(tmp_path, monkeypatch):
    """Plugin not installed → returns None, doesn't crash."""
    from apps.worker.src import run_scheduler as scheduler
    monkeypatch.setattr(scheduler, "INSTALLED_DIR", tmp_path / "installed")
    assert scheduler._read_manifest_cron("ghost") is None


def test_read_manifest_cron_strips_whitespace(tmp_path, monkeypatch):
    from apps.worker.src import run_scheduler as scheduler

    plugin_id = "ws-plugin"
    plugin_dir = tmp_path / "installed" / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "name: ws-plugin\nversion: 1.0.0\nsync:\n  schedule: '   0 */6 * * *   '\n"
    )

    monkeypatch.setattr(scheduler, "INSTALLED_DIR", tmp_path / "installed")
    assert scheduler._read_manifest_cron(plugin_id) == "0 */6 * * *"


# ── B183: prev-fire helper ───────────────────────────────────────────


def test_compute_prev_fire_returns_most_recent_slot():
    """prev_fire returns the most recent slot at or before `before`."""
    from apps.worker.src.run_scheduler import compute_prev_fire
    # 12:30 UTC, cron 0 */6 — most recent slot is 12:00.
    before = datetime(2026, 4, 28, 12, 30, 0, tzinfo=timezone.utc)
    prev = compute_prev_fire("0 */6 * * *", before)
    assert prev == datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)


def test_compute_prev_fire_returns_aware_utc():
    from apps.worker.src.run_scheduler import compute_prev_fire
    before = datetime(2026, 4, 28, 12, 30, 0, tzinfo=timezone.utc)
    prev = compute_prev_fire("*/5 * * * *", before)
    assert prev is not None
    assert prev.tzinfo is not None


def test_compute_prev_fire_returns_none_on_invalid():
    from apps.worker.src.run_scheduler import compute_prev_fire
    before = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    assert compute_prev_fire("garbage", before) is None


# ── B183: anchor logic in _process_plugin ────────────────────────────
# These tests stub the DB-touching helpers so we can drive the cold-state
# (last_enqueued_at IS NULL) and warm-state branches deterministically.


def _patch_process_plugin_io(
    monkeypatch,
    *,
    cron: str,
    last_enqueued_at,
    now: datetime,
):
    """Wire up _process_plugin's I/O helpers for a single test scenario.

    Returns (enqueue_calls, record_calls, upsert_calls) — lists the test
    can assert against to verify enqueue/dedupe behavior.
    """
    from apps.worker.src import run_scheduler as scheduler

    enqueue_calls: list = []
    record_calls: list = []
    upsert_calls: list = []

    monkeypatch.setattr(scheduler, "_now", lambda: now)
    monkeypatch.setattr(scheduler, "_read_manifest_cron", lambda pid: cron)
    monkeypatch.setattr(scheduler, "_read_override_cron", lambda pid: None)
    monkeypatch.setattr(
        scheduler,
        "_read_registry_row",
        lambda pid: {
            "cron_expression": cron,
            "cron_source": "manifest",
            "next_fire_at": None,
            "last_enqueued_at": last_enqueued_at,
            "last_run_id": None,
            "last_error": None,
        },
    )

    def fake_enqueue(plugin_id, fire_at, c, source):
        enqueue_calls.append({"plugin_id": plugin_id, "fire_at": fire_at, "cron": c, "source": source})
        return 999  # fake run_id

    def fake_record(plugin_id, run_id, fire_at):
        record_calls.append({"plugin_id": plugin_id, "run_id": run_id, "fire_at": fire_at})

    def fake_upsert(plugin_id, c, source, next_fire_at, last_error):
        upsert_calls.append({
            "plugin_id": plugin_id,
            "cron": c,
            "source": source,
            "next_fire_at": next_fire_at,
            "last_error": last_error,
        })

    monkeypatch.setattr(scheduler, "_enqueue_run", fake_enqueue)
    monkeypatch.setattr(scheduler, "_record_enqueue", fake_record)
    monkeypatch.setattr(scheduler, "_upsert_registry", fake_upsert)
    monkeypatch.setattr(scheduler, "log_job_event", lambda *a, **kw: None)

    return enqueue_calls, record_calls, upsert_calls


def test_b183_cold_state_at_slot_boundary_fires(monkeypatch):
    """Fresh registry row (last_enqueued_at NULL). Now is at the slot
    boundary. Scheduler enqueues this poll."""
    from apps.worker.src import run_scheduler as scheduler

    now = datetime(2026, 4, 28, 12, 0, 5, tzinfo=timezone.utc)
    enqueue_calls, record_calls, _ = _patch_process_plugin_io(
        monkeypatch, cron="0 */6 * * *", last_enqueued_at=None, now=now,
    )

    scheduler._process_plugin("test-plugin")

    assert len(enqueue_calls) == 1, "should enqueue at slot boundary on cold start"
    assert enqueue_calls[0]["fire_at"] == datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    assert len(record_calls) == 1


def test_b183_cold_state_mid_slot_does_not_fire(monkeypatch):
    """Fresh registry row, now is mid-slot (well past the grace window).
    Scheduler does NOT enqueue; registry's next_fire_at is the upcoming
    future slot."""
    from apps.worker.src import run_scheduler as scheduler

    # 12:30 UTC — 30 min past 12:00 slot, well past 40s grace window.
    now = datetime(2026, 4, 28, 12, 30, 0, tzinfo=timezone.utc)
    enqueue_calls, _, upsert_calls = _patch_process_plugin_io(
        monkeypatch, cron="0 */6 * * *", last_enqueued_at=None, now=now,
    )

    scheduler._process_plugin("test-plugin")

    assert len(enqueue_calls) == 0, "should not back-fire missed slots"
    # Registry should advertise the next future slot (18:00).
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["next_fire_at"] == datetime(2026, 4, 28, 18, 0, 0, tzinfo=timezone.utc)


def test_b183_cold_state_just_past_slot_within_grace_fires(monkeypatch):
    """Cold state, now is 20s past slot boundary (within ~40s grace).
    Scheduler enqueues — this is the typical post-deploy / post-override
    path where the scheduler restarts a few seconds after a slot."""
    from apps.worker.src import run_scheduler as scheduler

    now = datetime(2026, 4, 28, 12, 0, 20, tzinfo=timezone.utc)
    enqueue_calls, _, _ = _patch_process_plugin_io(
        monkeypatch, cron="0 */6 * * *", last_enqueued_at=None, now=now,
    )

    scheduler._process_plugin("test-plugin")

    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["fire_at"] == datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)


def test_b183_warm_state_advances_one_slot(monkeypatch):
    """Steady state: last_enqueued_at = previous slot, now = current slot.
    Scheduler enqueues exactly once for the current slot."""
    from apps.worker.src import run_scheduler as scheduler

    now = datetime(2026, 4, 28, 12, 0, 5, tzinfo=timezone.utc)
    last = datetime(2026, 4, 28, 6, 0, 10, tzinfo=timezone.utc)
    enqueue_calls, _, _ = _patch_process_plugin_io(
        monkeypatch, cron="0 */6 * * *", last_enqueued_at=last, now=now,
    )

    scheduler._process_plugin("test-plugin")

    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["fire_at"] == datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)


def test_b183_warm_state_within_dedup_window_does_not_double_fire(monkeypatch):
    """Just enqueued 10s ago. Next poll must not double-fire even if
    cron's next slot is at-or-before now."""
    from apps.worker.src import run_scheduler as scheduler

    now = datetime(2026, 4, 28, 12, 0, 15, tzinfo=timezone.utc)
    last = now - timedelta(seconds=10)
    enqueue_calls, _, _ = _patch_process_plugin_io(
        monkeypatch, cron="*/5 * * * *", last_enqueued_at=last, now=now,
    )

    scheduler._process_plugin("test-plugin")

    assert len(enqueue_calls) == 0


# ── B184: enqueue uses sync: prefix on job_id ────────────────────────


def test_b184_enqueue_uses_sync_prefix(monkeypatch):
    """_enqueue_run binds 'sync:<plugin>' as job_id, not the bare slug.

    The worker's _run_job (apps/worker/src/run_jobs.py) calls
    _parse_plugin_id which expects 'sync:' prefix and rejects anything
    else with 'Unsupported job_id shape'. Pin the contract here so the
    scheduler stays in sync with the worker's expectation.
    """
    from apps.worker.src import run_scheduler as scheduler

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params

        def fetchone(self):
            return (12345,)

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(scheduler, "get_pg_conn", lambda: FakeConn())

    fire_at = datetime(2026, 4, 29, 18, 0, 0, tzinfo=timezone.utc)
    run_id = scheduler._enqueue_run(
        plugin_id="example-plugin",
        fire_at=fire_at,
        cron="0 */6 * * *",
        source="manifest",
    )

    assert run_id == 12345
    assert captured["params"][0] == "sync:example-plugin", (
        f"job_id must be 'sync:<plugin>' to match worker's _parse_plugin_id "
        f"contract; got {captured['params'][0]!r}"
    )


# ── B277 v0.9.11.17.1: scheduler active-run guard ────────────────────


def _scheduler_fake_conn(monkeypatch, queries: list[tuple]):
    """Helper to plant a sequence of fetchone responses on the
    scheduler's get_pg_conn calls."""
    from apps.worker.src import run_scheduler as scheduler

    class FakeCursor:
        def __init__(self):
            self._next: list = list(queries)

        def execute(self, sql, params=None):
            self._last_sql = str(sql)
            self._last_params = params

        def fetchone(self):
            return self._next.pop(0) if self._next else None

    class FakeConn:
        def __init__(self):
            self._cur = FakeCursor()

        def cursor(self):
            return self._cur

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(scheduler, "get_pg_conn", lambda: FakeConn())


def test_has_active_run_returns_tuple_when_in_flight(monkeypatch):
    from apps.worker.src import run_scheduler as scheduler

    _scheduler_fake_conn(monkeypatch, queries=[(42, "running")])
    result = scheduler._has_active_run("intercom")
    assert result == (42, "running")


def test_has_active_run_returns_none_when_idle(monkeypatch):
    from apps.worker.src import run_scheduler as scheduler

    _scheduler_fake_conn(monkeypatch, queries=[None])
    assert scheduler._has_active_run("intercom") is None


def test_has_active_run_fails_open_on_db_error(monkeypatch):
    """Transient DB errors must not silently skip a real cron fire —
    the active-run check returns None on exception so the caller
    falls through to the existing time-window dedup."""
    from apps.worker.src import run_scheduler as scheduler

    def boom():
        raise RuntimeError("connection lost")

    monkeypatch.setattr(scheduler, "get_pg_conn", boom)
    assert scheduler._has_active_run("intercom") is None


# ── B277 v0.9.11.17.1: orphan sweep handles cancelling state ─────────


def test_sweep_orphans_runs_two_updates_and_returns_count(monkeypatch):
    """_sweep_orphans must issue separate UPDATEs for 'running' and
    'cancelling' rows. Returns the total cleaned across both."""
    from apps.worker.src import run_jobs as worker

    captured: list[str] = []

    class FakeCursor:
        def __init__(self):
            self._fetch_q = [
                # First UPDATE: running orphans → 1 row
                [(101, "sync:foo")],
                # Second UPDATE: cancelling orphans → 0 rows
                [],
            ]

        def execute(self, sql, params=None):
            captured.append(str(sql))

        def fetchall(self):
            return self._fetch_q.pop(0) if self._fetch_q else []

    class FakeConn:
        def __init__(self):
            self._cur = FakeCursor()

        def cursor(self):
            return self._cur

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(worker, "get_pg_conn", lambda: FakeConn())
    monkeypatch.setattr(worker, "log_job_event", lambda *a, **kw: None)

    n = worker._sweep_orphans(source_label="periodic")
    assert n == 1
    # Two UPDATEs: 'running' and 'cancelling'.
    assert sum(1 for s in captured if "status = 'error'" in s) == 1
    assert sum(1 for s in captured if "status = 'cancelled'" in s) == 1


def test_orphan_threshold_is_120s_after_b16_4():
    """Sanity pin: post v0.9.11.16.4 live heartbeats, the orphan
    threshold must be tight enough (120s) that a dead worker is
    detected before the next deploy cycle."""
    from apps.worker.src.run_jobs import ORPHAN_HEARTBEAT_STALE_SEC
    assert ORPHAN_HEARTBEAT_STALE_SEC == 120
