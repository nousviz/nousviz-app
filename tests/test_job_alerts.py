"""Tests for B284 (v0.9.11.23) — per-job-run failure alert bridge.

Covers:
  - derive_suggested_fix matches the documented patterns + falls back
  - on_status filter rejects non-alertable statuses
  - plugin_id validator refuses garbage
  - process_run_failure routing (plugin filter, wildcard, status filter)
  - per-subscription failure isolation
  - webhook payload shape (text + alert_type + suggested_fix + HMAC delegation)
  - shared webhook_dispatch.post_webhook is what the bridge calls
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TS = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


# ── derive_suggested_fix ────────────────────────────────────────────


def test_derive_suggested_fix_db_connection():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    msg = "psycopg2.OperationalError: could not connect to server: connection refused"
    assert "Postgres connection" in derive_suggested_fix(msg)


def test_derive_suggested_fix_oauth():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    for msg in [
        "Missing OAuth credentials in vault",
        "{'error': 'invalid_grant'}",
        "401 Unauthorized: token expired",
    ]:
        assert "OAuth" in derive_suggested_fix(msg) or "Re-authorize" in derive_suggested_fix(msg)


def test_derive_suggested_fix_upstream_http():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    for msg in [
        "requests.exceptions.HTTPError: 502 Bad Gateway",
        "ConnectionError: max retries exceeded",
        "RemoteDisconnected: server closed connection",
    ]:
        assert "Upstream" in derive_suggested_fix(msg)


def test_derive_suggested_fix_schema_change():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    for msg in [
        "KeyError: 'new_column_introduced_upstream'",
        "AttributeError: 'NoneType' object has no attribute 'get'",
        "json.decoder.JSONDecodeError: Expecting value: line 1 column 1",
    ]:
        assert "schema change" in derive_suggested_fix(msg).lower()


def test_derive_suggested_fix_integrity():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    msg = "psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint"
    assert "Database constraint" in derive_suggested_fix(msg)


def test_derive_suggested_fix_oom():
    from apps.api.src.services.job_alerts import derive_suggested_fix
    for msg in [
        "MemoryError",
        "Process killed",
        "Worker received signal 9",
    ]:
        assert "memory" in derive_suggested_fix(msg).lower()


def test_derive_suggested_fix_default():
    from apps.api.src.services.job_alerts import derive_suggested_fix, DEFAULT_SUGGESTION
    # Empty / unknown errors fall back to the default.
    assert derive_suggested_fix(None) == DEFAULT_SUGGESTION
    assert derive_suggested_fix("") == DEFAULT_SUGGESTION
    assert derive_suggested_fix("Some completely unrecognised error") == DEFAULT_SUGGESTION


def test_derive_suggested_fix_first_match_wins():
    """When multiple patterns could match, the first listed wins.

    Pin: IntegrityError comes before OperationalError in the ordered
    list, so a UniqueViolation that incidentally references
    `OperationalError` in the surrounding traceback resolves to the
    constraint suggestion, not the connection one.
    """
    from apps.api.src.services.job_alerts import derive_suggested_fix
    msg = (
        "Traceback (most recent call last):\n"
        "  File 'sync.py', line 99, in main\n"
        "    raise psycopg2.errors.UniqueViolation('dup row')\n"
        "Note: this is NOT an OperationalError despite the surrounding text"
    )
    assert "Database constraint" in derive_suggested_fix(msg)


# ── Validators ──────────────────────────────────────────────────────


def test_validate_on_status_rejects_unknown():
    from apps.api.src.services.job_alerts import _validate_on_status
    raised = False
    try:
        _validate_on_status(["error", "success"])
    except ValueError:
        raised = True
    assert raised, "success is deliberately not alertable"


def test_validate_on_status_rejects_empty():
    from apps.api.src.services.job_alerts import _validate_on_status
    raised = False
    try:
        _validate_on_status([])
    except ValueError:
        raised = True
    assert raised


def test_validate_on_status_dedupes():
    from apps.api.src.services.job_alerts import _validate_on_status
    out = _validate_on_status(["error", "error", "timeout"])
    assert out == ["error", "timeout"]


def test_validate_plugin_id_accepts_wildcard_and_slugs():
    from apps.api.src.services.job_alerts import _validate_plugin_id
    assert _validate_plugin_id("*") == "*"
    assert _validate_plugin_id("example-customers") == "example-customers"
    assert _validate_plugin_id("a") == "a"


def test_validate_plugin_id_rejects_garbage():
    from apps.api.src.services.job_alerts import _validate_plugin_id
    for bad in ["", " ", "sync:foo", "a; DROP TABLE x;", "1starts-with-digit"]:
        raised = False
        try:
            _validate_plugin_id(bad)
        except ValueError:
            raised = True
        assert raised, f"expected rejection for {bad!r}"


# ── process_run_failure routing ─────────────────────────────────────


def _install_fake(monkeypatch, *, subs: list[dict], capture: list, fail_urls=None):
    """Patch the bridge to use an in-memory subscription list +
    capture all POSTs to a list. fail_urls are URLs that simulate a
    delivery error."""
    from apps.api.src.services import job_alerts as bridge
    fail_urls = fail_urls or set()

    def fake_load(plugin_id, status):
        return [
            {**s, "plugin_id_filter": s["plugin_id"]}
            for s in subs
            if (s["plugin_id"] == "*" or s["plugin_id"] == plugin_id)
            and status in s.get("on_status", [])
            and s.get("enabled", True)
        ]

    monkeypatch.setattr(bridge, "_load_matching_subscriptions", fake_load)

    def fake_post(url, secret, body):
        if url in fail_urls:
            raise RuntimeError(f"simulated failure for {url}")

    # The bridge imports post_webhook from .webhook_dispatch inside
    # _dispatch_to_subscription; patch the module-level reference.
    from apps.api.src.services import webhook_dispatch
    monkeypatch.setattr(webhook_dispatch, "post_webhook",
                        lambda u, s, b: capture.append((u, s, b)) or fake_post(u, s, b))

    return bridge


def test_no_matching_subscriptions_no_op(monkeypatch):
    monkeypatch.delenv("JOB_ALERT_EMAIL_TO", raising=False)
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[], capture=captured)
    out = bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert out == {"matched": 0, "delivered": 0, "failed": 0, "emailed": 0}
    assert captured == []


def test_plugin_filter_specific_match(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "foo", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    # Run for plugin foo → fires.
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert len(captured) == 1


def test_plugin_filter_specific_no_match_other_plugin(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "foo", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:bar", "status": "error", "error": "boom",
    }, ts=TS)
    assert captured == []


def test_wildcard_plugin_matches_any(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    for plugin in ["foo", "bar", "baz-quux"]:
        bridge.process_run_failure({
            "id": 1, "job_id": f"sync:{plugin}", "status": "error", "error": "boom",
        }, ts=TS)
    assert len(captured) == 3


def test_status_filter_skips_non_matching(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],  # only error
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    # timeout status is not in on_status → skipped
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "timeout", "error": "slow",
    }, ts=TS)
    assert captured == []


def test_disabled_subscription_skipped(monkeypatch):
    """Disabled subscriptions should be filtered out by _load_matching_subscriptions."""
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": False},
    ], capture=captured)
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert captured == []


def test_multiple_subscriptions_all_fire(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],
         "url": "http://a/1", "secret": "k", "name": "a", "enabled": True},
        {"id": "s2", "plugin_id": "foo", "on_status": ["error"],
         "url": "http://b/1", "secret": "k", "name": "b", "enabled": True},
    ], capture=captured)
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert len(captured) == 2  # both wildcard and specific fire


def test_one_failing_webhook_doesnt_break_others(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s-good", "plugin_id": "*", "on_status": ["error"],
         "url": "http://good/1", "secret": "k", "name": "good", "enabled": True},
        {"id": "s-bad", "plugin_id": "*", "on_status": ["error"],
         "url": "http://bad/1", "secret": "k", "name": "bad", "enabled": True},
    ], capture=captured, fail_urls={"http://bad/1"})
    out = bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert out["matched"] == 2
    assert out["delivered"] == 1
    assert out["failed"] == 1


# ── Payload shape ───────────────────────────────────────────────────


def test_payload_includes_text_alert_type_and_suggested_fix(monkeypatch):
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    bridge.process_run_failure({
        "id": 4321, "job_id": "sync:quickbooks", "status": "error",
        "error": "Missing OAuth credentials in vault",
    }, ts=TS)
    assert len(captured) == 1
    import json
    _, _, body = captured[0]
    payload = json.loads(body)
    assert payload["alert_type"] == "job_run_failure"
    assert payload["plugin_id"] == "quickbooks"
    assert payload["run_id"] == 4321
    assert payload["status"] == "error"
    assert payload["fired_at"] == TS.isoformat()
    assert "text" in payload, "Slack-compatible top-level text required"
    assert "OAuth" in payload["suggested_fix"] or "Re-authorize" in payload["suggested_fix"]
    assert "logs_url" in payload
    assert "dashboard_url" in payload


def test_skips_non_alertable_status(monkeypatch):
    """status='success' / 'queued' / 'running' should never trigger
    even if a subscription somehow had them in on_status."""
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error", "timeout", "cancelled"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    for status in ["success", "running", "queued", "skipped"]:
        bridge.process_run_failure({
            "id": 1, "job_id": "sync:foo", "status": status, "error": None,
        }, ts=TS)
    assert captured == []


def test_skips_non_sync_job_ids(monkeypatch):
    """Hook jobs ('hook:plugin:hookname') aren't covered by B284 v1."""
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "*", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    bridge.process_run_failure({
        "id": 1, "job_id": "hook:plugin:on_install", "status": "error", "error": "boom",
    }, ts=TS)
    assert captured == []


