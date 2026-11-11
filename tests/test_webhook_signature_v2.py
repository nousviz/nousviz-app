"""B346 — replay-protected (timestamped) outbound webhook signatures.

Outbound webhooks carry three headers when a secret is set:

  X-Webhook-Signature    = hex(HMAC-SHA256(secret, body))            V1, unchanged
  X-Webhook-Timestamp    = unix epoch seconds (string)
  X-Webhook-Signature-V2 = hex(HMAC-SHA256(secret, f"{ts}." + body))

V1 is pinned to a literal digest, so existing consumers that verify the
body-only signature keep working byte-for-byte.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import urllib.request
from pathlib import Path

import pytest

from apps.api.src.services import webhook_dispatch
from apps.api.src.services.webhook_dispatch import post_webhook, sign_headers

_SECRET = "whsec-test-key"
_BODY = b'{"alert_name":"FTD drop","value":42}'
_TS = 1700000000

# Literal digests: if either changes, consumers break.
_V1_PINNED = "324b4ec74cee39ab1ce276325988210c8afa67b8bc1e7d1165e5dc415b1edb28"
_V2_PINNED = "0336fc93685155f4cff347c623cfd27d28296ee2a0b69c55502602fc68338979"


def test_sign_headers_emits_all_three():
    h = sign_headers(_SECRET, _BODY, timestamp=_TS)
    assert set(h) == {
        "X-Webhook-Signature",
        "X-Webhook-Timestamp",
        "X-Webhook-Signature-V2",
    }
    assert h["X-Webhook-Timestamp"] == "1700000000"


def test_v1_is_byte_for_byte_unchanged():
    h = sign_headers(_SECRET, _BODY, timestamp=_TS)
    assert h["X-Webhook-Signature"] == _V1_PINNED
    assert h["X-Webhook-Signature"] == hmac.new(
        _SECRET.encode(), _BODY, hashlib.sha256
    ).hexdigest()


def test_v2_signs_timestamp_dot_body():
    h = sign_headers(_SECRET, _BODY, timestamp=_TS)
    expected = hmac.new(
        _SECRET.encode(), f"{_TS}.".encode() + _BODY, hashlib.sha256
    ).hexdigest()
    assert h["X-Webhook-Signature-V2"] == expected == _V2_PINNED
    assert re.fullmatch(r"[0-9a-f]{64}", h["X-Webhook-Signature-V2"])


def test_v2_changes_with_timestamp_v1_does_not():
    a = sign_headers(_SECRET, _BODY, timestamp=_TS)
    b = sign_headers(_SECRET, _BODY, timestamp=_TS + 1)
    assert a["X-Webhook-Signature"] == b["X-Webhook-Signature"]
    assert a["X-Webhook-Signature-V2"] != b["X-Webhook-Signature-V2"]


def test_default_timestamp_is_current_epoch_seconds(monkeypatch):
    monkeypatch.setattr(webhook_dispatch.time, "time", lambda: 1700000000.987)
    h = sign_headers(_SECRET, _BODY)
    assert h["X-Webhook-Timestamp"] == "1700000000"
    assert h["X-Webhook-Signature-V2"] == _V2_PINNED


@pytest.mark.parametrize("secret", [None, ""])
def test_no_secret_no_headers(secret):
    assert sign_headers(secret, _BODY, timestamp=_TS) == {}


def _capture(monkeypatch):
    captured: dict = {}

    class _Resp:
        status = 200

        def read(self):
            return b""

    def fake_urlopen(req, timeout=None):
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["data"] = req.data
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def test_post_webhook_sends_signed_headers(monkeypatch):
    monkeypatch.setattr(webhook_dispatch.time, "time", lambda: _TS)
    cap = _capture(monkeypatch)
    post_webhook("http://x/y", _SECRET, _BODY)
    assert cap["data"] == _BODY
    assert cap["headers"]["x-webhook-signature"] == _V1_PINNED
    assert cap["headers"]["x-webhook-timestamp"] == str(_TS)
    assert cap["headers"]["x-webhook-signature-v2"] == _V2_PINNED


@pytest.mark.parametrize("secret", [None, ""])
def test_post_webhook_unsigned_without_secret(monkeypatch, secret):
    cap = _capture(monkeypatch)
    post_webhook("http://x/y", secret, _BODY)
    assert not [k for k in cap["headers"] if k.startswith("x-webhook-")]


def test_worker_alert_webhook_uses_shared_signer(monkeypatch):
    run_alerts = pytest.importorskip("apps.worker.src.run_alerts")
    monkeypatch.setattr(webhook_dispatch.time, "time", lambda: _TS)
    cap = _capture(monkeypatch)
    run_alerts._post_webhook("http://x/y", _BODY, _SECRET)
    assert cap["headers"]["x-webhook-signature"] == _V1_PINNED
    assert cap["headers"]["x-webhook-timestamp"] == str(_TS)
    assert cap["headers"]["x-webhook-signature-v2"] == _V2_PINNED

    cap.clear()
    run_alerts._post_webhook("http://x/y", _BODY, None)
    assert not [k for k in cap["headers"] if k.startswith("x-webhook-")]


def test_no_outbound_signer_outside_shared_helper():
    """Every outbound signer must go through `sign_headers`. Only the
    helper itself may set X-Webhook-Signature headers; the webhooks
    plugin's inbound verifier only reads them. `plugins/installed/` is a
    gitignored runtime copy and is skipped."""
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in list((root / "apps").rglob("*.py")) + list((root / "plugins").rglob("*.py")):
        if path.is_relative_to(root / "plugins" / "installed"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"""\[\s*["']X-Webhook-Signature""", text):
            if path.name != "webhook_dispatch.py":
                offenders.append(str(path.relative_to(root)))
    assert offenders == []
