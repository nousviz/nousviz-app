"""B238 (v0.9.10.1): tests for log_event's subprocess direct-write path.

Three branches to cover:
1. NOUSVIZ_PLUGIN_ID unset → existing test-harness fallback (stderr only).
2. NOUSVIZ_PLUGIN_ID set + DBLogHandler attached → existing logger path.
3. NOUSVIZ_PLUGIN_ID set + no handler → new direct-INSERT path.

Plus the DB-error fallback that catches exceptions in the new path.

These tests don't require a running database — they mock get_pg_conn
(or its surrounding context) to verify the call shape.
"""
from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sdk"))


def _reset_handler_cache():
    """Reset the per-process cache so each test starts fresh."""
    import nousviz_sdk.logging as mod
    mod._handler_attached_cache = None  # noqa: SLF001


def _drop_handlers():
    """Detach any handlers — including root — to simulate a true
    worker-subprocess context where no handler is attached anywhere
    along the logger chain.

    pytest's caplog mounts handlers on root by default, which our
    _has_db_log_handler now correctly walks up to detect. To exercise
    the subprocess direct-write path in tests, we need a clean tree.
    """
    # nousviz.plugin and children
    parent = logging.getLogger("nousviz.plugin")
    parent.handlers.clear()
    for name in list(logging.root.manager.loggerDict.keys()):
        if name.startswith("nousviz.plugin"):
            logging.getLogger(name).handlers.clear()
    # Root — pytest caplog hangs handlers here.
    _saved_root_handlers = list(logging.root.handlers)
    logging.root.handlers.clear()
    return _saved_root_handlers


def _restore_root_handlers(saved):
    """Restore the root handlers we cleared in _drop_handlers (so
    subsequent tests' caplog still works)."""
    logging.root.handlers.clear()
    logging.root.handlers.extend(saved)


# ── Branch 1: test-harness fallback (NOUSVIZ_PLUGIN_ID unset) ─────────

def test_log_event_with_no_plugin_id_writes_to_stderr_only(monkeypatch, capsys):
    """Existing behavior preserved: outside a NousViz context, log_event
    prints to stderr and doesn't try to write to the DB."""
    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)
    _reset_handler_cache()
    saved = _drop_handlers()
    try:
        from nousviz_sdk.logging import log_event
        log_event("info", "hello from a test harness")

        captured = capsys.readouterr()
        assert "hello from a test harness" in captured.err
        assert "[nousviz_sdk]" in captured.err
        assert "no NOUSVIZ_PLUGIN_ID" in captured.err
    finally:
        _restore_root_handlers(saved)


# ── Branch 2: handler attached (API process semantics) ────────────────

def test_log_event_with_handler_attached_uses_logger_path(monkeypatch):
    """When a DB-routing handler is attached to nousviz.plugin (or
    nousviz.plugin.<id>), log_event delegates to logger.log() rather than
    doing a direct DB write.

    The detection is class-name-based (handler class named 'DBLogHandler'
    or 'LogCaptureHandler') so tests need to use a matching class name
    to exercise the logger path. A plain StreamHandler at root does NOT
    trigger the logger path — it's just stderr output, which is exactly
    what we'd want to bypass."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "test-plugin")
    _reset_handler_cache()
    saved = _drop_handlers()

    # Attach a fake handler whose class name matches the production
    # DBLogHandler so log_event detects it as a DB-routing handler.
    captured_records = []

    class DBLogHandler(logging.Handler):  # name matches the SDK's detection list
        def emit(self, record):
            captured_records.append(record)

    handler = DBLogHandler()
    parent = logging.getLogger("nousviz.plugin")
    parent.addHandler(handler)
    parent.setLevel(logging.INFO)

    try:
        # Patch _direct_write_app_logs to ensure it's NOT called
        with patch("nousviz_sdk.logging._direct_write_app_logs") as direct_mock:
            from nousviz_sdk.logging import log_event
            log_event("info", "via logger path", detail={"foo": 1})

            assert direct_mock.call_count == 0, "direct write must not fire when handler is attached"
            assert len(captured_records) == 1
            record = captured_records[0]
            assert record.getMessage() == "via logger path"
            assert getattr(record, "source_override", None) == "plugin"
            assert getattr(record, "detail", None) == {"foo": 1, "plugin_id": "test-plugin"}
    finally:
        _drop_handlers()
        _restore_root_handlers(saved)


# ── Branch 3: no handler (subprocess direct-write path) ────────────────

def test_log_event_with_no_handler_does_direct_write(monkeypatch):
    """When NOUSVIZ_PLUGIN_ID is set but no handler is attached, log_event
    invokes the direct-INSERT path with the right SQL parameters."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "cloudflare-analytics")
    monkeypatch.setenv("NOUSVIZ_JOB_RUN_ID", "12345")
    _reset_handler_cache()
    saved = _drop_handlers()

    captured_args = []

    def _fake_direct_write(db_level, message, detail, plugin_id, run_id):
        captured_args.append({
            "db_level": db_level,
            "message": message,
            "detail": detail,
            "plugin_id": plugin_id,
            "run_id": run_id,
        })

    try:
        with patch("nousviz_sdk.logging._direct_write_app_logs", side_effect=_fake_direct_write):
            from nousviz_sdk.logging import log_event
            log_event("warn", "URL-level metrics failed", detail={"zone": "example.com"})

        assert len(captured_args) == 1
        call = captured_args[0]
        assert call["db_level"] == "warning", "warn maps to warning in app_logs.level"
        assert call["message"] == "URL-level metrics failed"
        assert call["plugin_id"] == "cloudflare-analytics"
        assert call["run_id"] == 12345
        # detail must include the user-supplied dict + plugin_id injected
        assert call["detail"] == {"zone": "example.com", "plugin_id": "cloudflare-analytics"}
    finally:
        _restore_root_handlers(saved)