# ── Refactor smoke: shared dispatcher ──────────────────────────────


def test_diagnostic_alerts_uses_shared_dispatcher():
    """The B274 refactor (B284 v0.9.11.23) routed
    diagnostic_alerts._post_webhook through the shared
    webhook_dispatch.post_webhook helper. Pin that so a future
    refactor can't silently re-introduce the duplicate POST helper."""
    import importlib
    bridge = importlib.import_module("apps.api.src.services.diagnostic_alerts")
    src = (Path(REPO_ROOT) / "apps/api/src/services/diagnostic_alerts.py").read_text()
    assert "from .webhook_dispatch import post_webhook" in src, (
        "diagnostic_alerts._post_webhook should delegate to "
        "webhook_dispatch.post_webhook (B284 refactor)"
    )
    # And the shared module has the function.
    wd = importlib.import_module("apps.api.src.services.webhook_dispatch")
    assert callable(wd.post_webhook)


# ── Operator email (JOB_ALERT_EMAIL_TO) ─────────────────────────────


def _install_fake_email(monkeypatch, *, configured=True, fail_to=()):
    from apps.api.src.services import email as email_mod
    sent: list = []

    def fake_send(to, subject, html, plain):
        sent.append({"to": to, "subject": subject, "plain": plain})
        return (False, "simulated") if to in fail_to else (True, "")

    monkeypatch.setattr(email_mod, "_send", fake_send)
    monkeypatch.setattr(email_mod, "is_configured", lambda: configured)
    return sent


