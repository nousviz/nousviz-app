"""
NousViz Alert Runner

Checks all enabled alerts and fires notifications when conditions are met.
Alert definitions live in core Postgres; the data each alert reads can be in
Postgres, ClickHouse or MySQL (P230). Evaluation is shared with the API's
Test and Preview through apps/api/src/alert_engine.py.

Run on a cron or manually:

  # Check all alerts now
  python3 apps/worker/src/run_alerts.py

  # Dry run — shows what would fire without sending notifications
  python3 apps/worker/src/run_alerts.py --dry-run

  # Check a specific alert by ID
  python3 apps/worker/src/run_alerts.py --alert-id <uuid>

Cron (every hour):
  0 * * * * cd /path/to/nousviz && .venv/bin/python3 apps/worker/src/run_alerts.py >> logs/alerts.log 2>&1
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# P230: the evaluator is shared with the API (Test / Preview).
_REPO = str(Path(__file__).resolve().parents[3])
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
from apps.api.src.alert_engine import PERIODS, evaluate_alert  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("nousviz.alerts")

# ── Connections ───────────────────────────────────────────────────────────

def get_pg():
    # S108: POSTGRES_PASSWORD must be set — no default.
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD environment variable is required. "
            "Set it in .env before running the alert worker."
        )
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "nousviz"),
        user=os.environ.get("POSTGRES_USER", "nousviz"),
        password=password,
        sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
    )


# ── Load alerts from Postgres ──────────────────────────────────────────────

def load_alerts(pg) -> list[dict]:
    """Load alert definitions from the alert_rules table."""
    cur = pg.cursor()
    cur.execute("SELECT * FROM alert_rules ORDER BY created_at")
    cols = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        for k in ("created_at", "updated_at", "last_triggered"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
        # Ensure id is string for compatibility
        r["id"] = str(r["id"])
        rows.append(r)
    return rows


# ── Labels ─────────────────────────────────────────────────────────────────

def period_label(check_period: str) -> str:
    return PERIODS.get(check_period, check_period)


# ── Cooldown check ─────────────────────────────────────────────────────────

def is_on_cooldown(alert: dict, pg: psycopg2.extensions.connection) -> bool:
    """Return True if this alert fired within its cooldown window."""
    cooldown_hours = alert.get("cooldown_hours", 24)
    cur = pg.cursor()
    cur.execute("""
        SELECT triggered_at FROM alert_triggers
        WHERE alert_id = %s
        ORDER BY triggered_at DESC LIMIT 1
    """, (alert["id"],))
    row = cur.fetchone()
    if not row:
        return False
    last = row[0]
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() < cooldown_hours * 3600


# ── Record trigger ─────────────────────────────────────────────────────────

def record_trigger(alert: dict, trigger_data: dict, pg: psycopg2.extensions.connection) -> str:
    trigger_id = str(uuid.uuid4())
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO alert_triggers (id, alert_id, alert_name, plugin_id, trigger_data)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        trigger_id, alert["id"], alert["label"], alert.get("plugin_id", ""),
        json.dumps(trigger_data),
    ))
    # Update last_triggered and trigger_count in alert_rules
    cur.execute("""
        UPDATE alert_rules SET last_triggered = now(), trigger_count = trigger_count + 1
        WHERE id = %s
    """, (alert["id"],))
    pg.commit()
    return trigger_id


# ── Notifications ──────────────────────────────────────────────────────────

def send_notification(alert: dict, trigger_data: dict, dry_run: bool = False) -> None:
    channels = alert.get("notify_channels", ["log"])
    label = alert["label"]
    period = period_label(alert.get("check_period", "yesterday"))
    triggered = trigger_data.get("triggered_rows", [])

    lines = [f"ALERT: {label}"]
    for row in triggered[:5]:
        group = row.get("group", "Total")
        value = row.get("current_value", 0)
        change = row.get("change_pct")
        if change is not None:
            lines.append(f"  {group}: {value:,.2f} ({change:+.1f}%)")
        else:
            lines.append(f"  {group}: {value:,.2f}")
    if len(triggered) > 5:
        lines.append(f"  ... and {len(triggered) - 5} more")

    message = "\n".join(lines)

    if dry_run:
        logger.info(f"[DRY RUN] Would send to {channels}:\n{message}")
        return

    for channel in channels:
        if channel == "log":
            logger.info(f"NOTIFICATION → {channel}:\n{message}")
        elif channel == "telegram":
            _send_telegram(message)
        elif channel == "slack":
            _send_slack(message)
        elif channel == "email":
            _send_email(alert, message)
        elif channel.startswith("webhook:"):
            _send_webhook_named(channel[8:], alert, trigger_data, message)


def _send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing)")
        return
    import urllib.request
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def _send_slack(message: str) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        logger.warning("Slack not configured (SLACK_WEBHOOK_URL missing)")
        return
    import urllib.request
    data = json.dumps({"text": message}).encode()
    req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        logger.info("Slack notification sent")
    except Exception as e:
        logger.error(f"Slack send failed: {e}")


def _build_webhook_payload(alert: dict, trigger_data: dict, message: str) -> bytes:
    return json.dumps({
        "alert_name": alert.get("label", alert.get("name")),
        "alert_id": str(alert.get("id", "")),
        "plugin_id": alert.get("plugin_id"),
        "fired_at": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "triggered_rows": trigger_data.get("triggered_rows", [])[:10],
    }).encode()


def _post_webhook(url: str, payload: bytes, secret: str | None = None) -> None:
    import urllib.request
    from apps.api.src.services.webhook_dispatch import sign_headers
    headers = {"Content-Type": "application/json"}
    headers.update(sign_headers(secret, payload))  # B346: V1 + timestamp + V2
    req = urllib.request.Request(url, data=payload, headers=headers)
    urllib.request.urlopen(req, timeout=10)


def _send_webhook_named(endpoint_name: str, alert: dict, trigger_data: dict, message: str) -> None:
    try:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "nousviz"),
            user=os.environ.get("POSTGRES_USER", "nousviz"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            SELECT url, secret, is_active FROM webhook_endpoints
            WHERE name = %s AND direction = 'outbound'
        """, (endpoint_name,))
        row = cur.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"Could not look up webhook '{endpoint_name}': {e}")
        return

    if not row:
        logger.warning(f"Outbound webhook '{endpoint_name}' not found")
        return
    url, secret, is_active = row
    if not is_active:
        logger.info(f"Outbound webhook '{endpoint_name}' is disabled, skipping")
        return
    if not url:
        logger.warning(f"Outbound webhook '{endpoint_name}' has no URL configured")
        return

    payload = _build_webhook_payload(alert, trigger_data, message)
    try:
        _post_webhook(url, payload, secret)
        logger.info(f"Webhook notification sent to '{endpoint_name}' ({url})")
    except Exception as e:
        logger.error(f"Webhook send to '{endpoint_name}' failed: {e}")


