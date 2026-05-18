"""
Tests for P204 (plugin load failure visibility) + P205 (SDK sanity +
plugin-route exception logging).
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── P204: LOAD_STATUS tracking ───────────────────────────────────────


def test_record_load_success_populates_status():
    from apps.api.src import plugin_loader

    plugin_loader.LOAD_STATUS.pop("test-plug-succ", None)
    plugin_loader._record_load_success("test-plug-succ")

    assert plugin_loader.LOAD_STATUS["test-plug-succ"] == {"routes_registered": True}


def test_record_load_failure_captures_exception(monkeypatch):
    from apps.api.src import plugin_loader

    # Stub log_job_event so test doesn't touch DB
    monkeypatch.setattr(
        "apps.api.src.log_events.log_job_event",
        lambda *a, **kw: None,
    )

    plugin_loader.LOAD_STATUS.pop("test-plug-fail", None)
    try:
        raise ModuleNotFoundError("No module named 'something'")
    except ModuleNotFoundError as exc:
        plugin_loader._record_load_failure("test-plug-fail", exc, stage="routes")

    status = plugin_loader.LOAD_STATUS["test-plug-fail"]
    assert status["routes_registered"] is False
    assert status["stage"] == "routes"
    assert status["exception_class"] == "ModuleNotFoundError"
    assert "something" in status["exception_message"]
    assert "traceback_tail" in status


def test_record_load_failure_survives_app_logs_failure(monkeypatch):
    """If log_job_event itself fails (e.g., app_logs table missing), the
    loader must still record in LOAD_STATUS."""
    from apps.api.src import plugin_loader

    def boom(*a, **kw):
        raise RuntimeError("app_logs table missing")

    monkeypatch.setattr("apps.api.src.log_events.log_job_event", boom)

    plugin_loader.LOAD_STATUS.pop("test-resilient", None)
    try:
        raise ValueError("plugin broke")
    except ValueError as exc:
        plugin_loader._record_load_failure("test-resilient", exc)

    assert plugin_loader.LOAD_STATUS["test-resilient"]["routes_registered"] is False
    assert plugin_loader.LOAD_STATUS["test-resilient"]["exception_class"] == "ValueError"


# ── P205d: plugin-route rate limiter ─────────────────────────────────


def test_plugin_route_regex_matches_plugin_paths():
    from apps.api.src.middleware.errors import _PLUGIN_ROUTE_RE

    assert _PLUGIN_ROUTE_RE.match("/api/plugins/example-mysql/test-connection")
    assert _PLUGIN_ROUTE_RE.match("/api/plugins/abc/x")
    m = _PLUGIN_ROUTE_RE.match("/api/plugins/my-plugin/items")
    assert m.group(1) == "my-plugin"


def test_plugin_route_regex_rejects_non_plugin_paths():
    from apps.api.src.middleware.errors import _PLUGIN_ROUTE_RE

    # Plugin LIST endpoint is a core route, not a plugin route
    assert _PLUGIN_ROUTE_RE.match("/api/plugins") is None
    # Bare plugin detail (no trailing slash/subpath) — core route
    assert _PLUGIN_ROUTE_RE.match("/api/plugins/foo") is None
    # Completely unrelated
    assert _PLUGIN_ROUTE_RE.match("/api/health") is None


def _allowed(mw, path, exc_class):
    """Test helper: B139 changed _should_log_route_error to return
    (allowed, drops_to_report). For tests that only care about whether
    the event was allowed, unwrap the tuple."""
    return mw._should_log_route_error(path, exc_class)[0]


def test_should_log_route_error_allows_up_to_limit(monkeypatch):
    """B131: rate limiter is keyed by (path, exception_class)."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()

    # First 10 go through
    for _ in range(10):
        assert _allowed(mw, "/api/plugins/plug/x", "ValueError") is True


def test_should_log_route_error_drops_past_limit(monkeypatch):
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()

    for _ in range(10):
        mw._should_log_route_error("/api/plugins/plug/x", "ValueError")

    # 11th within the window: dropped
    assert _allowed(mw, "/api/plugins/plug/x", "ValueError") is False