def test_validate_on_status_accepts_missed():
    from apps.api.src.services.job_alerts import _validate_on_status
    assert _validate_on_status(["error", "missed"]) == ["error", "missed"]


def test_email_sent_without_any_subscription(monkeypatch):
    """Email is operator-level: it must fire on an install with no
    webhooks plugin and no subscriptions."""
    monkeypatch.setenv("JOB_ALERT_EMAIL_TO", "a@example.com, b@example.com")
    bridge = _install_fake(monkeypatch, subs=[], capture=[])
    sent = _install_fake_email(monkeypatch)
    out = bridge.process_run_failure({
        "id": 29, "job_id": "sync:foo", "status": "error",
        "error": "Integrity check failed: Recorded SHA: f662c0d",
    }, ts=TS)
    assert out["emailed"] == 2
    assert [m["to"] for m in sent] == ["a@example.com", "b@example.com"]
    assert "sync:foo error" in sent[0]["subject"]
    assert "Integrity check failed" in sent[0]["plain"]


def test_email_and_webhook_both_fire(monkeypatch):
    monkeypatch.setenv("JOB_ALERT_EMAIL_TO", "a@example.com")
    captured: list = []
    bridge = _install_fake(monkeypatch, subs=[
        {"id": "s1", "plugin_id": "foo", "on_status": ["error"],
         "url": "http://h/1", "secret": "k", "name": "n1", "enabled": True},
    ], capture=captured)
    sent = _install_fake_email(monkeypatch)
    out = bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert out["delivered"] == 1 and out["emailed"] == 1
    assert len(captured) == 1 and len(sent) == 1


def test_email_skipped_when_smtp_unconfigured(monkeypatch):
    monkeypatch.setenv("JOB_ALERT_EMAIL_TO", "a@example.com")
    bridge = _install_fake(monkeypatch, subs=[], capture=[])
    sent = _install_fake_email(monkeypatch, configured=False)
    out = bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert out["emailed"] == 0 and sent == []


def test_one_failing_email_doesnt_stop_others(monkeypatch):
    monkeypatch.setenv("JOB_ALERT_EMAIL_TO", "bad@example.com,good@example.com")
    bridge = _install_fake(monkeypatch, subs=[], capture=[])
    sent = _install_fake_email(monkeypatch, fail_to={"bad@example.com"})
    out = bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "error", "error": "boom",
    }, ts=TS)
    assert out["emailed"] == 1 and len(sent) == 2


