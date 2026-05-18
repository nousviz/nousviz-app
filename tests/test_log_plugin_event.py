"""Tests for log_plugin_event wrapper (B203).

Pins the structured-detail and message-prefix contract so /system/logs
filtering by plugin works consistently.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_log_plugin_event_prefixes_message_and_merges_detail(monkeypatch):
    """The wrapper prefixes message with [plugin_id] action: ... and
    merges plugin_id + action into the structured detail dict."""
    from apps.api.src import log_events

    captured: list[dict] = []

    def fake_log_job_event(level, message, detail=None, source="sync", **kwargs):
        captured.append({"level": level, "message": message, "detail": detail, "source": source})

    monkeypatch.setattr(log_events, "log_job_event", fake_log_job_event)

    log_events.log_plugin_event(
        "error",
        "plausible",
        "update_check",
        "git ls-remote failed (rc=128): Permission denied (publickey).",
        detail={"source_class": "git", "source_url": "git@github.com:nousviz/plugin-plausible.git"},
        source="plugin_update",
    )

    assert len(captured) == 1
    e = captured[0]
    assert e["level"] == "error"
    assert e["source"] == "plugin_update"
    assert e["message"].startswith("[plausible] update_check: ")
    assert "Permission denied" in e["message"]
    # plugin_id and action auto-merged into detail
    assert e["detail"]["plugin_id"] == "plausible"
    assert e["detail"]["action"] == "update_check"
    # original detail keys preserved
    assert e["detail"]["source_class"] == "git"
    assert e["detail"]["source_url"] == "git@github.com:nousviz/plugin-plausible.git"


def test_log_plugin_event_handles_missing_detail(monkeypatch):
    """detail=None should still produce a dict with plugin_id + action."""
    from apps.api.src import log_events

    captured: list[dict] = []
    monkeypatch.setattr(
        log_events,
        "log_job_event",
        lambda level, message, detail=None, source="sync", **kwargs: captured.append(
            {"level": level, "message": message, "detail": detail, "source": source}
        ),
    )

    log_events.log_plugin_event(
        "warning",
        "myplugin",
        "deploy_key_lookup",
        "no key registered",
        source="plugin_install",
    )

    assert captured[0]["detail"] == {"plugin_id": "myplugin", "action": "deploy_key_lookup"}


def test_log_plugin_event_default_source_is_plugin_lifecycle(monkeypatch):
    """Default source tag is plugin_lifecycle."""
    from apps.api.src import log_events

    captured: list[dict] = []
    monkeypatch.setattr(
        log_events,
        "log_job_event",
        lambda level, message, detail=None, source="sync", **kwargs: captured.append({"source": source}),
    )

    log_events.log_plugin_event("info", "x", "y", "z")
    assert captured[0]["source"] == "plugin_lifecycle"