def test_should_log_route_error_different_paths_are_independent():
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()

    # path_a uses up its window
    for _ in range(10):
        mw._should_log_route_error("/api/a", "ValueError")
    assert _allowed(mw, "/api/a", "ValueError") is False

    # path_b has its own quota
    assert _allowed(mw, "/api/b", "ValueError") is True


def test_should_log_route_error_different_exc_classes_are_independent():
    """Same path raising two different exception classes are tracked
    separately. ValueError limit doesn't gate TypeError."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()

    for _ in range(10):
        mw._should_log_route_error("/api/x", "ValueError")
    assert _allowed(mw, "/api/x", "ValueError") is False

    # Same path, different exception → fresh quota
    assert _allowed(mw, "/api/x", "TypeError") is True


def test_should_log_route_error_window_expiry(monkeypatch):
    """Timestamps older than the window are evicted."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()
    key = ("/api/plugins/plug/x", "ValueError")

    # Pre-populate with 10 stale timestamps (2 minutes ago)
    stale = time.time() - 120
    mw._rate_timestamps[key] = [stale] * 10

    # Should now be allowed because stale stamps get evicted
    assert _allowed(mw, "/api/plugins/plug/x", "ValueError") is True


# B139: rate-limit drop visibility — rollup row on next allowed event ──


def test_b139_drops_counted_when_suppressed():
    """B139: when an event is suppressed by the rate limit, the drop
    counter for that key increments; allowed=False, drops_to_report=0."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()
    key = ("/api/burning", "RuntimeError")

    for _ in range(10):
        mw._should_log_route_error(*key)

    # Three suppressed
    for _ in range(3):
        allowed, drops = mw._should_log_route_error(*key)
        assert allowed is False
        assert drops == 0

    # Internal state: 3 drops accumulated
    assert mw._drop_counter[key] == 3


def test_b139_drops_drained_on_next_allowed_event():
    """B139: when the next event is allowed (window slid), the helper
    returns drops_to_report = the count that was suppressed."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()
    key = ("/api/burning", "RuntimeError")

    # Saturate
    for _ in range(10):
        mw._should_log_route_error(*key)
    # Suppress 5
    for _ in range(5):
        mw._should_log_route_error(*key)
    assert mw._drop_counter[key] == 5

    # Force the window to slide
    mw._rate_timestamps[key] = [time.time() - 120] * 10

    # Next allowed event reports the 5 drops, then drops counter is empty
    allowed, drops = mw._should_log_route_error(*key)
    assert allowed is True
    assert drops == 5
    assert key not in mw._drop_counter or mw._drop_counter[key] == 0


def test_b139_no_rollup_when_no_drops():
    """If nothing was suppressed, drops_to_report stays 0."""
    from apps.api.src.middleware import errors as mw

    mw._rate_timestamps.clear()
    mw._drop_counter.clear()
    allowed, drops = mw._should_log_route_error("/api/clean", "ValueError")
    assert allowed is True
    assert drops == 0


# B131: source tagging — core_route vs plugin_route ────────────────────


def test_log_route_500_sets_core_route_source(monkeypatch):
    """A 500 on a non-plugin path gets source=core_route, no plugin_id."""
    from apps.api.src.middleware import errors as mw
    mw._rate_timestamps.clear()

    captured = []

    def fake_log_job_event(level, message, detail, source=None, **kwargs):
        captured.append({"level": level, "message": message, "detail": detail, "source": source})

    monkeypatch.setattr("apps.api.src.log_events.log_job_event", fake_log_job_event)

    try:
        raise ValueError("boom")
    except ValueError as exc:
        import traceback as tb
        mw.ErrorSanitizationMiddleware._log_route_500(
            "/api/users", "POST", exc, tb.format_exc()
        )

    assert len(captured) == 1
    # source kwarg sets the app_logs.source column value (the bug v0.9.1
    # caught was passing source only inside detail, where it became JSON
    # data instead of a queryable column).
    assert captured[0]["source"] == "core_route"
    detail = captured[0]["detail"]
    assert detail["source"] == "core_route"
    assert "plugin_id" not in detail
    assert detail["method"] == "POST"
    assert detail["path"] == "/api/users"
    assert detail["exception_class"] == "ValueError"
    assert "boom" in detail["exception_message"]


