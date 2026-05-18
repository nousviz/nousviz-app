"""
B283 (v0.9.11.24) — Slack Block Kit formatter.

Renders an alert payload (B274 diagnostic finding OR B284 job-run
failure) into a Slack incoming-webhook body with severity color bar,
structured fields, code-formatted error excerpt, suggested-fix
section, and an action button.

Generic-webhook receivers continue to receive today's flat
`{text + structured fields}` shape — that path is unchanged. This
module is only invoked when `webhook_endpoints.channel_type='slack'`.

Notes:
- Block Kit blocks have a 3000-char limit on `text` fields. We
  truncate the error excerpt at 1500 chars from the END (preserving
  the actual exception class — same logic as v0.9.11.22.4
  `RIGHT(error, 4000)` for `/system/jobs`).
- The top-level `text` field is preserved as a notification fallback
  (Slack uses it for desktop banners, screen readers, plain-text
  clients).
- No Slack SDK dependency — Block Kit is a stable JSON shape.
"""

from __future__ import annotations

import re
from typing import Optional


# Severity → Slack attachment color.
_SEVERITY_COLORS = {
    "critical": "#dc3545",
    "error":    "#dc3545",
    "warning":  "#ffc107",
    "timeout":  "#ffc107",
    "cancelled":"#6c757d",
    "info":     "#198754",
}

_SEVERITY_EMOJI = {
    "critical": ":rotating_light:",
    "error":    ":rotating_light:",
    "warning":  ":warning:",
    "timeout":  ":hourglass:",
    "cancelled":":no_entry_sign:",
    "info":     ":information_source:",
}

_DEFAULT_MENTION_SEVERITIES = ["critical", "error"]

# Slack member ID format: starts with U, then uppercase alphanumerics.
# (Yes, Slack also has W-prefixed enterprise IDs, but the public
# Slack API normalizes to U for mentions in incoming webhooks.)
_MEMBER_ID_RE = re.compile(r"^U[A-Z0-9]{2,}$")

# Channel override format: leading # for channel, leading @ for DM.
_CHANNEL_OVERRIDE_RE = re.compile(r"^[#@][A-Za-z0-9_\-\.]{1,80}$")

# Per-block text limit (Slack Block Kit hard limit is 3000; staying at
# 1500 leaves headroom for the surrounding code-block fences and
# section structure).
_ERROR_EXCERPT_LIMIT = 1500


def validate_mention_user_id(value: str) -> str:
    """Reject anything that isn't a Slack member ID. Empty/whitespace
    raises — the editor should never submit those."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("mention_user_id must be a non-empty string")
    v = value.strip()
    if not _MEMBER_ID_RE.match(v):
        raise ValueError(
            f"Invalid Slack member ID: {v!r}. Expected format like 'U06ABC123' "
            f"(starts with U, then uppercase letters/digits)."
        )
    return v


def validate_channel_override(value: Optional[str]) -> Optional[str]:
    """None / empty / whitespace → None. Otherwise must match #channel
    or @user."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("channel_override must be a string or None")
    v = value.strip()
    if not v:
        return None
    if not _CHANNEL_OVERRIDE_RE.match(v):
        raise ValueError(
            f"Invalid channel override: {v!r}. Expected '#channel' or '@user'."
        )
    return v


def _severity_for_payload(payload: dict) -> str:
    """Pick a severity bucket. B274 carries explicit `severity`; B284
    uses `status` (error/timeout/cancelled). Default to 'error' if
    neither is present so we color-bar consistently."""
    sev = payload.get("severity")
    if sev in _SEVERITY_COLORS:
        return sev
    status = payload.get("status")
    if status in _SEVERITY_COLORS:
        return status
    # B274 alert_type=='diagnostic_resolved' carries severity='info' in
    # practice; preserve that. Fall back to 'error' for unknown shapes.
    return "error"


def _truncate_error_excerpt(text: Optional[str]) -> Optional[str]:
    """Last N chars — exception class lives at the end of a Python
    traceback (see v0.9.11.22.4)."""
    if not text:
        return None
    if len(text) <= _ERROR_EXCERPT_LIMIT:
        return text
    return text[-_ERROR_EXCERPT_LIMIT:]


def _build_mention_prefix(
    severity: str,
    channel_config: dict,
) -> str:
    """`<@Uxxx> <@Uyyy>` if mention IDs are configured AND the alert
    severity is in the trigger list; empty string otherwise."""
    mention_ids = channel_config.get("mention_user_ids") or []
    trigger_severities = (
        channel_config.get("mention_on_severities")
        or _DEFAULT_MENTION_SEVERITIES
    )
    if not mention_ids or severity not in trigger_severities:
        return ""
    # Defensive re-validate at render time so a corrupt config can't
    # leak `<@oncall>` literals into Slack.
    parts = []
    for uid in mention_ids:
        try:
            parts.append(f"<@{validate_mention_user_id(uid)}>")
        except ValueError:
            continue
    return " ".join(parts) + " " if parts else ""


