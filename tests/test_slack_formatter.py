"""B283 (v0.9.11.24) — Slack Block Kit formatter tests.

Pins the Slack-shaped body so the formatter can't silently drift away
from what the operator's Slack workspace renders. Every assertion is
on a stable Block Kit shape (block types, mrkdwn vs plain_text, top-
level fields, attachment color, action button URL).
"""

from __future__ import annotations

import json
import pytest

from apps.api.src.services.slack_formatter import (
    format,
    validate_mention_user_id,
    validate_channel_override,
    _SEVERITY_COLORS,
)


# ── Sample payloads (minimal, but realistic) ────────────────────────


def _job_run_payload(**overrides) -> dict:
    base = {
        "text": ":rotating_light: [error] sync:quickbooks error (run abc-123) — Suggested: Re-authorize · /system/logs?run_id=abc-123",
        "alert_type": "job_run_failure",
        "plugin_id": "quickbooks",
        "job_id": "sync:quickbooks",
        "run_id": "abc-123",
        "status": "error",
        "error_excerpt": "Traceback (most recent call last):\n  File 'sync.py', line 99\nValueError: bad token",
        "suggested_fix": "OAuth token expired or revoked. Re-authorize the plugin.",
        "duration_ms": 1234,
        "started_at": "2026-05-05T12:00:00+00:00",
        "fired_at":   "2026-05-05T12:00:01+00:00",
        "dashboard_url": "https://nousviz.online/system/jobs",
        "logs_url":      "https://nousviz.online/system/logs?run_id=abc-123",
    }
    base.update(overrides)
    return base


def _diagnostic_payload(**overrides) -> dict:
    base = {
        "text": ":rotating_light: DETECTED · 4 syncs are consistently failing · /system/health",
        "alert_type": "diagnostic_critical",
        "severity": "critical",
        "title": "Multiple syncs consistently failing",
        "finding_id": "syncs_consistently_failing",
        "affected_key": "global",
        "first_detected_at": "2026-05-05T11:50:00+00:00",
        "fired_at":          "2026-05-05T12:00:00+00:00",
        "dashboard_url": "https://nousviz.online/system/health",
    }
    base.update(overrides)
    return base


# ── Block Kit shape pins ────────────────────────────────────────────


def test_format_returns_top_level_text_and_attachments():
    body = format(_job_run_payload())
    assert "text" in body
    assert isinstance(body["text"], str) and body["text"]
    assert "attachments" in body
    assert isinstance(body["attachments"], list) and len(body["attachments"]) == 1


def test_attachment_carries_severity_color_for_error():
    body = format(_job_run_payload(status="error"))
    assert body["attachments"][0]["color"] == _SEVERITY_COLORS["error"]


def test_attachment_color_for_timeout_status():
    body = format(_job_run_payload(status="timeout"))
    assert body["attachments"][0]["color"] == _SEVERITY_COLORS["timeout"]


def test_attachment_color_for_cancelled_status():
    body = format(_job_run_payload(status="cancelled"))
    assert body["attachments"][0]["color"] == _SEVERITY_COLORS["cancelled"]


def test_diagnostic_critical_gets_critical_color():
    body = format(_diagnostic_payload(severity="critical"))
    assert body["attachments"][0]["color"] == _SEVERITY_COLORS["critical"]


def test_blocks_have_header_first():
    body = format(_job_run_payload())
    blocks = body["attachments"][0]["blocks"]
    assert blocks[0]["type"] == "header"
    assert blocks[0]["text"]["type"] == "plain_text"


def test_header_includes_status_for_job_run():
    body = format(_job_run_payload(status="timeout"))
    header_text = body["attachments"][0]["blocks"][0]["text"]["text"]
    assert "TIMEOUT" in header_text
    assert "sync:quickbooks" in header_text


def test_header_includes_severity_for_diagnostic():
    body = format(_diagnostic_payload(severity="critical", title="Disk full"))
    header_text = body["attachments"][0]["blocks"][0]["text"]["text"]
    assert "CRITICAL" in header_text
    assert "Disk full" in header_text


def test_fields_block_has_two_column_grid():
    body = format(_job_run_payload())
    blocks = body["attachments"][0]["blocks"]
    field_blocks = [b for b in blocks if b.get("type") == "section" and "fields" in b]
    assert len(field_blocks) == 1
    fields = field_blocks[0]["fields"]
    assert all(f["type"] == "mrkdwn" for f in fields)
    # Plugin / Status / Run ID / Started — all four expected for job_run
    field_text = " ".join(f["text"] for f in fields)
    assert "Plugin" in field_text
    assert "Status" in field_text
    assert "Run ID" in field_text