def test_log_route_500_sets_plugin_route_source(monkeypatch):
    """A 500 on /api/plugins/{slug}/... gets source=plugin_route AND plugin_id."""
    from apps.api.src.middleware import errors as mw
    mw._rate_timestamps.clear()

    captured = []

    def fake_log_job_event(level, message, detail, source=None, **kwargs):
        captured.append({"detail": detail, "source": source, **kwargs})

    monkeypatch.setattr("apps.api.src.log_events.log_job_event", fake_log_job_event)

    try:
        raise RuntimeError("plugin broke")
    except RuntimeError as exc:
        import traceback as tb
        mw.ErrorSanitizationMiddleware._log_route_500(
            "/api/plugins/starter-plugin/items", "GET", exc, tb.format_exc()
        )

    assert len(captured) == 1
    # The kwarg `source` becomes the app_logs.source column value.
    # The same string also appears inside detail (for backward compat
    # with operators querying detail->>'source').
    assert captured[0]["source"] == "plugin_route"
    detail = captured[0]["detail"]
    assert detail["source"] == "plugin_route"
    # B208 (v0.9.6.1): plugin_id is now passed as a keyword-only kwarg to
    # log_job_event so it lands in the dedicated app_logs.plugin_id column.
    # The helper's setdefault would also put it in detail, but since this
    # test stubs log_job_event before that merge happens, we check kwargs.
    assert captured[0]["plugin_id"] == "starter-plugin"
    assert detail["exception_class"] == "RuntimeError"


def test_log_route_500_respects_rate_limit(monkeypatch):
    """11th call within window does NOT log."""
    from apps.api.src.middleware import errors as mw
    mw._rate_timestamps.clear()

    captured = []

    def fake_log_job_event(level, message, detail, source=None, **kwargs):
        captured.append(detail)

    monkeypatch.setattr("apps.api.src.log_events.log_job_event", fake_log_job_event)

    import traceback as tb_mod
    try:
        raise ValueError("x")
    except ValueError as exc:
        for _ in range(15):
            mw.ErrorSanitizationMiddleware._log_route_500(
                "/api/foo", "GET", exc, tb_mod.format_exc()
            )

    assert len(captured) == 10  # cap


def test_log_route_500_survives_log_failure(monkeypatch):
    """If log_job_event itself raises, the helper catches and continues —
    must never mask the original 500."""
    from apps.api.src.middleware import errors as mw
    mw._rate_timestamps.clear()

    def boom(*a, **kw):
        raise RuntimeError("app_logs offline")

    monkeypatch.setattr("apps.api.src.log_events.log_job_event", boom)

    import traceback as tb_mod
    try:
        raise ValueError("real error")
    except ValueError as exc:
        # Should not raise
        mw.ErrorSanitizationMiddleware._log_route_500(
            "/api/foo", "GET", exc, tb_mod.format_exc()
        )


# ── B132: DBLogHandler reads structured extras ───────────────────────


def test_db_log_handler_reads_record_detail(monkeypatch):
    """When a logger call passes `extra={"detail": {...}}`, the handler
    merges it into the app_logs row's detail JSON."""
    from apps.api.src.log_handler import DBLogHandler
    import logging

    captured = []

    def fake_get_pg_conn():
        from contextlib import contextmanager

        @contextmanager
        def cm():
            class _Cur:
                def execute(self, sql, params):
                    captured.append({"sql": sql, "params": params})

            class _Conn:
                def cursor(self):
                    return _Cur()

            yield _Conn()

        return cm()

    monkeypatch.setattr("apps.api.src.db.get_pg_conn", fake_get_pg_conn)

    handler = DBLogHandler(level=logging.INFO)
    record = logging.LogRecord(
        name="nousviz.plugin_loader",
        level=logging.ERROR,
        pathname="x",
        lineno=1,
        msg="Plugin foo failed",
        args=(),
        exc_info=None,
    )
    record.detail = {"plugin_id": "foo", "stage": "routes", "exception_class": "ValueError"}

    handler.emit(record)

    assert len(captured) == 1
    params = captured[0]["params"]
    # params: (level, source, message, detail_json)
    import json
    detail = json.loads(params[3])
    assert detail["plugin_id"] == "foo"
    assert detail["stage"] == "routes"
    assert detail["exception_class"] == "ValueError"


