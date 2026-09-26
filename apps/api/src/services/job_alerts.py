"""
B284 (v0.9.11.23) — per-job-run failure alert bridge.

Called from `apps/worker/src/run_jobs.py:_finalize_run` whenever a run
terminates with status in {error, timeout, cancelled}. Looks up
matching subscriptions in `job_alert_subscriptions`, derives a
suggested-fix from the error excerpt, and dispatches a webhook for
each subscribed (plugin, status, webhook) match.

Reuses the shared `webhook_dispatch.post_webhook` HMAC-signed POST
helper. Per-subscription delivery failures are isolated so one bad
URL doesn't prevent others from firing — and dispatch failures don't
roll back the run finalization (try/except in the worker hook).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.job_alerts")


# ── Suggested-fix static map ────────────────────────────────────────


# Ordered list — first match wins. More-specific patterns come BEFORE
# broader ones so e.g. UniqueViolation isn't accidentally caught by
# the OperationalError fallback. Patterns are case-insensitive.
SUGGESTED_FIX_MAP: list[tuple[re.Pattern, str]] = [
    (
        # DB constraint violations come BEFORE the generic OperationalError
        # pattern below so UniqueViolation/ForeignKeyViolation surface as
        # a constraint problem, not a connection problem.
        re.compile(r"IntegrityError|UniqueViolation|ForeignKey(Violation)?|CheckViolation", re.I),
        "Database constraint violation. Look for duplicate or stale rows colliding with the new sync.",
    ),
    (
        re.compile(r"Missing.*OAuth|invalid_grant|expired_token|401.*unauthorized", re.I),
        "OAuth token expired or revoked. Re-authorize the plugin in /plugin/<id>/settings.",
    ),
    (
        re.compile(r"requests\.exceptions|HTTPError|ConnectionError|RemoteDisconnected|\b(429|502|503)\b", re.I),
        "Upstream API unreachable, throttled, or returning errors. Check the upstream service status; consider widening the cron interval.",
    ),
    (
        # Connection/credential errors. Tightened from the original
        # bare `psycopg2` to specific connection-shaped phrases —
        # UniqueViolation etc. above already caught more-specific
        # psycopg2 errors before reaching here.
        re.compile(r"OperationalError|connection refused|password authentication failed|FATAL:", re.I),
        "Postgres connection or credential issue. Check the credentials in /plugin/<id>/settings, then verify the DB host is reachable.",
    ),
    (
        re.compile(r"KeyError|AttributeError|TypeError|JSONDecodeError|ValidationError", re.I),
        "Likely a schema change in upstream data. Inspect the recent run's stdout in /system/logs and update the plugin's parser.",
    ),
    (
        re.compile(r"MemoryError|killed|signal 9|out of memory", re.I),
        "Worker out of memory. Reduce batch size in plugin.yaml or upgrade host memory.",
    ),
    (
        re.compile(r"Exceeded timeout|timed out", re.I),
        "Sync exceeded its configured timeout. Either widen `sync.timeout_seconds` in plugin.yaml or split the workload.",
    ),
]

DEFAULT_SUGGESTION = (
    "Open /system/jobs and inspect the full traceback. Search /system/logs "
    "for the run id."
)


def derive_suggested_fix(error_text: Optional[str]) -> str:
    """First matching pattern wins; falls back to a generic suggestion
    when no pattern matches (or the error column is empty)."""
    if not error_text:
        return DEFAULT_SUGGESTION
    for pattern, suggestion in SUGGESTED_FIX_MAP:
        if pattern.search(error_text):
            return suggestion
    return DEFAULT_SUGGESTION


# ── Status filter validation ────────────────────────────────────────


# Statuses an operator can subscribe to. `success` is deliberately
# excluded — we never alert on success (way too noisy). `running` /
# `queued` / `cancelling` are not terminal, so they're not meaningful
# for failure alerts either.
#
# `missed` is not written by a run. The scheduler's watchdog records it
# when a scheduled fire produced no run at all (worker down, run stuck in
# the queue), because a run that never starts never reaches
# `_finalize_run` and so could never alert on its own.
ALERTABLE_STATUSES = frozenset({"error", "timeout", "cancelled", "missed"})


def _validate_on_status(on_status: list[str]) -> list[str]:
    """Refuse statuses that aren't in ALERTABLE_STATUSES. Returns the
    sanitised list."""
    if not on_status:
        raise ValueError("on_status must contain at least one status")
    out = []
    for s in on_status:
        if s not in ALERTABLE_STATUSES:
            raise ValueError(
                f"Invalid on_status value: {s!r}. "
                f"Allowed: {sorted(ALERTABLE_STATUSES)}"
            )
        if s not in out:
            out.append(s)
    return out


# Plugin id regex — same shape as plugin slugs throughout the
# codebase, plus the `*` wildcard for "any plugin".
_PLUGIN_ID_RE = re.compile(r"^(\*|[a-zA-Z][a-zA-Z0-9_-]*)$")


def _validate_plugin_id(plugin_id: str) -> str:
    if not _PLUGIN_ID_RE.match(plugin_id):
        raise ValueError(
            f"Invalid plugin_id: {plugin_id!r}. Must be '*' or a plugin slug."
        )
    return plugin_id


# ── Available webhooks (picker source) ─────────────────────────────


def list_available_webhooks() -> list[dict]:
    """Return outbound webhooks for the create-subscription picker.

    Each item: {id, name, url, is_active}. id is a UUID string — what
    the create endpoint expects as `webhook_id`. Webhooks plugin not
    installed → []. Inactive webhooks are returned but flagged so the
    UI can render them disabled in the dropdown.
    """
    out: list[dict] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            return out
        cur.execute(
            """
            SELECT id::text, name, url, is_active
            FROM webhook_endpoints
            WHERE direction = 'outbound'
            ORDER BY name
            """
        )
        for row in cur.fetchall():
            out.append({
                "id": row[0],
                "name": row[1],
                "url": row[2],
                "is_active": bool(row[3]),
            })
    return out


# ── Subscription CRUD ──────────────────────────────────────────────


def list_subscriptions() -> list[dict]:
    """Return all subscriptions joined with webhook info. Webhooks
    plugin not installed → returns []."""
    out: list[dict] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            # No webhooks plugin → still return our subscription rows
            # without webhook_name/url (UI can render orphans).
            cur.execute(
                """
                SELECT id, plugin_id, on_status, webhook_id, enabled,
                       updated_at
                FROM job_alert_subscriptions
                ORDER BY plugin_id, updated_at
                """
            )
            for row in cur.fetchall():
                out.append({
                    "id": str(row[0]),
                    "plugin_id": row[1],
                    "on_status": list(row[2] or []),
                    "webhook_id": str(row[3]),
                    "webhook_name": None,
                    "webhook_url": None,
                    "webhook_active": False,
                    "enabled": bool(row[4]),
                    "updated_at": row[5].isoformat() if row[5] else None,
                })
            return out

        cur.execute(
            """
            SELECT s.id, s.plugin_id, s.on_status, s.webhook_id, s.enabled,
                   s.updated_at,
                   we.name, we.url, we.is_active,
                   COALESCE(we.channel_type, 'generic') AS channel_type
            FROM job_alert_subscriptions s
            LEFT JOIN webhook_endpoints we ON we.id = s.webhook_id
            ORDER BY s.plugin_id, s.updated_at
            """
        )
        for row in cur.fetchall():
            (sid, plugin_id, on_status, webhook_id, enabled, updated_at,
             webhook_name, webhook_url, webhook_active, channel_type) = row
            out.append({
                "id": str(sid),
                "plugin_id": plugin_id,
                "on_status": list(on_status or []),
                "webhook_id": str(webhook_id),
                "webhook_name": webhook_name,
                "webhook_url": webhook_url,
                "webhook_active": bool(webhook_active) if webhook_active is not None else False,
                "webhook_channel_type": channel_type if webhook_name else None,
                "enabled": bool(enabled),
                "updated_at": updated_at.isoformat() if updated_at else None,
            })
    return out


def _verify_webhook_id_exists(cur, webhook_id: str) -> None:
    """Raise KeyError if webhook_id isn't in webhook_endpoints with
    direction='outbound'."""
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
        raise KeyError(f"Unknown outbound webhook_id: {webhook_id!r}")


def create_subscription(
    plugin_id: str,
    on_status: list[str],
    webhook_id: str,
    *,
    by_user: Optional[str] = None,
) -> str:
    """Create a new subscription. Returns the new id (UUID string).

    Raises ValueError on invalid plugin_id / on_status, KeyError on
    unknown webhook_id, RuntimeError on duplicate (plugin_id,
    webhook_id) UNIQUE violation.
    """
    plugin_id = _validate_plugin_id(plugin_id)
    on_status = _validate_on_status(on_status)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        _verify_webhook_id_exists(cur, webhook_id)
        try:
            cur.execute(
                """
                INSERT INTO job_alert_subscriptions
                    (plugin_id, on_status, webhook_id, created_by)
                VALUES (%s, %s, %s::uuid, %s)
                RETURNING id
                """,
                (plugin_id, on_status, webhook_id, by_user),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return str(new_id)
        except Exception as e:
            conn.rollback()
            msg = str(e).lower()
            if "unique" in msg or "duplicate" in msg:
                raise RuntimeError(
                    f"Subscription already exists for plugin={plugin_id!r} + webhook={webhook_id!r}. "
                    f"Update or delete the existing subscription instead."
                ) from e
            raise


def update_subscription(
    sub_id: str,
    *,
    on_status: Optional[list[str]] = None,
    enabled: Optional[bool] = None,
    by_user: Optional[str] = None,
) -> dict:
    """Update an existing subscription. Returns the updated row.

    Either or both of on_status / enabled may be passed; pass only
    what's changing.
    """
    if on_status is None and enabled is None:
        raise ValueError("Pass at least one of on_status or enabled")
    if on_status is not None:
        on_status = _validate_on_status(on_status)

    set_parts: list[str] = []
    values: list = []
    if on_status is not None:
        set_parts.append("on_status = %s")
        values.append(on_status)
    if enabled is not None:
        set_parts.append("enabled = %s")
        values.append(bool(enabled))
    set_parts.append("updated_at = now()")
    values.append(sub_id)

    sql = f"""
        UPDATE job_alert_subscriptions
        SET {', '.join(set_parts)}
        WHERE id = %s::uuid
        RETURNING id
    """

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, values)
        if not cur.fetchone():
            raise KeyError(f"Subscription not found: {sub_id!r}")
        conn.commit()

    # Return the joined row for the API response.
    for s in list_subscriptions():
        if s["id"] == sub_id:
            return s
    raise RuntimeError(f"Subscription disappeared after update: {sub_id!r}")


def delete_subscription(sub_id: str, *, by_user: Optional[str] = None) -> None:
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM job_alert_subscriptions WHERE id = %s::uuid",
            (sub_id,),
        )
        if cur.rowcount == 0:
            raise KeyError(f"Subscription not found: {sub_id!r}")
        conn.commit()


# ── Dispatch ────────────────────────────────────────────────────────


_DASHBOARD_BASE_URL = os.environ.get("NOUSVIZ_DASHBOARD_BASE_URL", "")


def _plugin_id_from_job_id(job_id: Optional[str]) -> Optional[str]:
    """Extract plugin slug from a job_id like 'sync:my-plugin'. Returns
    None for hook jobs and other non-sync shapes."""
    if not job_id or not job_id.startswith("sync:"):
        return None
    return job_id[len("sync:"):]


def _build_payload(run: dict, *, suggested_fix: str, now: datetime) -> dict:
    """Compose the webhook body. Slack-compatible top-level `text`
    summary plus full structured fields."""
    plugin_id = _plugin_id_from_job_id(run.get("job_id"))
    status = run.get("status") or "?"
    severity_emoji = {
        "error": ":rotating_light:",
        "timeout": ":hourglass:",
        "cancelled": ":no_entry_sign:",
        "missed": ":warning:",
    }.get(status, "")
    base = (_DASHBOARD_BASE_URL.rstrip("/") + "/") if _DASHBOARD_BASE_URL else "/"
    dashboard_url = f"{base}system/jobs"
    logs_url = f"{base}system/logs?run_id={run.get('id')}" if run.get("id") else f"{base}system/logs"

    title = f"sync:{plugin_id} {status}" if plugin_id else f"{run.get('job_id') or 'job'} {status}"
    text_summary = (
        f"{severity_emoji} [{status}] {title} (run {run.get('id')}) — "
        f"Suggested: {suggested_fix} · {logs_url}"
    ).strip()

    started_at = run.get("started_at")
    if isinstance(started_at, datetime):
        started_at = started_at.isoformat()

    return {
        "text": text_summary,
        "version": "1.0",
        "alert_type": "job_run_failure",
        "plugin_id": plugin_id,
        "job_id": run.get("job_id"),
        "run_id": run.get("id"),
        "status": status,
        "error_excerpt": run.get("error"),
        "suggested_fix": suggested_fix,
        "duration_ms": run.get("duration_ms"),
        "started_at": started_at,
        "fired_at": now.isoformat(),
        "dashboard_url": dashboard_url,
        "logs_url": logs_url,
    }


def _load_matching_subscriptions(plugin_id: Optional[str], status: str) -> list[dict]:
    """Subscriptions where (plugin_id matches or '*') AND on_status
    contains status AND enabled. Joined with webhook_endpoints to get
    url + secret + channel info. Webhooks plugin not installed → [].

    v0.9.11.24 (B283): pulls `channel_type` + `channel_config` so
    `_dispatch_to_subscription` can render Slack Block Kit when a
    subscription points at a typed-Slack webhook.
    """
    out: list[dict] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            return out
        cur.execute(
            """
            SELECT s.id, s.plugin_id, s.on_status,
                   we.url, we.secret, we.name,
                   COALESCE(we.channel_type, 'generic') AS channel_type,
                   COALESCE(we.channel_config, '{}'::jsonb) AS channel_config
            FROM job_alert_subscriptions s
            JOIN webhook_endpoints we ON we.id = s.webhook_id
            WHERE s.enabled = TRUE
              AND we.is_active = TRUE
              AND we.url IS NOT NULL
              AND we.direction = 'outbound'
              AND (s.plugin_id = '*' OR s.plugin_id = %s)
              AND %s = ANY(s.on_status)
            """,
            (plugin_id, status),
        )
        for row in cur.fetchall():
            out.append({
                "id": str(row[0]),
                "plugin_id": row[1],
                "on_status": list(row[2] or []),
                "url": row[3],
                "secret": row[4],
                "name": row[5],
                "channel_type": row[6] or "generic",
                "channel_config": row[7] or {},
            })
    return out


def _dispatch_to_subscription(sub: dict, payload: dict) -> bool:
    """POST to one subscription's webhook. Returns True on success,
    False on failure (caller already isolates per-subscription).

    v0.9.11.24 (B283): renders payload via `format_for_channel` so
    Slack-typed webhooks see Block Kit; generic-typed webhooks see
    today's flat payload (byte-identical regression pin in
    `tests/test_webhook_dispatch.py`).
    """
    from .webhook_dispatch import format_for_channel, post_webhook
    body = format_for_channel(
        payload,
        sub.get("channel_type") or "generic",
        sub.get("channel_config") or {},
    )
    try:
        post_webhook(sub["url"], sub.get("secret"), body)
        return True
    except urllib.error.HTTPError as e:
        logger.warning(
            "job_alerts: webhook %s returned HTTP %s for run %s",
            sub.get("name") or sub["id"], e.code, payload.get("run_id"),
        )
        return False
    except Exception as e:
        logger.warning(
            "job_alerts: webhook %s failed for run %s: %s",
            sub.get("name") or sub["id"], payload.get("run_id"), e,
        )
        return False


# ── Operator email ──────────────────────────────────────────────────


def _email_recipients() -> list[str]:
    """`JOB_ALERT_EMAIL_TO`, comma-separated. Empty means no email.

    Email is an operator-level channel rather than a subscription: it
    needs no webhooks plugin, and the watchdog's `missed` alert has to
    reach someone even on an install with no subscriptions at all.
    """
    raw = os.environ.get("JOB_ALERT_EMAIL_TO", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _send_email_alert(payload: dict, recipients: list[str]) -> int:
    """Send the alert to each recipient. Returns how many were sent.

    Failures are logged and swallowed, like webhook delivery: an
    unreachable SMTP server must not affect the run it reports on.
    """
    from html import escape

    from .email import _send, is_configured
    if not is_configured():
        logger.warning("job_alerts: JOB_ALERT_EMAIL_TO is set but SMTP is not configured")
        return 0
    title = f"{payload.get('job_id') or 'job'} {payload.get('status')}"
    subject = f"[NousViz] {title}"
    lines = [
        payload.get("text") or title,
        "",
        f"Run: {payload.get('run_id')}",
        f"Error: {payload.get('error_excerpt') or '(none)'}",
        f"Suggested: {payload.get('suggested_fix')}",
        f"Logs: {payload.get('logs_url')}",
    ]
    plain = "\n".join(lines)
    html = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;'
        'max-width:560px;margin:0 auto;padding:24px;">'
        f'<h2 style="font-size:18px;margin:0 0 12px;">{escape(title)}</h2>'
        f'<pre style="font-size:12px;white-space:pre-wrap;">{escape(plain)}</pre>'
        "</div>"
    )
    sent = 0
    for to in recipients:
        ok, err = _send(to, subject, html, plain)
        if ok:
            sent += 1
        else:
            logger.warning("job_alerts: email to %s failed: %s", to, err)
    return sent


def process_run_failure(run: dict, *, ts: Optional[datetime] = None) -> dict:
    """Main entry — called from worker after a terminal-status commit,
    and from the scheduler's missed-run watchdog.

    Args:
      run: dict with id, job_id, status, error, duration_ms?, started_at?

    Returns a summary:
      {matched: int, delivered: int, failed: int, emailed: int}
    """
    now = ts or datetime.now(timezone.utc)
    summary = {"matched": 0, "delivered": 0, "failed": 0, "emailed": 0}

    status = run.get("status") or ""
    if status not in ALERTABLE_STATUSES:
        return summary

    plugin_id = _plugin_id_from_job_id(run.get("job_id"))
    if plugin_id is None:
        # Non-sync job (hooks etc.) — skip. Hook failure alerts can be
        # added later if operator wants.
        return summary

    subs = _load_matching_subscriptions(plugin_id, status)
    summary["matched"] = len(subs)
    recipients = _email_recipients()
    if not subs and not recipients:
        return summary

    suggested_fix = derive_suggested_fix(run.get("error"))
    payload = _build_payload(run, suggested_fix=suggested_fix, now=now)

    for sub in subs:
        if _dispatch_to_subscription(sub, payload):
            summary["delivered"] += 1
        else:
            summary["failed"] += 1
    if recipients:
        try:
            summary["emailed"] = _send_email_alert(payload, recipients)
        except Exception as exc:
            logger.warning("job_alerts: email dispatch failed for run %s: %s",
                           run.get("id"), exc)
    return summary


# ── Missed-run watchdog ─────────────────────────────────────────────

# Statuses that prove a scheduled fire was acted on. `queued` is absent on
# purpose: a run that sits in the queue past the grace period is exactly
# the dead-worker case this exists to catch.
_ACTED_ON_STATUSES = ("success", "error", "timeout", "cancelled",
                      "running", "cancelling")

# How long after a scheduled fire before its absence is called missed.
DEFAULT_MISSED_GRACE_MINUTES = 120


def _missed_grace_minutes() -> int:
    raw = os.environ.get("JOB_ALERT_MISSED_GRACE_MINUTES", "")
    try:
        return max(5, int(raw)) if raw.strip() else DEFAULT_MISSED_GRACE_MINUTES
    except ValueError:
        return DEFAULT_MISSED_GRACE_MINUTES


def _prev_fire(cron: str, before: datetime) -> Optional[datetime]:
    from croniter import croniter
    try:
        prev = croniter(cron, before).get_prev(datetime)
    except Exception:
        return None
    return prev if prev.tzinfo else prev.replace(tzinfo=timezone.utc)


def check_missed_runs(*, now: Optional[datetime] = None) -> list[dict]:
    """Record and alert on scheduled syncs that never ran.

    For each cron-scheduled plugin, take the most recent fire that is at
    least the grace period old and check it with `_check_one`. Returns
    the missed runs recorded on this call.
    """
    now = now or datetime.now(timezone.utc)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT plugin_id, cron_expression FROM sync_schedule_registry")
        schedules = cur.fetchall()
    recorded: list[dict] = []
    for plugin_id, cron in schedules:
        run = _check_one(plugin_id, cron, now=now)
        if run:
            recorded.append(run)
    return recorded


def _check_one(plugin_id: str, cron: str, *, now: datetime) -> Optional[dict]:
    """Decide whether one plugin's most recent due fire was missed.

    If no run was acted on since that fire, write a `missed` row to
    job_runs (so it shows in job history) and send it through
    `process_run_failure`. The row doubles as the dedupe key: one alert
    per missed fire, however often this is called or by how many
    schedulers.

    A plugin with no run before that fire is skipped: it was installed
    or scheduled after the fire, so nothing was missed.
    """
    grace = _missed_grace_minutes()
    fire = _prev_fire(cron, now - timedelta(minutes=grace))
    if fire is None:
        return None
    job_id = f"sync:{plugin_id}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # Serialise per (job, fire) so two schedulers cannot both record
        # the same miss.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"{job_id}|{fire.isoformat()}",))
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM job_runs WHERE job_id = %s AND started_at < %s)",
            (job_id, fire),
        )
        if not cur.fetchone()[0]:
            conn.commit()
            return None
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM job_runs
                WHERE job_id = %s
                  AND (
                    -- Acted on: started for this fire, still in flight
                    -- (the scheduler skips a fire while a run is
                    -- active), or finished after it.
                    (status = ANY(%s)
                     AND (started_at >= %s - interval '5 minutes'
                          OR completed_at IS NULL
                          OR completed_at >= %s))
                    -- Already recorded as missed.
                    OR (status = 'missed'
                        AND details->>'scheduled_fire_at' = %s))
            )
            """,
            (job_id, list(_ACTED_ON_STATUSES), fire, fire, fire.isoformat()),
        )
        if cur.fetchone()[0]:
            conn.commit()
            return None
        error = (
            f"Scheduled run for {fire.isoformat()} ({cron}) did not start "
            f"within {grace} minutes. Check that the job worker and "
            f"scheduler are running (/system/jobs)."
        )
        cur.execute(
            """
            INSERT INTO job_runs (job_id, status, source, started_at,
                                  completed_at, error, details)
            VALUES (%s, 'missed', 'watchdog', %s, now(), %s, %s::jsonb)
            RETURNING id
            """,
            (job_id, fire, error, json.dumps({
                "scheduled_fire_at": fire.isoformat(),
                "cron_expression": cron,
                "grace_minutes": grace,
            })),
        )
        run_id = cur.fetchone()[0]
        conn.commit()
    run = {"id": run_id, "job_id": job_id, "status": "missed", "error": error}
    try:
        process_run_failure(run, ts=now)
    except Exception as exc:
        logger.warning("job_alerts: missed-run alert failed for %s: %s", job_id, exc)
    return run