def test_error_excerpt_in_code_block():
    body = format(_job_run_payload())
    blocks = body["attachments"][0]["blocks"]
    err_blocks = [b for b in blocks if b.get("type") == "section" and "Error" in b.get("text", {}).get("text", "")]
    assert len(err_blocks) == 1
    assert "```" in err_blocks[0]["text"]["text"]
    assert "ValueError" in err_blocks[0]["text"]["text"]


def test_suggested_fix_section_present():
    body = format(_job_run_payload())
    blocks = body["attachments"][0]["blocks"]
    fix_blocks = [b for b in blocks if b.get("type") == "section" and "Suggested fix" in b.get("text", {}).get("text", "")]
    assert len(fix_blocks) == 1
    assert "OAuth token" in fix_blocks[0]["text"]["text"]


def test_action_button_links_to_dashboard():
    body = format(_job_run_payload())
    blocks = body["attachments"][0]["blocks"]
    actions = [b for b in blocks if b.get("type") == "actions"]
    assert len(actions) == 1
    elements = actions[0]["elements"]
    assert len(elements) == 1
    btn = elements[0]
    assert btn["type"] == "button"
    assert btn["url"] == "https://nousviz.online/system/jobs"
    assert btn["text"]["text"] == "View in NousViz"


def test_action_button_style_primary_for_critical():
    body = format(_diagnostic_payload(severity="critical"))
    blocks = body["attachments"][0]["blocks"]
    actions = [b for b in blocks if b.get("type") == "actions"][0]
    btn = actions["elements"][0]
    assert btn.get("style") == "primary"


def test_action_button_no_style_key_for_info():
    """Slack rejects `style: null` — defensive: when severity isn't
    error/critical, the style key should be absent entirely."""
    body = format(_diagnostic_payload(severity="info", title="resolved"))
    blocks = body["attachments"][0]["blocks"]
    actions = [b for b in blocks if b.get("type") == "actions"][0]
    btn = actions["elements"][0]
    assert "style" not in btn


def test_no_action_block_when_no_url():
    body = format(_job_run_payload(dashboard_url=None, logs_url=None))
    blocks = body["attachments"][0]["blocks"]
    actions = [b for b in blocks if b.get("type") == "actions"]
    assert len(actions) == 0


def test_no_error_block_when_excerpt_missing():
    body = format(_job_run_payload(error_excerpt=None))
    blocks = body["attachments"][0]["blocks"]
    err_blocks = [b for b in blocks if b.get("type") == "section" and "Error" in b.get("text", {}).get("text", "")]
    assert len(err_blocks) == 0


# ── Truncation pin (preserves exception class) ──────────────────────


def test_error_excerpt_truncates_at_1500_from_end():
    """Same logic as v0.9.11.22.4 RIGHT(error, 4000) — the actual
    exception is at the END of a Python traceback, not the start."""
    long_traceback = ("Frame line\n" * 1000) + "ValueError: actual exception at end"
    payload = _job_run_payload(error_excerpt=long_traceback)
    body = format(payload)
    err_block = next(
        b for b in body["attachments"][0]["blocks"]
        if b.get("type") == "section" and "Error" in b.get("text", {}).get("text", "")
    )
    rendered = err_block["text"]["text"]
    assert "ValueError: actual exception at end" in rendered, (
        "Truncation must preserve the exception line at the end"
    )
    # Truncated content should be ≤ 1500 chars (plus the `*Error:*\n```...```` wrapper).
    # Strip the wrapper and check.
    body_text = rendered.replace("*Error:*\n", "").replace("```", "")
    assert len(body_text) <= 1500


# ── Mention rendering ───────────────────────────────────────────────


def test_no_mention_prefix_when_mention_ids_empty():
    body = format(_job_run_payload(), channel_config={})
    assert "<@U" not in body["text"]


def test_no_mention_prefix_when_severity_not_in_trigger_list():
    """info-severity alert with critical+error trigger list → no @-mention."""
    body = format(
        _diagnostic_payload(severity="info"),
        channel_config={"mention_user_ids": ["U06ABC123"]},
    )
    assert "<@U06ABC123>" not in body["text"]


def test_mention_prefix_added_when_severity_matches():
    body = format(
        _job_run_payload(),  # status=error → matches default critical+error
        channel_config={"mention_user_ids": ["U06ABC123", "U07XYZ789"]},
    )
    assert body["text"].startswith("<@U06ABC123> <@U07XYZ789>")


def test_mention_section_block_added_for_paged_alerts():
    body = format(
        _job_run_payload(),
        channel_config={"mention_user_ids": ["U06ABC123"]},
    )
    blocks = body["attachments"][0]["blocks"]
    # First block is header; second should be the mention section
    assert blocks[1]["type"] == "section"
    assert "<@U06ABC123>" in blocks[1]["text"]["text"]


