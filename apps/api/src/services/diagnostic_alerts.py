"""
B274 (v0.9.11.20) — diagnostic-finding → webhook bridge.
B283 (v0.9.11.24) — subscription PK consolidated to webhook_id UUID
(closes the slug→UUID FK debt deferred from v0.9.11.22.9); dispatch
honors webhook_endpoints.channel_type so Slack-typed channels render
Block Kit instead of the generic flat payload.

Runs after every snapshot evaluation (called from
apps/worker/src/snapshot_resources.py). Dedup + cooldown logic:

  - A critical finding NOT present in the prior snapshot fires
    `event=detected`. State row inserted.
  - Same finding on the next snapshot updates `last_seen_at` only.
    No re-fire (dedup).
  - A finding present in state but absent from the current snapshot
    fires `event=resolved`. State row deleted.
  - Cooldown: 1 hour per (finding_id, affected_key). A flap-loop
    (detected → resolved → detected within an hour) only fires the
    first detection in that window.

Severity threshold: only `critical` triggers in v1. Hardcoded for
predictability; severity-tuning UI is deferred to a follow-up.

Subscription model: opt-in via `system_diagnostic_alert_subscriptions`
keyed on `webhook_id` UUID (FK-shaped reference to
`webhook_endpoints.id`). No alerts fire when the subscription set is
empty.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.diagnostic_alerts")


# Severity threshold — only this and higher fire alerts.
SEVERITY_THRESHOLD = "critical"

# Cooldown — a (finding_id, affected_key) won't re-fire detected
# within this many seconds. Prevents flap-loops where a finding
# bounces in and out across consecutive snapshots.
COOLDOWN_SECONDS = 3600

# Webhook delivery timeout. POSTs that exceed this are logged and
# the run continues with the next webhook.
WEBHOOK_TIMEOUT_SECONDS = 10

# Operator-facing dashboard URL. Snapshot worker is fed the absolute
# host via env (NOUSVIZ_DASHBOARD_BASE_URL); falls back to a relative
# path so the alert payload is still informative without that.
import os
_DASHBOARD_BASE_URL = os.environ.get(
    "NOUSVIZ_DASHBOARD_BASE_URL",
    "",
)


# ── Helpers ─────────────────────────────────────────────────────────


def _affected_key(finding: dict) -> str:
    """Stable serialization of finding.affected for dedup keying.

    Sorts by (type, name) so reordering doesn't churn state. Falls
    back to '*' when affected is empty (rare — most rules carry at
    least one affected entry).
    """
    affected = finding.get("affected") or []
    if not affected:
        return "*"
    parts = sorted(
        f"{a.get('type', '?')}:{a.get('name', '?')}"
        for a in affected
    )
    return "|".join(parts)


def _alertable(finding: dict) -> bool:
    return finding.get("severity") == SEVERITY_THRESHOLD


def _is_in_cooldown(state_row: dict, now: datetime) -> bool:
    last = state_row.get("last_alerted_at")
    if last is None:
        return False
    if isinstance(last, str):
        last = datetime.fromisoformat(last.replace("Z", "+00:00"))
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() < COOLDOWN_SECONDS


# ── Subscription management ─────────────────────────────────────────


def list_subscriptions() -> list[dict]:
    """Return outbound webhook endpoints joined with their subscription
    state. The webhooks plugin owns webhook_endpoints; we only read.

    Each item:
      {webhook_id, name, url, is_active, channel_type, subscribed, updated_at}

    v0.9.11.24 (B283): subscription PK is now `webhook_id` UUID (was
    `webhook_slug` text). Existing slug-keyed rows were backfilled by
    migration 070. The COALESCE shim from v0.9.11.22.9 is gone — every
    outbound webhook is addressable directly by its UUID.

    `channel_type` is surfaced so the maintenance UI can show a Slack
    badge next to typed-Slack rows.

    Subscribed=False means either no row in subscriptions OR row with
    enabled=false; the operator UI doesn't need to distinguish.
    """
    out: list[dict] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # webhook_endpoints lives in a plugin. If the plugin isn't
        # installed, the table won't exist and we return [].
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            return []
        cur.execute(
            """
            SELECT we.id::text, we.name, we.url, we.is_active,
                   COALESCE(we.channel_type, 'generic') AS channel_type,
                   COALESCE(s.enabled, FALSE) AS subscribed,
                   s.updated_at
            FROM webhook_endpoints we
            LEFT JOIN system_diagnostic_alert_subscriptions s
              ON s.webhook_id = we.id
            WHERE we.direction = 'outbound'
            ORDER BY we.name
            """
        )
        for row in cur.fetchall():
            (webhook_id, name, url, is_active, channel_type,
             subscribed, updated_at) = row
            out.append({
                "webhook_id": webhook_id,
                "name": name,
                "url": url,
                "is_active": bool(is_active),
                "channel_type": channel_type or "generic",
                "subscribed": bool(subscribed),
                "updated_at": updated_at.isoformat() if updated_at else None,
            })
    return out


def set_subscription(
    webhook_id: str,
    enabled: bool,
    *,
    by_user: Optional[str] = None,
) -> None:
    """Upsert a subscription row. Validates webhook_id against
    webhook_endpoints to refuse unknown identifiers."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            raise RuntimeError(
                "webhook_endpoints table missing — install the webhooks plugin"
            )
        cur.execute(
            """
            SELECT 1 FROM webhook_endpoints
            WHERE id = %s::uuid AND direction = 'outbound'
            """,
            (webhook_id,),
        )
        if not cur.fetchone():
            raise KeyError(f"Unknown outbound webhook id: {webhook_id!r}")

        cur.execute(
            """
            INSERT INTO system_diagnostic_alert_subscriptions
                (webhook_id, enabled, created_by, created_at, updated_at)
            VALUES (%s::uuid, %s, %s, now(), now())
            ON CONFLICT (webhook_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                updated_at = now()
            """,
            (webhook_id, bool(enabled), by_user),
        )
        conn.commit()