def fire_test_alert_for_subscription(
    sub_id: str,
    *,
    by_user: Optional[str] = None,
) -> dict:
    """Fire a synthetic 'job_run_failure' payload to the subscription's
    webhook. Used by `/api/maintenance/job-alerts/{id}/test` for
    one-click verification.
    """
    now = datetime.now(timezone.utc)

    # Fetch the subscription joined with the webhook so we can dispatch
    # without going through the per-status filter.
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.webhook_endpoints')")
        if (cur.fetchone() or [None])[0] is None:
            raise RuntimeError("webhooks plugin not installed")
        cur.execute(
            """
            SELECT s.plugin_id, we.url, we.secret, we.name, we.is_active,
                   COALESCE(we.channel_type, 'generic') AS channel_type,
                   COALESCE(we.channel_config, '{}'::jsonb) AS channel_config
            FROM job_alert_subscriptions s
            JOIN webhook_endpoints we ON we.id = s.webhook_id
            WHERE s.id = %s::uuid
            """,
            (sub_id,),
        )
        row = cur.fetchone()
    if not row:
        raise KeyError(f"Subscription not found: {sub_id!r}")
    plugin_id, url, secret, name, is_active, channel_type, channel_config = row
    if not is_active or not url:
        return {"delivered": 0, "skipped": 1, "reason": "webhook inactive or url missing"}

    synthetic = {
        "id": 0,
        "job_id": f"sync:{plugin_id}" if plugin_id != "*" else "sync:test-plugin",
        "status": "error",
        "error": (
            "Test alert from /settings/maintenance.\n\n"
            "Traceback (most recent call last):\n"
            "  File \".../sync.py\", line 99, in main\n"
            "    raise RuntimeError('synthetic test failure — no real error')\n"
            "RuntimeError: synthetic test failure — no real error"
        ),
        "duration_ms": 1234,
        "started_at": now.isoformat(),
    }
    suggested = derive_suggested_fix(synthetic["error"])
    payload = _build_payload(synthetic, suggested_fix=suggested, now=now)
    sub = {
        "id": sub_id, "url": url, "secret": secret, "name": name,
        "channel_type": channel_type or "generic",
        "channel_config": channel_config or {},
    }
    delivered = 1 if _dispatch_to_subscription(sub, payload) else 0
    return {"delivered": delivered, "skipped": 1 - delivered}