def _send_email(alert: dict, message: str) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from apps.api.src.services.email import _send, is_configured
        if not is_configured():
            logger.warning("Email notification skipped — SMTP not configured")
            return
        label = alert.get("label", alert.get("name", "Alert"))
        plugin = alert.get("plugin_id", "unknown")
        subject = f"[NousViz] Alert fired: {label}"
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#16161d;border-radius:12px;">
  <h2 style="color:#f0f0f5;font-size:18px;margin:0 0 12px;">Alert: {label}</h2>
  <p style="color:#999;font-size:13px;margin:0 0 16px;">Plugin: {plugin}</p>
  <pre style="color:#e0e0e5;font-size:12px;background:#0c0c10;padding:12px;border-radius:8px;white-space:pre-wrap;">{message}</pre>
  <p style="color:#555;font-size:11px;margin:16px 0 0;">Sent by NousViz &middot; Self-hosted data intelligence</p>
</div>"""
        to = os.environ.get("SMTP_FROM_ADDRESS", "")
        if to:
            ok, err = _send(to, subject, html, message)
            if ok:
                logger.info(f"Email notification sent to {to}")
            else:
                logger.error(f"Email notification failed: {err}")
        else:
            logger.warning("Email notification skipped — no SMTP_FROM_ADDRESS configured")
    except Exception as e:
        logger.error(f"Email notification error: {e}")


# ── Main runner ────────────────────────────────────────────────────────────

def record_status(pg, alert_id: str, status: str, ev) -> None:
    """P230: the alert list shows each alert's last run, status and error."""
    try:
        cur = pg.cursor()
        cur.execute("""
            UPDATE alert_rules
               SET last_run_at = now(), last_status = %s, last_error = %s,
                   last_duration_ms = %s, last_rows_checked = %s
             WHERE id = %s
        """, (status, (ev.error or None) and ev.error[:500], ev.elapsed_ms, ev.rows_checked, alert_id))
        pg.commit()
    except Exception as e:  # noqa: BLE001 — migration 081 not applied yet
        pg.rollback()
        logger.debug(f"Could not record alert status: {e}")