def _load_subscribed_webhooks() -> list[dict]:
    """Return outbound webhooks with active subscription, ready to dispatch.

    Skips webhooks whose `is_active` is false OR whose subscription is
    `enabled=false` so the operator can pause one without removing the
    row. v0.9.11.24 (B283): adds `channel_type` + `channel_config` so
    `_dispatch` can render Slack Block Kit when appropriate.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            return []
        cur.execute(
            """
            SELECT we.id::text, we.name, we.url, we.secret,
                   COALESCE(we.channel_type, 'generic') AS channel_type,
                   COALESCE(we.channel_config, '{}'::jsonb) AS channel_config
            FROM webhook_endpoints we
            JOIN system_diagnostic_alert_subscriptions s
              ON s.webhook_id = we.id
                 AND s.enabled = TRUE
            WHERE we.direction = 'outbound'
              AND we.is_active = TRUE
              AND we.url IS NOT NULL
            """
        )
        out: list[dict] = []
        for (wid, name, url, secret, channel_type, channel_config) in cur.fetchall():
            out.append({
                "id": wid,
                "name": name,
                "url": url,
                "secret": secret,
                "channel_type": channel_type or "generic",
                "channel_config": channel_config or {},
            })
        return out


# ── Webhook dispatch ────────────────────────────────────────────────


def _build_payload(
    finding: dict,
    *,
    event: str,
    state_row: Optional[dict],
    now: datetime,
) -> dict:
    """Compose the webhook body. Same shape across detected/resolved
    so consumers can route on `event` without reshaping their parsers."""
    first_detected = (
        state_row.get("first_detected_at") if state_row else now
    )
    if isinstance(first_detected, datetime):
        first_detected = first_detected.isoformat()

    dashboard_url = (
        f"{_DASHBOARD_BASE_URL.rstrip('/')}/system/health"
        if _DASHBOARD_BASE_URL else "/system/health"
    )

    # v0.9.11.22.8: top-level `text` summary so Slack incoming webhooks
    # accept the payload (Slack returns 400 when `text` is missing).
    # All structured fields preserved below for any other consumer.
    severity_emoji = {
        "critical": ":rotating_light:",
        "warn": ":warning:",
        "info": ":information_source:",
    }.get(finding.get("severity", ""), "")
    event_label = "DETECTED" if event == "detected" else "RESOLVED"
    text_summary = (
        f"{severity_emoji} [{event_label}] {finding.get('title', '(untitled)')} "
        f"({finding.get('severity', '?')}) — {dashboard_url}"
    ).strip()

    return {
        "text": text_summary,
        "version": "1.0",
        "alert_type": "diagnostic_finding",
        "event": event,
        "finding_id": finding.get("id"),
        "severity": finding.get("severity"),
        "title": finding.get("title"),
        "evidence": finding.get("evidence"),
        "recommendation": finding.get("recommendation"),
        "affected": finding.get("affected") or [],
        "first_detected_at": first_detected,
        "fired_at": now.isoformat(),
        "dashboard_url": dashboard_url,
    }


def _post_webhook(url: str, secret: Optional[str], body: bytes) -> None:
    """HMAC-signed POST. Delegates to the shared
    `apps/api/src/services/webhook_dispatch.py:post_webhook` helper
    (B284 refactor, v0.9.11.23) so this and `job_alerts.py` go
    through one implementation of the POST contract.

    Kept as a module-level wrapper with the same signature so existing
    tests that monkey-patch `bridge._post_webhook` continue to work.
    """
    from .webhook_dispatch import post_webhook as _shared
    _shared(url, secret, body)


def _dispatch(finding: dict, *, event: str, state_row: Optional[dict], now: datetime) -> int:
    """POST the payload to every subscribed webhook. Returns count of
    successful deliveries. Per-webhook failures are logged and don't
    abort the run.

    v0.9.11.24 (B283): per-target body is rendered via
    `webhook_dispatch.format_for_channel`. Generic-type webhooks see
    today's flat payload (byte-identical regression pin in
    `tests/test_webhook_dispatch.py`); Slack-typed webhooks see Block
    Kit with mention prefix + channel override applied.
    """
    targets = _load_subscribed_webhooks()
    if not targets:
        return 0
    payload = _build_payload(finding, event=event, state_row=state_row, now=now)
    delivered = 0
    for t in targets:
        # Older monkeypatch fixtures pass `slug` not `id`; tolerate it
        # so test pins from B274 keep their fixture shape.
        target_label = t.get("name") or t.get("id") or t.get("slug") or "?"
        try:
            from .webhook_dispatch import format_for_channel
            body = format_for_channel(
                payload,
                t.get("channel_type") or "generic",
                t.get("channel_config") or {},
            )
            _post_webhook(t["url"], t.get("secret"), body)
            delivered += 1
            logger.info(
                "diagnostic_alerts: %s → %s (event=%s, finding=%s, channel=%s)",
                target_label, t["url"], event, finding.get("id"),
                t.get("channel_type") or "generic",
            )
        except urllib.error.HTTPError as e:
            logger.warning(
                "diagnostic_alerts: webhook %s returned HTTP %s for finding %s",
                target_label, e.code, finding.get("id"),
            )
        except Exception as e:
            logger.warning(
                "diagnostic_alerts: webhook %s failed for finding %s: %s",
                target_label, finding.get("id"), e,
            )
    return delivered


# ── State queries ───────────────────────────────────────────────────


def _load_current_state() -> dict[tuple[str, str], dict]:
    """Return all active state rows keyed by (finding_id, affected_key)."""
    out: dict[tuple[str, str], dict] = {}
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT finding_id, affected_key, severity, title,
                   first_detected_at, last_seen_at, last_alerted_at,
                   alerts_fired
            FROM system_diagnostic_alert_state
            """
        )
        for row in cur.fetchall():
            (fid, akey, sev, title, first_detected, last_seen,
             last_alerted, alerts_fired) = row
            out[(fid, akey)] = {
                "finding_id": fid,
                "affected_key": akey,
                "severity": sev,
                "title": title,
                "first_detected_at": first_detected,
                "last_seen_at": last_seen,
                "last_alerted_at": last_alerted,
                "alerts_fired": int(alerts_fired or 0),
            }
    return out


