"""
NousViz Alert Runner

Checks all enabled alerts and fires notifications when conditions are met.
Queries the core Postgres DB.

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
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

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


def query_postgres(pg, sql: str, params: dict) -> list[tuple]:
    """Execute a read-only SELECT on Postgres. Returns list of row tuples."""
    cur = pg.cursor()
    # Convert {key:Type} placeholders to %(key)s for psycopg2
    converted = re.sub(r"\{(\w+):[^}]+\}", r"%(\1)s", sql)
    cur.execute(converted, params)
    return cur.fetchall()


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


# ── Period SQL helpers ─────────────────────────────────────────────────────

def period_filter_pg(check_period: str) -> str:
    """Postgres WHERE clause fragment for the check period."""
    return {
        "today":              "date = current_date",
        "yesterday":          "date = current_date - 1",
        "today_or_yesterday": "date IN (current_date, current_date - 1)",
        "this_week":          "date >= date_trunc('week', current_date)",
        "rolling_7d":         "date >= current_date - 7",
    }.get(check_period, "date = current_date - 1")


def period_label(check_period: str) -> str:
    return {
        "today":              "today",
        "yesterday":          "yesterday",
        "today_or_yesterday": "today or yesterday",
        "this_week":          "this week",
        "rolling_7d":         "last 7 days",
    }.get(check_period, check_period)


# ── SQL builder ────────────────────────────────────────────────────────────

# S103: allowlist/regex for all identifier fields. Previously these were
# interpolated into f-string SQL without validation — an admin who could
# create an alert rule could inject arbitrary SQL that ran in the worker.
# Now every identifier is validated before it touches the SQL template.
_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]{0,63}$")
_ALLOWED_AGGS = frozenset({"sum", "avg", "count", "min", "max"})


def _validate_ident(name: str, value: str) -> None:
    """Raise ValueError if `value` is not a safe SQL identifier."""
    if not value or not _SAFE_IDENT.match(value):
        raise ValueError(f"Invalid identifier for {name!r}: {value!r}")


def build_check_sql(alert: dict) -> tuple[str, dict]:
    """Build Postgres SQL for the alert condition."""
    dataset      = alert["dataset"]
    metric       = alert["metric"]
    agg          = alert.get("aggregation", "sum")
    condition    = alert.get("condition_type", "absolute_above")
    check_period = alert.get("check_period", "yesterday")
    group_by     = alert.get("group_by")
    filters      = alert.get("scope_filters", {})

    # S103: validate all identifier fields before any SQL is composed.
    # `dataset`, `metric`, `group_by` (optional) must be plain identifiers;
    # `agg` must be in the aggregate function allowlist.
    _validate_ident("dataset", dataset)
    _validate_ident("metric", metric)
    if group_by:
        _validate_ident("group_by", group_by)
    if agg not in _ALLOWED_AGGS:
        raise ValueError(
            f"Invalid aggregation {agg!r}. Allowed: {sorted(_ALLOWED_AGGS)}"
        )

    # `min_baseline` is interpolated as a literal number — validate it's numeric.
    min_baseline = alert.get("min_baseline", 0)
    try:
        float(min_baseline)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid min_baseline {min_baseline!r} (must be numeric)")

    period = period_filter_pg(check_period)

    # Build optional WHERE filters using parameterized placeholders.
    # Column names are validated — only alphanumeric/underscore allowed.
    extra_where = ""
    query_params: dict = {}
    if filters:
        clauses = []
        for k, v in filters.items():
            if not v:
                continue
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", k):
                continue
            param_name = f"filter_{k}"
            clauses.append(f"{k} = %({param_name})s")
            query_params[param_name] = str(v)
        if clauses:
            extra_where = " AND " + " AND ".join(clauses)

    if condition in ("threshold_drop", "threshold_rise"):
        compare = alert.get("compare_to", "7d_avg")
        days = int(compare.replace("d_avg", "")) if "d_avg" in compare else 7

        if group_by:
            return f"""
                SELECT
                    {group_by} AS group_name,
                    {agg}({metric}) FILTER (WHERE {period}) AS current_value,
                    COALESCE({agg}({metric}) FILTER (WHERE date >= current_date - {days} AND NOT ({period})), 0)
                        / GREATEST({days} - 1, 1) AS baseline
                FROM {dataset}
                WHERE date >= current_date - {days}{extra_where}
                  AND {group_by} IS NOT NULL AND {group_by} != ''
                GROUP BY group_name
                HAVING COALESCE({agg}({metric}) FILTER (WHERE date >= current_date - {days} AND NOT ({period})), 0)
                        / GREATEST({days} - 1, 1) > {alert.get('min_baseline', 0)}
                ORDER BY current_value DESC
                LIMIT 100
            """, query_params
        return f"""
            SELECT
                {agg}({metric}) FILTER (WHERE {period}) AS current_value,
                COALESCE({agg}({metric}) FILTER (WHERE date >= current_date - {days} AND NOT ({period})), 0)
                    / GREATEST({days} - 1, 1) AS baseline
            FROM {dataset}
            WHERE date >= current_date - {days}{extra_where}
        """, query_params

    # Absolute threshold / zero check
    if group_by:
        return f"""
            SELECT
                {group_by} AS group_name,
                {agg}({metric}) AS current_value
            FROM {dataset}
            WHERE {period}{extra_where}
              AND {group_by} IS NOT NULL AND {group_by} != ''
            GROUP BY group_name
            ORDER BY current_value DESC
            LIMIT 100
        """, query_params
    return f"""
        SELECT {agg}({metric}) AS current_value
        FROM {dataset}
        WHERE {period}{extra_where}
    """, query_params


# ── Condition evaluator ────────────────────────────────────────────────────

def evaluate_row(alert: dict, current: float, baseline: float = 0.0) -> tuple[bool, float]:
    """Returns (triggered, change_pct_or_value)."""
    condition = alert.get("condition_type", "absolute_above")
    threshold = alert.get("threshold", 0)

    if condition == "threshold_drop":
        if baseline > 0:
            change = ((current - baseline) / baseline) * 100
            return change <= threshold, change
        return False, 0.0

    if condition == "threshold_rise":
        if baseline > 0:
            change = ((current - baseline) / baseline) * 100
            return change >= threshold, change
        return False, 0.0

    if condition == "absolute_above":
        return current > threshold, current

    if condition == "absolute_below":
        return current < threshold, current

    if condition == "zero_check":
        return current == 0 and baseline > 0, current

    return False, current


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
    import hmac as _hmac
    import hashlib as _hl
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = _hmac.new(secret.encode(), payload, _hl.sha256).hexdigest()
        headers["X-Webhook-Signature"] = sig
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

def run_alert(alert: dict, pg, dry_run: bool = False) -> bool:
    """Check one alert. Returns True if it fired."""
    label = alert["label"]

    if not alert.get("enabled", True):
        logger.debug(f"Skipping disabled alert: {label}")
        return False

    if not dry_run and is_on_cooldown(alert, pg):
        logger.info(f"On cooldown: {label}")
        return False

    sql, query_params = build_check_sql(alert)
    logger.debug(f"Alert SQL for '{label}':\n{sql.strip()}")

    try:
        rows = query_postgres(pg, sql, query_params)
    except Exception as e:
        logger.error(f"Alert '{label}' query failed: {e}")
        return False

    if not rows:
        logger.info(f"No data: {label}")
        return False

    condition = alert.get("condition_type", "absolute_above")
    group_by = alert.get("group_by")
    triggered_rows = []

    for row in rows:
        if group_by:
            group_name = row[0]
            current = float(row[1]) if row[1] is not None else 0.0
            baseline = float(row[2]) if len(row) > 2 and row[2] is not None else 0.0
        else:
            group_name = "Total"
            current = float(row[0]) if row[0] is not None else 0.0
            baseline = float(row[1]) if len(row) > 1 and row[1] is not None else 0.0

        fired, value = evaluate_row(alert, current, baseline)
        if fired:
            triggered_rows.append({
                "group": group_name,
                "current_value": round(current, 4),
                "baseline": round(baseline, 4),
                "change_pct": round(((current - baseline) / baseline * 100), 1) if baseline > 0 and condition in ("threshold_drop", "threshold_rise") else None,
            })

    if not triggered_rows:
        logger.info(f"No trigger: {label} — condition not met")
        return False

    period = period_label(alert.get("check_period", "yesterday"))
    logger.info(f"TRIGGERED: {label} — {len(triggered_rows)} row(s) for {period}")

    trigger_data = {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "check_period": alert.get("check_period", "yesterday"),
        "condition_type": condition,
        "threshold": alert.get("threshold"),
        "triggered_rows": triggered_rows,
        "sql": sql.strip(),
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