def run_alert(alert: dict, pg, dry_run: bool = False) -> bool:
    """Check one alert. Returns True if it fired."""
    label = alert["label"]

    if not alert.get("enabled", True):
        logger.debug(f"Skipping disabled alert: {label}")
        return False

    if not dry_run and is_on_cooldown(alert, pg):
        logger.info(f"On cooldown: {label}")
        return False

    ev = evaluate_alert(alert, pg_cursor=pg.cursor())
    logger.debug(f"Alert SQL for '{label}' ({ev.engine}):\n{ev.sql.strip()}")

    if ev.status == "error":
        logger.error(f"Alert '{label}' could not be evaluated on {ev.engine}: {ev.error}")
        if not dry_run:
            record_status(pg, alert["id"], "error", ev)
        return False

    triggered_rows = [
        {k: r[k] for k in ("group", "current_value", "baseline", "change_pct")}
        for r in ev.fired_rows
    ]
    if not dry_run:
        record_status(pg, alert["id"], "fired" if triggered_rows else ev.status, ev)

    if ev.status == "no_data":
        logger.info(f"No data: {label}")
        return False
    if not triggered_rows:
        logger.info(f"No trigger: {label} — condition not met ({ev.rows_checked} group(s) checked)")
        return False

    period = period_label(alert.get("check_period", "yesterday"))
    logger.info(f"TRIGGERED: {label} — {len(triggered_rows)} row(s) for {period} on {ev.engine}")

    trigger_data = {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "check_period": alert.get("check_period", "yesterday"),
        "condition_type": alert.get("condition_type", "absolute_above"),
        "threshold": alert.get("threshold"),
        "triggered_rows": triggered_rows,
        "engine": ev.engine,
        "sql": ev.sql.strip(),
    }

    if not dry_run:
        record_trigger(alert, trigger_data, pg)

    send_notification(alert, trigger_data, dry_run=dry_run)
    return True


def main():
    parser = argparse.ArgumentParser(description="NousViz Alert Runner")
    parser.add_argument("--dry-run", action="store_true", help="Check conditions but don't record triggers or send notifications")
    parser.add_argument("--alert-id", type=str, help="Run a single alert by ID")
    parser.add_argument("--plugin-id", type=str, help="Run alerts for one plugin only")
    args = parser.parse_args()

    pg = get_pg()

    alerts = load_alerts(pg)
    if not alerts:
        logger.info("No alerts configured")
        pg.close()
        return

    if args.alert_id:
        alerts = [a for a in alerts if a["id"] == args.alert_id]
        if not alerts:
            logger.error(f"Alert not found: {args.alert_id}")
            sys.exit(1)

    if args.plugin_id:
        alerts = [a for a in alerts if a.get("plugin_id") == args.plugin_id]

    enabled = [a for a in alerts if a.get("enabled", True)]
    logger.info(f"Checking {len(enabled)} alert(s){' [DRY RUN]' if args.dry_run else ''}")

    import time as _t
    run_start = _t.time()
    fired = 0
    errors = 0
    for alert in enabled:
        try:
            if run_alert(alert, pg, dry_run=args.dry_run):
                fired += 1
        except Exception as e:
            errors += 1
            logger.error(f"Alert '{alert.get('label')}' failed: {e}", exc_info=True)

    duration_ms = int((_t.time() - run_start) * 1000)
    logger.info(f"Done — {fired}/{len(enabled)} alerts fired ({duration_ms}ms)")

    if not args.dry_run:
        try:
            cur = pg.cursor()
            cur.execute("""
                INSERT INTO job_runs (job_id, started_at, completed_at, status, duration_ms, source, details)
                VALUES ('alert-runner', %s, now(), %s, %s, 'alert_runner', %s)
            """, (
                datetime.fromtimestamp(run_start, tz=timezone.utc),
                "error" if errors > 0 else "success",
                duration_ms,
                json.dumps({"checked": len(enabled), "fired": fired, "errors": errors}),
            ))
            pg.commit()
        except Exception:
            pass

    pg.close()


if __name__ == "__main__":
    main()