def get_alert_state_for_findings(findings: list[dict]) -> dict[tuple[str, str], Optional[str]]:
    """Lightweight lookup used by the diagnostics route. Returns
    {(finding_id, affected_key): last_alerted_at_iso_or_None}. Findings
    not currently in state map to None — UI then doesn't render the
    "alert sent" badge.
    """
    state = _load_current_state()
    out: dict[tuple[str, str], Optional[str]] = {}
    for f in findings:
        key = (f.get("id"), _affected_key(f))
        row = state.get(key)
        last = row.get("last_alerted_at") if row else None
        if isinstance(last, datetime):
            last = last.isoformat()
        out[key] = last
    return out


# ── Main entry ──────────────────────────────────────────────────────


def process_findings(
    findings: list[dict],
    *,
    ts: Optional[datetime] = None,
) -> dict:
    """Diff current findings vs persisted state, fire detected/resolved
    alerts, return a summary dict.

    Returns:
        {
            "detected": int,   # newly detected critical findings (alerts fired)
            "resolved": int,   # findings that disappeared (alerts fired)
            "deduped": int,    # findings still active (no alert)
            "skipped_cooldown": int,  # would have fired but in cooldown window
            "subscribed_webhooks": int,
        }
    """
    now = ts or datetime.now(timezone.utc)
    summary = {
        "detected": 0,
        "resolved": 0,
        "deduped": 0,
        "skipped_cooldown": 0,
        "subscribed_webhooks": len(_load_subscribed_webhooks()),
    }

    # Filter to alertable severity. Findings below threshold don't
    # participate in state at all — they don't need dedup since they
    # never fire.
    current_alertable = [f for f in (findings or []) if _alertable(f)]
    current_keys: dict[tuple[str, str], dict] = {}
    for f in current_alertable:
        key = (f.get("id"), _affected_key(f))
        current_keys[key] = f

    state = _load_current_state()

    # Detected (or re-evaluated) findings.
    for key, finding in current_keys.items():
        existing = state.get(key)
        already_alerted = (
            existing is not None
            and existing.get("last_alerted_at") is not None
        )
        if already_alerted:
            # Dedup: known finding + we've already alerted on it.
            # Just refresh last_seen.
            _touch_state(key, now)
            summary["deduped"] += 1
        else:
            # Either brand-new OR seen before but never delivered
            # (no subscriptions at the time, or every webhook failed).
            # Try to fire — subscriptions may have been added since
            # the last attempt, in which case this is the first real
            # alert. last_alerted_at only flips when delivery succeeded
            # so the cooldown is anchored to actual sends, not attempts.
            delivered = _fire(finding, "detected", existing, now)
            if delivered:
                summary["detected"] += 1
            _upsert_state(finding, now=now, alerted=delivered)

    # Resolved findings.
    for key, state_row in state.items():
        if key in current_keys:
            continue
        # Finding gone. Fire resolved.
        # Build a minimal "finding-like" dict from the state row so the
        # webhook payload is still informative.
        synth = {
            "id": state_row.get("finding_id"),
            "severity": state_row.get("severity"),
            "title": state_row.get("title"),
            "evidence": "Finding cleared since last evaluation.",
            "recommendation": "No action required — issue resolved.",
            "affected": _key_to_affected(state_row.get("affected_key", "*")),
        }
        # Cooldown gating applies to resolved too — to avoid flap-loop
        # spam — but in a softer form: we still delete the state row
        # so the next detection can fire after cooldown.
        if _fire(synth, "resolved", state_row, now):
            summary["resolved"] += 1
        _delete_state(key)

    return summary