def test_log_event_run_id_optional(monkeypatch):
    """If NOUSVIZ_JOB_RUN_ID is unset, run_id is passed as None."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "some-plugin")
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)
    _reset_handler_cache()
    saved = _drop_handlers()

    captured_args = []

    def _fake_direct_write(db_level, message, detail, plugin_id, run_id):
        captured_args.append({"run_id": run_id, "plugin_id": plugin_id})

    try:
        with patch("nousviz_sdk.logging._direct_write_app_logs", side_effect=_fake_direct_write):
            from nousviz_sdk.logging import log_event
            log_event("info", "no run id available")

        assert captured_args[0]["run_id"] is None
        assert captured_args[0]["plugin_id"] == "some-plugin"
    finally:
        _restore_root_handlers(saved)


def test_log_event_run_id_invalid_falls_back_to_none(monkeypatch):
    """If NOUSVIZ_JOB_RUN_ID is set but not numeric, run_id is None."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "some-plugin")
    monkeypatch.setenv("NOUSVIZ_JOB_RUN_ID", "not-a-number")
    _reset_handler_cache()
    saved = _drop_handlers()

    captured_args = []

    def _fake_direct_write(db_level, message, detail, plugin_id, run_id):
        captured_args.append({"run_id": run_id})

    try:
        with patch("nousviz_sdk.logging._direct_write_app_logs", side_effect=_fake_direct_write):
            from nousviz_sdk.logging import log_event
            log_event("info", "bad run id")

        assert captured_args[0]["run_id"] is None
    finally:
        _restore_root_handlers(saved)


# ── DB error fallback: log_event must not raise ────────────────────────

def test_log_event_db_error_falls_through_to_stderr(monkeypatch, capsys):
    """If the direct-write path raises, log_event catches it and writes
    to stderr instead of raising."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "broken-plugin")
    _reset_handler_cache()
    saved = _drop_handlers()

    def _fake_direct_write_raises(*args, **kwargs):
        raise RuntimeError("simulated DB error")

    try:
        with patch("nousviz_sdk.logging._direct_write_app_logs", side_effect=_fake_direct_write_raises):
            from nousviz_sdk.logging import log_event
            # Must not raise.
            log_event("error", "this should fall through")

        captured = capsys.readouterr()
        assert "this should fall through" in captured.err
        assert "db write failed" in captured.err
    finally:
        _restore_root_handlers(saved)


# ── Cache behavior ──────────────────────────────────────────────────────

def test_handler_attached_cache_memoizes(monkeypatch):
    """The handler-attached check should run once per process; subsequent
    log_event calls don't re-walk the logger chain. Negative case only."""
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "cache-test")
    _reset_handler_cache()
    saved = _drop_handlers()

    try:
        with patch("nousviz_sdk.logging._direct_write_app_logs"):
            from nousviz_sdk.logging import log_event
            # First call populates the cache (no handler → False).
            log_event("info", "first")
            import nousviz_sdk.logging as mod
            assert mod._handler_attached_cache is False  # noqa: SLF001
            # Second call still uses cache.
            log_event("info", "second")
            assert mod._handler_attached_cache is False  # noqa: SLF001
    finally:
        _restore_root_handlers(saved)
