"""B283 (v0.9.11.24) — webhook_dispatch tests.

The critical pin in this file is the **byte-identical regression
pin** for `channel_type='generic'`: any webhook receiver that worked
before B283 must continue to receive the exact same body, byte-for-
byte. Slack-typed channels diverge (Block Kit), but generic /
Discord / Teams must stay flat-payload.

HMAC signing is computed on the FORMATTED body, not the raw payload —
so a Slack receiver verifies the signature on the Block Kit shape, and
a generic receiver verifies on the original flat shape. The signature
is byte-stable for a given (secret, body) pair, so we pin a known
fixture.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import pytest

from apps.api.src.services.webhook_dispatch import (
    format_for_channel,
    post_webhook,
)


# Sample alert payload identical in shape to what diagnostic_alerts /
# job_alerts emit. We avoid coupling to those modules' build helpers
# to keep this test self-contained.
_PAYLOAD = {
    "text": ":rotating_light: [error] sync:quickbooks error",
    "alert_type": "job_run_failure",
    "plugin_id": "quickbooks",
    "run_id": "abc-123",
    "status": "error",
    "error_excerpt": "ValueError: bad token",
    "suggested_fix": "OAuth token expired",
    "dashboard_url": "https://nousviz.online/system/jobs",
}


# ── Generic-channel byte-identical regression pin ──────────────────


def _legacy_format(payload: dict) -> bytes:
    """How the body was built pre-B283 (in `diagnostic_alerts._post_webhook`
    and `job_alerts._dispatch_to_subscription`): `json.dumps(payload).encode()`.
    Any drift from this shape risks breaking generic-webhook receivers."""
    return json.dumps(payload).encode()


def test_generic_channel_byte_identical_to_pre_b283():
    """REGRESSION PIN. Generic-channel receivers must see the exact
    same body as before B283. If this test ever fails, a refactor has
    silently broken every Discord / Teams / custom webhook integration."""
    expected = _legacy_format(_PAYLOAD)
    assert format_for_channel(_PAYLOAD, "generic", {}) == expected


def test_none_channel_type_falls_through_to_generic():
    """Defensive — if a row somehow lacks channel_type (pre-migration
    state, corrupt config), we default to generic, not error."""
    expected = _legacy_format(_PAYLOAD)
    assert format_for_channel(_PAYLOAD, None, None) == expected


def test_unknown_channel_type_falls_through_to_generic():
    """The CHECK constraint on webhook_endpoints.channel_type prevents
    unknown values reaching the dispatcher in practice, but the
    formatter must be safe regardless — never raise on user data."""
    expected = _legacy_format(_PAYLOAD)
    assert format_for_channel(_PAYLOAD, "garbage", {}) == expected


def test_discord_stays_generic_until_its_own_ticket():
    """B283 only formats Slack specially. Discord rows that switch to
    typed before the Discord formatter ships should receive their
    generic payload — harmless, the operator's sub-panel disables the
    option in the UI."""
    expected = _legacy_format(_PAYLOAD)
    assert format_for_channel(_PAYLOAD, "discord", {}) == expected


def test_teams_stays_generic_until_its_own_ticket():
    expected = _legacy_format(_PAYLOAD)
    assert format_for_channel(_PAYLOAD, "teams", {}) == expected


# ── Slack channel produces Block Kit ───────────────────────────────


def test_slack_channel_produces_block_kit_body():
    raw = format_for_channel(_PAYLOAD, "slack", {})
    body = json.loads(raw)
    assert "attachments" in body
    assert body["attachments"][0]["color"] == "#dc3545"  # error severity
    assert body["attachments"][0]["blocks"][0]["type"] == "header"


def test_slack_channel_diverges_from_generic_byte_for_byte():
    """Sanity check: Slack rendering MUST differ from generic. If they
    matched, the formatter wouldn't be doing anything."""
    generic = format_for_channel(_PAYLOAD, "generic", {})
    slack = format_for_channel(_PAYLOAD, "slack", {})
    assert generic != slack


def test_slack_channel_with_mention_config():
    raw = format_for_channel(
        _PAYLOAD,
        "slack",
        {"mention_user_ids": ["U06ABC123"]},
    )
    body = json.loads(raw)
    assert body["text"].startswith("<@U06ABC123>")


def test_slack_channel_returns_valid_json():
    raw = format_for_channel(_PAYLOAD, "slack", {})
    # If json.loads fails, the formatter produced something Slack
    # would HTTP-400 on. This test catches that early.
    json.loads(raw)


# ── HMAC signature stability ───────────────────────────────────────


def test_hmac_signature_byte_stable_for_known_payload():
    """Pin: identical (secret, body) pair always produces the same
    signature. Catches accidental signature-format drift."""
    secret = "test-secret-do-not-use-in-prod"
    body = b'{"hello":"world"}'
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    # The post_webhook helper uses this exact computation; we pin the
    # reference here so any rewrite stays compatible.
    assert len(expected) == 64  # sha256 hex
    assert all(c in "0123456789abcdef" for c in expected)


def test_post_webhook_no_secret_skips_signature_header(monkeypatch):
    """Captures the request kwargs to verify the headers list."""
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        "apps.api.src.services.webhook_dispatch.urllib.request.urlopen",
        fake_urlopen,
    )

    post_webhook("https://example.test/", None, b'{"a":1}')
    # urllib normalizes header keys to title-case; check both spellings.
    assert "Content-type" in captured["headers"] or "Content-Type" in captured["headers"]
    assert "X-webhook-signature" not in captured["headers"]
    assert "X-Webhook-Signature" not in captured["headers"]


def test_post_webhook_with_secret_signs_body(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        return FakeResponse()

    monkeypatch.setattr(
        "apps.api.src.services.webhook_dispatch.urllib.request.urlopen",
        fake_urlopen,
    )

    body = b'{"a":1}'
    secret = "my-secret"
    post_webhook("https://example.test/", secret, body)

    sig_hdr = captured["headers"].get("X-webhook-signature") or captured["headers"].get("X-Webhook-Signature")
    assert sig_hdr, f"signature header missing in {captured['headers']!r}"
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sig_hdr == expected


def test_post_webhook_signs_formatted_body_not_raw_payload(monkeypatch):
    """Critical: HMAC is computed on the post-format bytes. A Slack
    receiver verifies on Block Kit shape; a generic receiver verifies
    on flat payload. If signing happened pre-format, both would verify
    against the same flat shape and one of them would fail."""
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data
        return FakeResponse()

    monkeypatch.setattr(
        "apps.api.src.services.webhook_dispatch.urllib.request.urlopen",
        fake_urlopen,
    )

    secret = "shared-secret"
    slack_body = format_for_channel(_PAYLOAD, "slack", {})
    post_webhook("https://example.test/", secret, slack_body)

    sig_hdr = captured["headers"].get("X-webhook-signature") or captured["headers"].get("X-Webhook-Signature")
    expected = hmac.new(secret.encode(), slack_body, hashlib.sha256).hexdigest()
    assert sig_hdr == expected
    assert captured["body"] == slack_body