def test_email_not_sent_for_success(monkeypatch):
    monkeypatch.setenv("JOB_ALERT_EMAIL_TO", "a@example.com")
    bridge = _install_fake(monkeypatch, subs=[], capture=[])
    sent = _install_fake_email(monkeypatch)
    bridge.process_run_failure({
        "id": 1, "job_id": "sync:foo", "status": "success", "error": None,
    }, ts=TS)
    assert sent == []


# ── Missed-run watchdog (needs Postgres; skipped without one) ───────
#
# The decision is SQL over job_runs, so it is tested against a real
# database rather than a fake cursor. Each test uses its own job id and
# deletes its rows afterwards.

import uuid  # noqa: E402

import pytest  # noqa: E402

FIRE = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 1, 10, 15, 0, 0, tzinfo=timezone.utc)   # fire + 5h
CRON = "0 10 * * *"


@pytest.fixture
def watchdog(monkeypatch):
    from apps.api.src.services import job_alerts as bridge
    try:
        with bridge.get_pg_conn() as conn:
            conn.cursor().execute("SELECT 1 FROM job_runs LIMIT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no Postgres with job_runs: {exc}")
    monkeypatch.delenv("JOB_ALERT_MISSED_GRACE_MINUTES", raising=False)
    alerts: list = []
    monkeypatch.setattr(bridge, "process_run_failure",
                        lambda run, ts=None: alerts.append(run))
    plugin = f"zz-watchdog-{uuid.uuid4().hex[:8]}"
    job_id = f"sync:{plugin}"

    def add_run(status, started, completed=None):
        with bridge.get_pg_conn() as conn:
            conn.cursor().execute(
                "INSERT INTO job_runs (job_id, status, source, started_at, completed_at) "
                "VALUES (%s, %s, 'cron', %s, %s)",
                (job_id, status, started, completed))

    def check(now=NOW):
        return bridge._check_one(plugin, CRON, now=now)

    def rows():
        with bridge.get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, started_at FROM job_runs "
                        "WHERE job_id = %s AND status = 'missed'", (job_id,))
            return cur.fetchall()

    yield {"add": add_run, "check": check, "rows": rows, "alerts": alerts}
    with bridge.get_pg_conn() as conn:
        conn.cursor().execute("DELETE FROM job_runs WHERE job_id = %s", (job_id,))


YESTERDAY = FIRE - timedelta(days=1, minutes=-1)


def test_watchdog_skips_plugin_with_no_history(watchdog):
    assert watchdog["check"]() is None
    assert watchdog["alerts"] == [] and watchdog["rows"]() == []


def test_watchdog_records_and_alerts_once_for_missed_fire(watchdog):
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    run = watchdog["check"]()
    assert run and run["status"] == "missed"
    assert [a["status"] for a in watchdog["alerts"]] == ["missed"]
    recorded = watchdog["rows"]()
    assert len(recorded) == 1 and recorded[0][1] == FIRE
    # Called again (next scheduler poll, or a second scheduler): no repeat.
    assert watchdog["check"]() is None
    assert len(watchdog["alerts"]) == 1 and len(watchdog["rows"]()) == 1


def test_watchdog_quiet_when_fire_ran(watchdog):
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    watchdog["add"]("success", FIRE + timedelta(seconds=30), FIRE + timedelta(minutes=2))
    assert watchdog["check"]() is None


def test_watchdog_quiet_when_fire_failed(watchdog):
    """A failed run already alerted through _finalize_run; the watchdog
    must not add a second alert for the same fire."""
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    watchdog["add"]("error", FIRE + timedelta(seconds=20), FIRE + timedelta(seconds=21))
    assert watchdog["check"]() is None


def test_watchdog_flags_run_stuck_in_queue(watchdog):
    """Worker down: the scheduler enqueued the run but nothing claimed it."""
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    watchdog["add"]("queued", FIRE + timedelta(seconds=5))
    assert watchdog["check"]()["status"] == "missed"


def test_watchdog_quiet_while_previous_run_in_flight(watchdog):
    """The scheduler skips a fire while a run is active, so a long run
    that spans the fire is not a miss."""
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    watchdog["add"]("running", FIRE - timedelta(minutes=30))
    assert watchdog["check"]() is None


def test_watchdog_quiet_inside_grace_period(watchdog):
    """At fire + 1h with a 2h grace, today's fire is not due yet, so the
    fire under test is yesterday's, which ran."""
    # History before yesterday's fire, so the no-history skip is not what
    # keeps this quiet.
    watchdog["add"]("success", YESTERDAY - timedelta(days=1), YESTERDAY - timedelta(days=1))
    watchdog["add"]("success", YESTERDAY, YESTERDAY + timedelta(minutes=2))
    assert watchdog["check"](now=FIRE + timedelta(hours=1)) is None
    assert watchdog["check"]()["status"] == "missed"   # and at +5h, today's is