def test_db_log_handler_reads_source_override(monkeypatch):
    """`extra={"source_override": "..."}` replaces the auto-derived source."""
    from apps.api.src.log_handler import DBLogHandler
    import logging

    captured = []

    def fake_get_pg_conn():
        from contextlib import contextmanager

        @contextmanager
        def cm():
            class _Cur:
                def execute(self, sql, params):
                    captured.append(params)

            class _Conn:
                def cursor(self):
                    return _Cur()

            yield _Conn()

        return cm()

    monkeypatch.setattr("apps.api.src.db.get_pg_conn", fake_get_pg_conn)

    handler = DBLogHandler(level=logging.INFO)
    record = logging.LogRecord(
        name="nousviz.api.plugins",  # would normally map to "plugin_install"
        level=logging.ERROR,
        pathname="x",
        lineno=1,
        msg="manual override",
        args=(),
        exc_info=None,
    )
    record.source_override = "custom_tag"

    handler.emit(record)

    # params[1] is source
    assert captured[0][1] == "custom_tag"


def test_db_log_handler_no_extras_backward_compat(monkeypatch):
    """A plain logger.info without `extra=` writes the row with auto-derived
    source and empty detail (modulo exc_info auto-extraction). Backward-compat."""
    from apps.api.src.log_handler import DBLogHandler
    import logging
    import json

    captured = []

    def fake_get_pg_conn():
        from contextlib import contextmanager

        @contextmanager
        def cm():
            class _Cur:
                def execute(self, sql, params):
                    captured.append(params)

            class _Conn:
                def cursor(self):
                    return _Cur()

            yield _Conn()

        return cm()

    monkeypatch.setattr("apps.api.src.db.get_pg_conn", fake_get_pg_conn)

    handler = DBLogHandler(level=logging.INFO)
    record = logging.LogRecord(
        name="nousviz.plugin_loader",
        level=logging.INFO,
        pathname="x",
        lineno=1,
        msg="plugin loaded fine",
        args=(),
        exc_info=None,
    )
    handler.emit(record)

    assert len(captured) == 1
    # B208: INSERT shape grew from 4 columns to 7 (level, source, message,
    # detail, plugin_id, actor_user_id, run_id). Unpack accordingly.
    level, source, message, detail_json, plugin_id, actor_user_id, run_id = captured[0]
    assert source == "plugin_loader"  # auto from logger name
    assert message == "plugin loaded fine"
    assert detail_json == "{}"  # empty
    # Pre-B208 callers don't pass these — columns NULL.
    assert plugin_id is None
    assert actor_user_id is None
    assert run_id is None


def test_record_load_failure_does_not_double_log(monkeypatch):
    """B132: _record_load_failure used to call log_job_event explicitly,
    which combined with the existing DBLogHandler-attached logger.error
    produced TWO app_logs rows per failure. v0.9.1 removes the explicit
    log_job_event call — only the logger.error path remains."""
    from apps.api.src import plugin_loader

    # Track if log_job_event is called — it should NOT be in v0.9.1
    log_event_calls = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_job_event",
        lambda *a, **kw: log_event_calls.append((a, kw)),
    )

    # Track logger.error calls on plugin_loader's logger
    error_calls = []
    real_error = plugin_loader.logger.error

    def spy_error(msg, *a, **kw):
        error_calls.append({"msg": msg, "extra": kw.get("extra", {})})

    monkeypatch.setattr(plugin_loader.logger, "error", spy_error)

    plugin_loader.LOAD_STATUS.pop("dedup-test", None)
    try:
        raise RuntimeError("something broke")
    except RuntimeError as exc:
        plugin_loader._record_load_failure("dedup-test", exc, stage="routes")

    # log_job_event must NOT have been called — that path is gone
    assert log_event_calls == []
    # logger.error called once, with structured extras
    assert len(error_calls) == 1
    extra = error_calls[0]["extra"]
    assert "detail" in extra
    assert extra["detail"]["plugin_id"] == "dedup-test"
    assert extra["detail"]["exception_class"] == "RuntimeError"
    assert extra["detail"]["stage"] == "routes"
