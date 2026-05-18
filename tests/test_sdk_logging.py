"""B140: SDK structured logging API.

Verifies `nousviz_sdk.logging.log_event` emits records that the
DBLogHandler can ingest, and that the test-harness fallback (no
NOUSVIZ_PLUGIN_ID) writes to stderr without raising.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_log_event_emits_to_plugin_namespace_logger(caplog, monkeypatch):
    """Inside a NousViz subprocess (NOUSVIZ_PLUGIN_ID set), log_event
    routes to logging.getLogger('nousviz.plugin.<id>') with extras."""
    from sdk.nousviz_sdk.logging import log_event

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "test-plugin")

    with caplog.at_level(logging.INFO, logger="nousviz.plugin.test-plugin"):
        log_event("error", "boom", detail={"key": "value"})

    matching = [
        r for r in caplog.records
        if r.name == "nousviz.plugin.test-plugin" and r.message == "boom"
    ]
    assert len(matching) == 1
    record = matching[0]
    assert record.levelno == logging.ERROR
    assert getattr(record, "source_override") == "plugin"
    assert getattr(record, "detail") == {"key": "value", "plugin_id": "test-plugin"}


def test_log_event_levels_map_correctly(caplog, monkeypatch):
    from sdk.nousviz_sdk.logging import log_event

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "lvl-plugin")

    with caplog.at_level(logging.DEBUG, logger="nousviz.plugin.lvl-plugin"):
        log_event("info", "i")
        log_event("warn", "w")
        log_event("error", "e")

    levels_for_messages = {r.message: r.levelno for r in caplog.records}
    assert levels_for_messages.get("i") == logging.INFO
    assert levels_for_messages.get("w") == logging.WARNING
    assert levels_for_messages.get("e") == logging.ERROR


def test_log_event_falls_back_to_stderr_without_plugin_id(capsys, monkeypatch):
    """B138 harness scenario: no NOUSVIZ_PLUGIN_ID — log_event should
    write to stderr and never raise."""
    from sdk.nousviz_sdk.logging import log_event

    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)

    log_event("error", "from-harness", detail={"k": "v"})

    captured = capsys.readouterr()
    assert "from-harness" in captured.err
    assert "ERROR" in captured.err


def test_log_event_detail_defaults_to_plugin_id_only(caplog, monkeypatch):
    """If detail is omitted, the resulting record's detail still carries
    plugin_id so downstream consumers can attribute the entry."""
    from sdk.nousviz_sdk.logging import log_event

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "no-detail-plugin")

    with caplog.at_level(logging.INFO, logger="nousviz.plugin.no-detail-plugin"):
        log_event("info", "ping")

    matching = [
        r for r in caplog.records
        if r.name == "nousviz.plugin.no-detail-plugin"
    ]
    assert len(matching) == 1
    assert getattr(matching[0], "detail") == {"plugin_id": "no-detail-plugin"}


def test_log_event_re_exported_from_top_level():
    """log_event is exposed via `from nousviz_sdk import log_event` for
    plugin-author convenience."""
    from sdk.nousviz_sdk import log_event as top_level
    from sdk.nousviz_sdk.logging import log_event as direct
    assert top_level is direct