def test_mention_severities_override_defaults():
    """Operator can configure mention_on_severities=['warning'] only;
    a warning then pages, but error doesn't."""
    body_warning = format(
        _diagnostic_payload(severity="warning"),
        channel_config={
            "mention_user_ids": ["U06ABC123"],
            "mention_on_severities": ["warning"],
        },
    )
    assert "<@U06ABC123>" in body_warning["text"]

    body_error = format(
        _job_run_payload(status="error"),
        channel_config={
            "mention_user_ids": ["U06ABC123"],
            "mention_on_severities": ["warning"],
        },
    )
    assert "<@U06ABC123>" not in body_error["text"]


def test_mention_with_corrupt_id_skips_silently():
    """Defensive — config could carry stale data. Bad IDs are dropped
    at render time, not echoed to Slack as literals."""
    body = format(
        _job_run_payload(),
        channel_config={"mention_user_ids": ["oncall", "U06ABC123", "<@U07>"]},
    )
    # Only U06ABC123 should land
    assert "<@U06ABC123>" in body["text"]
    assert "<@oncall>" not in body["text"]
    assert "oncall" not in body["text"]


# ── Channel override ────────────────────────────────────────────────


def test_channel_override_added_to_body():
    body = format(
        _job_run_payload(),
        channel_config={"channel_override": "#data-eng"},
    )
    assert body.get("channel") == "#data-eng"


def test_no_channel_field_when_override_absent():
    body = format(_job_run_payload(), channel_config={})
    assert "channel" not in body


def test_no_channel_field_when_override_empty_string():
    body = format(
        _job_run_payload(),
        channel_config={"channel_override": ""},
    )
    assert "channel" not in body


def test_no_channel_field_when_override_whitespace():
    body = format(
        _job_run_payload(),
        channel_config={"channel_override": "   "},
    )
    assert "channel" not in body


def test_invalid_channel_override_raises():
    with pytest.raises(ValueError):
        format(
            _job_run_payload(),
            channel_config={"channel_override": "data-eng"},  # missing # or @
        )


# ── Validators ──────────────────────────────────────────────────────


def test_validate_mention_user_id_accepts_typical():
    assert validate_mention_user_id("U06ABC123") == "U06ABC123"


def test_validate_mention_user_id_strips_whitespace():
    assert validate_mention_user_id("  U06ABC123  ") == "U06ABC123"


@pytest.mark.parametrize("bad", [
    "",
    "   ",
    "oncall",          # no U prefix
    "u06abc123",       # lowercase
    "@U06ABC123",      # leading @
    "<@U06ABC123>",    # already wrapped
    "U",               # too short
])
def test_validate_mention_user_id_rejects_garbage(bad):
    with pytest.raises(ValueError):
        validate_mention_user_id(bad)


def test_validate_channel_override_none():
    assert validate_channel_override(None) is None


def test_validate_channel_override_empty_returns_none():
    assert validate_channel_override("") is None
    assert validate_channel_override("   ") is None


@pytest.mark.parametrize("ok", [
    "#data-eng",
    "#alerts",
    "@bob",
    "#alerts.prod",
])
def test_validate_channel_override_accepts(ok):
    assert validate_channel_override(ok) == ok


@pytest.mark.parametrize("bad", [
    "data-eng",       # missing prefix
    "#",              # nothing after prefix
    "#with spaces",
    "#" + "x" * 200,  # too long
])
def test_validate_channel_override_rejects(bad):
    with pytest.raises(ValueError):
        validate_channel_override(bad)


# ── Body is JSON-serializable ───────────────────────────────────────


def test_body_round_trips_through_json_dumps():
    body = format(
        _job_run_payload(),
        channel_config={
            "mention_user_ids": ["U06ABC123"],
            "channel_override": "#alerts",
        },
    )
    raw = json.dumps(body)
    parsed = json.loads(raw)
    assert parsed["text"].startswith("<@U06ABC123>")
    assert parsed["channel"] == "#alerts"
    assert parsed["attachments"][0]["color"] == "#dc3545"


def test_diagnostic_resolved_uses_info_color():
    """B274 emits alert_type='diagnostic_resolved' with severity='info'
    when a previously-detected finding clears. The formatter should
    honor that color even though the title doesn't carry an obvious
    severity word."""
    body = format(
        _diagnostic_payload(
            alert_type="diagnostic_resolved",
            severity="info",
            title="Disk space recovered",
        ),
    )
    assert body["attachments"][0]["color"] == _SEVERITY_COLORS["info"]
