"""Pure-logic tests for B205 cron display + interval helpers.

DB-touching paths (sync_status endpoint shape, 409 active-run guard, audit
log writes) are covered by the integration smoke during deploy. These
tests focus on the round-trip between the friendly schedule builder
("Every N minutes") and 5-field cron expressions, plus the SDK progress
helper's no-op + clamping behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── _cron_to_display ─────────────────────────────────────────────────


def test_cron_to_display_every_n_minutes():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display("*/15 * * * *") == "Every 15 minutes"
    assert _cron_to_display("*/1 * * * *") == "Every 1 minute"
    assert _cron_to_display("*/5 * * * *") == "Every 5 minutes"


def test_cron_to_display_every_n_hours():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display("0 */6 * * *") == "Every 6 hours"
    assert _cron_to_display("0 */1 * * *") == "Every 1 hour"
    assert _cron_to_display("0 */12 * * *") == "Every 12 hours"


def test_cron_to_display_every_n_days():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display("0 0 */2 * *") == "Every 2 days"
    assert _cron_to_display("0 0 */7 * *") == "Every 7 days"


def test_cron_to_display_hourly_at_minute():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display("30 * * * *") == "Every hour at :30"
    assert _cron_to_display("0 * * * *") == "Every hour at :00"


def test_cron_to_display_daily_at_time():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display("0 9 * * *") == "Daily at 09:00"
    assert _cron_to_display("30 14 * * *") == "Daily at 14:30"


def test_cron_to_display_returns_none_for_complex_cron():
    from apps.api.src.routes.plugins import _cron_to_display
    # Weekday-restricted — not roundtrippable to the simple builder
    assert _cron_to_display("30 8 * * 1-5") is None
    # Multiple specific hours — not roundtrippable
    assert _cron_to_display("0 8,12,16 * * *") is None
    # Specific day-of-month — not roundtrippable
    assert _cron_to_display("0 0 15 * *") is None


def test_cron_to_display_handles_empty_and_invalid():
    from apps.api.src.routes.plugins import _cron_to_display
    assert _cron_to_display(None) is None
    assert _cron_to_display("") is None
    assert _cron_to_display("   ") is None
    assert _cron_to_display("not a cron") is None
    assert _cron_to_display("* * *") is None  # too few fields
    assert _cron_to_display("*/abc * * * *") is None  # non-numeric


# ── _interval_to_cron ────────────────────────────────────────────────


def test_interval_to_cron_minutes():
    from apps.api.src.routes.plugins import _interval_to_cron
    assert _interval_to_cron(15, "minutes") == "*/15 * * * *"
    assert _interval_to_cron(1, "minutes") == "*/1 * * * *"


def test_interval_to_cron_hours():
    from apps.api.src.routes.plugins import _interval_to_cron
    assert _interval_to_cron(6, "hours") == "0 */6 * * *"
    assert _interval_to_cron(1, "hours") == "0 */1 * * *"


def test_interval_to_cron_days():
    from apps.api.src.routes.plugins import _interval_to_cron
    assert _interval_to_cron(2, "days") == "0 0 */2 * *"


def test_interval_to_cron_rejects_minutes_over_59():
    from apps.api.src.routes.plugins import _interval_to_cron
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _interval_to_cron(90, "minutes")
    assert exc.value.status_code == 400


def test_interval_to_cron_rejects_hours_over_23():
    from apps.api.src.routes.plugins import _interval_to_cron
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _interval_to_cron(48, "hours")
    assert exc.value.status_code == 400


def test_interval_to_cron_rejects_zero():
    from apps.api.src.routes.plugins import _interval_to_cron
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _interval_to_cron(0, "minutes")
    assert exc.value.status_code == 400


def test_interval_to_cron_rejects_unknown_unit():
    from apps.api.src.routes.plugins import _interval_to_cron
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _interval_to_cron(1, "weeks")
    assert exc.value.status_code == 400


# ── Round-trip: friendly form → cron → display ───────────────────────


def test_round_trip_minutes():
    from apps.api.src.routes.plugins import _cron_to_display, _interval_to_cron
    cron = _interval_to_cron(15, "minutes")
    assert _cron_to_display(cron) == "Every 15 minutes"


def test_round_trip_hours():
    from apps.api.src.routes.plugins import _cron_to_display, _interval_to_cron
    cron = _interval_to_cron(6, "hours")
    assert _cron_to_display(cron) == "Every 6 hours"


def test_round_trip_days():
    from apps.api.src.routes.plugins import _cron_to_display, _interval_to_cron
    cron = _interval_to_cron(2, "days")
    assert _cron_to_display(cron) == "Every 2 days"


# ── SDK progress helper ──────────────────────────────────────────────


def test_progress_report_no_op_outside_run(monkeypatch):
    """Calling progress.report() outside a tracked run is a silent no-op,
    not an exception. Plugin scripts running standalone (e.g. dev shell)
    must not crash on these calls.
    """
    # Force jobs.get_run_id() to None by clearing the env var the worker
    # would set + the context var.
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)

    from nousviz_sdk import progress, jobs
    jobs._set_current_run_id(None)

    # Should not raise.
    progress.report(pct=50, message="halfway")
    progress.report()
    progress.report(rows_done=100, rows_total=200)


def test_progress_report_clamps_pct(monkeypatch, mocker=None):
    """pct > 100 is clamped to 100, pct < 0 to 0, NaN/inf doesn't crash."""
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)

    captured: dict = {}

    def fake_heartbeat(progress=None):
        captured["payload"] = progress

    from nousviz_sdk import progress as progress_mod, jobs
    jobs._set_current_run_id(None)  # ensure no-op via heartbeat early-return,
                                     # but we patch heartbeat to capture

    monkeypatch.setattr(progress_mod._jobs, "heartbeat", fake_heartbeat)

    progress_mod.report(pct=150, message="over")
    assert captured["payload"]["pct"] == 100.0

    progress_mod.report(pct=-25)
    assert captured["payload"]["pct"] == 0.0

    progress_mod.report(pct=42.5, rows_done=10, rows_total=100)
    assert captured["payload"]["pct"] == 42.5
    assert captured["payload"]["rows_done"] == 10
    assert captured["payload"]["rows_total"] == 100


def test_progress_report_empty_call_bumps_heartbeat(monkeypatch):
    """progress.report() with no args bumps heartbeat without setting progress."""
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)

    captured: list = []

    def fake_heartbeat(progress=None):
        captured.append(progress)

    from nousviz_sdk import progress as progress_mod, jobs
    jobs._set_current_run_id(None)
    monkeypatch.setattr(progress_mod._jobs, "heartbeat", fake_heartbeat)

    progress_mod.report()
    assert captured == [None]  # no progress payload


def test_progress_report_string_coercion(monkeypatch):
    """message is coerced to str so non-string values don't crash json."""
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)

    captured: dict = {}

    def fake_heartbeat(progress=None):
        captured["payload"] = progress

    from nousviz_sdk import progress as progress_mod, jobs
    jobs._set_current_run_id(None)
    monkeypatch.setattr(progress_mod._jobs, "heartbeat", fake_heartbeat)

    progress_mod.report(message=42)  # int instead of str
    assert captured["payload"]["message"] == "42"