def _fire(
    finding: dict,
    event: str,
    state_row: Optional[dict],
    now: datetime,
) -> bool:
    """Send the alert if not in cooldown. Returns True if dispatched.

    Cooldown logic:
      - For event=detected: if state has last_alerted_at within COOLDOWN,
        skip (prevents flap-loops).
      - For event=resolved: always dispatch — resolved is a one-shot
        event tied to state-row deletion, so it can't flap.
    """
    if event == "detected" and state_row is not None and _is_in_cooldown(state_row, now):
        return False
    delivered = _dispatch(finding, event=event, state_row=state_row, now=now)
    return delivered > 0


def _upsert_state(finding: dict, *, now: datetime, alerted: bool) -> None:
    key_id = finding.get("id")
    key_aff = _affected_key(finding)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO system_diagnostic_alert_state (
                finding_id, affected_key, severity, title,
                first_detected_at, last_seen_at, last_alerted_at,
                alerts_fired
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (finding_id, affected_key) DO UPDATE SET
                severity = EXCLUDED.severity,
                title    = EXCLUDED.title,
                last_seen_at = EXCLUDED.last_seen_at,
                last_alerted_at = CASE
                    WHEN %s THEN EXCLUDED.last_alerted_at
                    ELSE system_diagnostic_alert_state.last_alerted_at
                END,
                alerts_fired = system_diagnostic_alert_state.alerts_fired + CASE
                    WHEN %s THEN 1 ELSE 0 END
            """,
            (
                key_id, key_aff,
                finding.get("severity"), finding.get("title"),
                now, now, now if alerted else None,
                1 if alerted else 0,
                bool(alerted), bool(alerted),
            ),
        )
        conn.commit()


def _touch_state(key: tuple[str, str], now: datetime) -> None:
    fid, aff = key
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE system_diagnostic_alert_state
            SET last_seen_at = %s
            WHERE finding_id = %s AND affected_key = %s
            """,
            (now, fid, aff),
        )
        conn.commit()


def _delete_state(key: tuple[str, str]) -> None:
    fid, aff = key
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM system_diagnostic_alert_state
            WHERE finding_id = %s AND affected_key = %s
            """,
            (fid, aff),
        )
        conn.commit()


def _key_to_affected(key: str) -> list[dict]:
    """Reverse of _affected_key for resolved-event payload composition."""
    if key == "*":
        return []
    out: list[dict] = []
    for piece in key.split("|"):
        if ":" in piece:
            t, n = piece.split(":", 1)
            out.append({"type": t, "name": n})
    return out


# ── Synthetic test alert (used by the "Send test" button) ───────────


def fire_test_alert(*, by_user: Optional[str] = None) -> dict:
    """Fire a fake critical finding to every subscribed webhook. Used
    by /api/maintenance/diagnostic-alerts/test for one-click verification
    after configuring a webhook."""
    now = datetime.now(timezone.utc)
    finding = {
        "id": "test_alert",
        "severity": "critical",
        "title": "Test alert from /settings/maintenance",
        "evidence": "This is a synthetic test alert dispatched manually.",
        "recommendation": "If you're seeing this, your webhook subscription is working.",
        "affected": [{"type": "test", "name": "synthetic"}],
    }
    delivered = _dispatch(finding, event="detected", state_row=None, now=now)
    return {
        "delivered": delivered,
        "subscribed_webhooks": len(_load_subscribed_webhooks()),
    }