def _build_header_text(payload: dict, severity: str) -> str:
    """Header line: `:emoji: [STATUS] alert_type plugin_label`."""
    emoji = _SEVERITY_EMOJI.get(severity, ":warning:")
    alert_type = payload.get("alert_type") or "alert"
    if alert_type == "job_run_failure":
        plugin_id = payload.get("plugin_id") or "?"
        status = payload.get("status") or "?"
        return f"{emoji} [{status.upper()}] sync:{plugin_id}"
    if alert_type in ("diagnostic_critical", "diagnostic_warning", "diagnostic_resolved"):
        title = payload.get("title") or alert_type
        return f"{emoji} [{severity.upper()}] {title}"
    return f"{emoji} [{severity.upper()}] {alert_type}"


def _build_fields_block(payload: dict) -> Optional[dict]:
    """Two-column field grid. None of the values are required — we
    skip empty rows so a sparse payload renders cleanly."""
    fields: list[dict] = []

    def add(label: str, value: object) -> None:
        if value is None or value == "":
            return
        fields.append({
            "type": "mrkdwn",
            "text": f"*{label}:*\n{value}",
        })

    if payload.get("alert_type") == "job_run_failure":
        add("Plugin", payload.get("plugin_id"))
        add("Status", payload.get("status"))
        add("Run ID", payload.get("run_id"))
        add("Started", payload.get("started_at"))
    else:
        add("Severity", payload.get("severity"))
        add("Affected", payload.get("affected_key"))
        add("Finding", payload.get("finding_id"))
        add("Detected", payload.get("first_detected_at") or payload.get("fired_at"))

    if not fields:
        return None
    return {
        "type": "section",
        "fields": fields[:10],  # Slack Block Kit field limit
    }


def _build_error_block(payload: dict) -> Optional[dict]:
    """Code-fenced error excerpt, truncated to last 1500 chars."""
    excerpt = _truncate_error_excerpt(payload.get("error_excerpt"))
    if not excerpt:
        return None
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Error:*\n```{excerpt}```",
        },
    }


def _build_suggested_fix_block(payload: dict) -> Optional[dict]:
    fix = payload.get("suggested_fix")
    if not fix:
        return None
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Suggested fix:* {fix}",
        },
    }


def _build_actions_block(payload: dict) -> Optional[dict]:
    """Single 'View in NousViz' button → dashboard_url."""
    url = payload.get("dashboard_url") or payload.get("logs_url")
    if not url:
        return None
    return {
        "type": "actions",
        "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "View in NousViz"},
            "url": url,
            "style": "primary" if payload.get("severity") in ("critical", "error") else None,
        }],
    }


def _strip_none(d: dict) -> dict:
    """Slack rejects null `style`. Drop None values from action buttons."""
    return {k: v for k, v in d.items() if v is not None}


def format(payload: dict, channel_config: Optional[dict] = None) -> dict:
    """Render `payload` as a Slack incoming-webhook body.

    Args:
      payload: the flat alert dict produced by
        `diagnostic_alerts._build_payload` or `job_alerts._build_payload`.
      channel_config: per-webhook config from
        `webhook_endpoints.channel_config` JSONB. Keys:
        - mention_user_ids: list[str] (optional)
        - mention_on_severities: list[str] (optional, default: critical+error)
        - channel_override: str (optional)

    Returns a dict ready for `json.dumps()` and POST to the Slack
    webhook URL.
    """
    cfg = channel_config or {}
    severity = _severity_for_payload(payload)
    mention_prefix = _build_mention_prefix(severity, cfg)

    # Top-level text fallback (notification banner, plain-text clients,
    # screen readers). Reuse the payload's own `text` if present, else
    # synthesize from header.
    flat_text = payload.get("text") or _build_header_text(payload, severity)
    text_with_mentions = (mention_prefix + flat_text).strip()

    # Build blocks. Header is plain_text (Slack constraint). Subsequent
    # sections are mrkdwn.
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": _build_header_text(payload, severity),
                "emoji": True,
            },
        },
    ]
    # Mention prefix lives inside a context block above the fields so
    # it's visually distinct from the header but still triggers the
    # ping.
    if mention_prefix:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": mention_prefix.strip()},
        })

    fields = _build_fields_block(payload)
    if fields:
        blocks.append(fields)

    err = _build_error_block(payload)
    if err:
        blocks.append(err)

    fix = _build_suggested_fix_block(payload)
    if fix:
        blocks.append(fix)

    actions = _build_actions_block(payload)
    if actions:
        actions["elements"] = [_strip_none(e) for e in actions["elements"]]
        blocks.append(actions)

    body: dict = {
        "text": text_with_mentions,
        "attachments": [{
            "color": _SEVERITY_COLORS.get(severity, "#6c757d"),
            "blocks": blocks,
        }],
    }

    channel_override = validate_channel_override(cfg.get("channel_override"))
    if channel_override:
        body["channel"] = channel_override

    return body
