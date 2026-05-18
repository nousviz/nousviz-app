"""
B284 (v0.9.11.23) — shared HMAC-signed POST helper for outbound webhooks.
B283 (v0.9.11.24) — adds `format_for_channel` so typed channels
(currently Slack) render their per-channel body shape (Block Kit) while
generic webhooks continue to receive byte-identical payloads.

Extracted from `diagnostic_alerts.py` so both bridges (B274 system-
level findings + B284 per-run failures) share a single implementation
of the POST contract. Channel-type-specific rendering happens BEFORE
the POST so HMAC signing always sees the actual transmitted body.

Contract:
  - POST <url> with Content-Type: application/json
  - X-Webhook-Signature: hex(sha256(secret, body)) when secret present
  - 10s timeout
  - Returns nothing on success; raises on failure (caller wraps with
    per-target try/except for isolation)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("nousviz.services.webhook_dispatch")


WEBHOOK_TIMEOUT_SECONDS = 10


def format_for_channel(
    payload: dict,
    channel_type: Optional[str],
    channel_config: Optional[dict] = None,
) -> bytes:
    """Render `payload` to the bytes that get POSTed to the webhook.

    `channel_type='generic'` (or any unknown / None value) returns
    `json.dumps(payload).encode()` byte-identical to the pre-B283
    helper — pinned in `tests/test_webhook_dispatch.py` so the
    typed-channel refactor cannot silently regress generic receivers.

    `channel_type='slack'` delegates to `slack_formatter.format` which
    produces a Block Kit body with severity color bar, structured
    fields, code-formatted error excerpt, suggested-fix section, and a
    "View in NousViz" action button. Mention prefix and channel
    override come from `channel_config`.

    Discord / Teams stay generic in B283; their typed formatters land
    in follow-up tickets using the same dispatch shape.
    """
    if channel_type == "slack":
        from .slack_formatter import format as slack_format
        body = slack_format(payload, channel_config or {})
        return json.dumps(body).encode()
    # Generic / discord / teams / unknown → today's flat payload.
    return json.dumps(payload).encode()


def post_webhook(url: str, secret: Optional[str], body: bytes) -> None:
    """HMAC-signed POST. Raises on transport / HTTP error; caller
    handles per-target failure isolation.
    """
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = sig
    req = urllib.request.Request(url, data=body, headers=headers)
    urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT_SECONDS)
