"""
run_scheduler.py — Manifest-driven sync scheduler (B147 / v0.9.3).

Polls plugin_registry for installed plugins, reads their sync.schedule
from plugin.yaml (with plugin_settings._sync_schedule overrides), and
enqueues job_runs rows on cron.

Companion to run_jobs.py:
  - Scheduler ENQUEUES (this file): writes status='queued' rows on cron
  - Worker DEQUEUES (run_jobs.py): claims and runs queued rows

Single instance. PM2 keeps it alive (autorestart=true). On crash, lost
poll cycles just delay enqueue by ~30s — no double-fires because the
30s last_enqueued_at window guards the enqueue.

Env: same as run_jobs.py — needs POSTGRES_PASSWORD via .env. No broker;
this is core infrastructure, not plugin code.

Concurrency: if two schedulers somehow run, both compute the same
next_fire_at; the UPDATE ... WHERE last_enqueued_at IS DISTINCT FROM
clause makes only one win the enqueue race. Idempotent.

Predicate semantics:
  schedule_active(plugin_id) = sync_schedule_registry has a row AND
  updated_at < 5 min ago. The scheduler refreshes updated_at on every
  poll (every 30s), so a healthy scheduler keeps the predicate true.
  If the scheduler is dead, predicate flips to false within 5 min —
  visible to operators via the setup checklist.
"""

from __future__ import annotations

import logging
import os
import random
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# Local .env load so we pick up POSTGRES_PASSWORD (run_jobs.py uses the same pattern).
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

import yaml  # noqa: E402

from apps.api.src.db import get_pg_conn  # noqa: E402
from apps.api.src.log_events import log_job_event  # noqa: E402

# croniter is required. Pinned in apps/api/requirements.txt to >=2.0,<3.0.
try:
    from croniter import croniter  # type: ignore
except ImportError as exc:  # pragma: no cover — caught at startup
    print(f"FATAL: croniter unavailable ({exc}). Run setup.sh.", file=sys.stderr)
    raise

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nousviz.scheduler")

INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"

SCHEDULER_ID = f"{socket.gethostname()}:{os.getpid()}"

# How often we walk plugin_registry. Short enough that operator changes
# (override save, plugin install/uninstall) take effect within tens of
# seconds. Long enough that DB/manifest reads aren't constant load.
POLL_INTERVAL_SEC = 30.0
POLL_JITTER_SEC = 5.0

# Idempotency window. After enqueueing for a fire-time, refuse to
# enqueue again until the wall clock has moved at least this far past
# last_enqueued_at. Catches scheduler-restart double-fires + two-scheduler
# races.
ENQUEUE_DEDUP_WINDOW_SEC = 30.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Plugin discovery ──────────────────────────────────────────────────


def _read_manifest_cron(plugin_id: str) -> Optional[str]:
    """Read sync.schedule from the installed plugin's manifest. Returns
    None if the plugin doesn't declare a schedule."""
    manifest_path = INSTALLED_DIR / plugin_id / "plugin.yaml"
    if not manifest_path.exists():
        return None
    try:
        meta = yaml.safe_load(manifest_path.read_text()) or {}
    except Exception as exc:
        logger.warning("manifest read failed for %s: %s", plugin_id, exc)
        return None
    sync = meta.get("sync") or {}
    cron = sync.get("schedule")
    if not cron or not isinstance(cron, str):
        return None
    return cron.strip()


def _read_override_cron(plugin_id: str) -> Optional[str]:
    """Read plugin_settings._sync_schedule.<plugin_id> override. Returns
    None if no override is set."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT value FROM plugin_settings
                WHERE plugin_id = %s AND key = '_sync_schedule'
                """,
                (plugin_id,),
            )
            row = cur.fetchone()
        if not row or row[0] is None:
            return None
        val = row[0]
        # JSONB: a stored string round-trips as a Python str
        if isinstance(val, str) and val.strip():
            return val.strip()
        return None
    except Exception as exc:
        logger.debug("override read failed for %s: %s", plugin_id, exc)
        return None


def _list_installed_plugins() -> list[str]:
    """Return slugs of installed plugins from plugin_registry."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT slug FROM plugin_registry
                WHERE installed_at IS NOT NULL
                ORDER BY slug
                """
            )
            return [r[0] for r in cur.fetchall()]
    except Exception as exc:
        logger.warning("plugin_registry read failed: %s", exc)
        return []


# ── Cron parsing & validation ─────────────────────────────────────────


def parse_cron(cron_str: str) -> bool:
    """Return True if cron_str is a valid 5-field cron expression."""
    try:
        croniter(cron_str, _now())
        return True
    except Exception:
        return False


def compute_next_fire(cron_str: str, after: datetime) -> Optional[datetime]:
    """Compute the next fire time for cron_str strictly after `after`.
    Returns None on invalid cron."""
    try:
        itr = croniter(cron_str, after)
        nxt = itr.get_next(datetime)
        # croniter returns naive datetimes if `after` is naive; we always
        # pass aware UTC so the output should be aware.
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        return nxt
    except Exception as exc:
        logger.warning("compute_next_fire failed for %r: %s", cron_str, exc)
        return None


def compute_prev_fire(cron_str: str, before: datetime) -> Optional[datetime]:
    """Compute the most recent fire time for cron_str at or before `before`.
    Returns None on invalid cron. Mirror of compute_next_fire used by the
    fresh-row anchor logic in _process_plugin (B183)."""
    try:
        itr = croniter(cron_str, before)
        prv = itr.get_prev(datetime)
        if prv.tzinfo is None:
            prv = prv.replace(tzinfo=timezone.utc)
        return prv
    except Exception as exc:
        logger.warning("compute_prev_fire failed for %r: %s", cron_str, exc)
        return None


# ── Registry I/O ──────────────────────────────────────────────────────


def _read_registry_row(plugin_id: str) -> Optional[dict]:
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT cron_expression, cron_source, next_fire_at,
                       last_enqueued_at, last_run_id, last_error
                FROM sync_schedule_registry WHERE plugin_id = %s
                """,
                (plugin_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "cron_expression": row[0],
            "cron_source": row[1],
            "next_fire_at": row[2],
            "last_enqueued_at": row[3],
            "last_run_id": row[4],
            "last_error": row[5],
        }
    except Exception as exc:
        logger.debug("registry read failed for %s: %s", plugin_id, exc)
        return None


def _upsert_registry(
    plugin_id: str,
    cron_expression: str,
    cron_source: str,
    next_fire_at: Optional[datetime],
    last_error: Optional[str],
) -> None:
    """Refresh the per-plugin registry row. Always touches updated_at.

    Does NOT modify last_enqueued_at / last_run_id — those are only set
    by _record_enqueue after a successful job_runs insert. The ON CONFLICT
    DO UPDATE clause therefore preserves last_enqueued_at across polls.
    Note: this means a fresh row inserted by this function starts with
    last_enqueued_at = NULL — _process_plugin's cold-state branch (B183)
    handles that case explicitly.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sync_schedule_registry (
                    plugin_id, cron_expression, cron_source,
                    next_fire_at, last_error, updated_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (plugin_id) DO UPDATE SET
                    cron_expression = EXCLUDED.cron_expression,
                    cron_source     = EXCLUDED.cron_source,
                    next_fire_at    = EXCLUDED.next_fire_at,
                    last_error      = EXCLUDED.last_error,
                    updated_at      = NOW()
                """,
                (plugin_id, cron_expression, cron_source, next_fire_at, last_error),
            )
    except Exception as exc:
        logger.warning("registry upsert failed for %s: %s", plugin_id, exc)


def _record_enqueue(plugin_id: str, run_id: int, fire_at: datetime) -> None:
    """Record that we successfully inserted a job_runs row for this
    plugin's fire-time. Subsequent polls within the dedup window won't
    re-enqueue."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE sync_schedule_registry
                SET last_enqueued_at = NOW(),
                    last_run_id = %s,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE plugin_id = %s
                """,
                (run_id, plugin_id),
            )
    except Exception as exc:
        logger.warning("record_enqueue failed for %s/%s: %s", plugin_id, run_id, exc)


def _delete_registry_row(plugin_id: str) -> None:
    """Remove a plugin's row when it's no longer installed."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM sync_schedule_registry WHERE plugin_id = %s",
                (plugin_id,),
            )
    except Exception as exc:
        logger.warning("registry delete failed for %s: %s", plugin_id, exc)


def _reap_uninstalled(installed_slugs: list[str]) -> int:
    """Delete registry rows for plugins not in `installed_slugs`. Returns
    count deleted."""
    if not installed_slugs:
        return 0
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM sync_schedule_registry
                WHERE plugin_id != ALL(%s::text[])
                RETURNING plugin_id
                """,
                (installed_slugs,),
            )
            return len(cur.fetchall())
    except Exception as exc:
        logger.warning("reap_uninstalled failed: %s", exc)
        return 0


# ── Enqueue ──────────────────────────────────────────────────────────


def _has_active_run(plugin_id: str) -> Optional[tuple[int, str]]:
    """B277 v0.9.11.17.1: state-based dedup for the scheduler.

    Returns (run_id, status) when a run for this plugin is currently
    in flight (queued / running / cancelling), else None.

    The pre-17.1 scheduler only debounced by ENQUEUE_DEDUP_WINDOW_SEC
    (30s) since the last enqueue. That guarded poll-iteration races
    but NOT the case where the prior run is still executing past the
    next cron boundary — letting the scheduler enqueue a second run
    that the worker would then run concurrently with the first.
    Mirrors the active-run guard in routes/sync.py:_enforce_concurrency.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, status FROM job_runs
                WHERE job_id = %s
                  AND status IN ('queued', 'running', 'cancelling')
                ORDER BY id DESC LIMIT 1
                """,
                (f"sync:{plugin_id}",),
            )
            row = cur.fetchone()
        if row:
            return int(row[0]), row[1]
    except Exception as exc:
        logger.warning("active-run check failed for %s: %s", plugin_id, exc)
        # Fail-open: if the check itself errored, fall through to
        # the existing time-window dedup. Worse to skip a real fire
        # because of a transient DB hiccup than to risk a duplicate.
    return None


def _enqueue_run(plugin_id: str, fire_at: datetime, cron: str, source: str) -> Optional[int]:
    """Insert a queued job_runs row for this plugin. Returns the new
    run_id, or None on failure (already logged).

    B184: job_id MUST be 'sync:<plugin_id>'. Worker's _run_job parses
    the prefix to dispatch sync vs hook runners — bare slug is rejected
    with 'Unsupported job_id shape'.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO job_runs (job_id, status, source, started_at, details)
                VALUES (%s, 'queued', 'cron', NOW(),
                        jsonb_build_object(
                            'scheduled_fire_at', %s::text,
                            'cron_expression',   %s,
                            'cron_source',       %s,
                            'scheduler_id',      %s
                        ))
                RETURNING id
                """,
                (f"sync:{plugin_id}", fire_at.isoformat(), cron, source, SCHEDULER_ID),
            )
            row = cur.fetchone()
        return int(row[0]) if row else None
    except Exception as exc:
        logger.error("enqueue failed for %s: %s", plugin_id, exc)
        return None


# ── Per-plugin pass ──────────────────────────────────────────────────


def _process_plugin(plugin_id: str) -> None:
    """One full pass for a single plugin: read crons, decide next fire,
    enqueue if due, refresh registry. Errors are confined to this plugin —
    they never break the scheduler's outer loop."""
    manifest_cron = _read_manifest_cron(plugin_id)
    override_cron = _read_override_cron(plugin_id)

    if not manifest_cron and not override_cron:
        # Plugin doesn't declare a schedule and operator hasn't set one.
        # Drop any stale registry row and skip.
        _delete_registry_row(plugin_id)
        return

    cron = override_cron or manifest_cron
    cron_source = "override" if override_cron else "manifest"

    if not parse_cron(cron):
        # Invalid cron — write the error to the registry so operators can
        # see it via the predicate / override UI, and skip the enqueue.
        _upsert_registry(
            plugin_id, cron, cron_source, None,
            last_error=f"Invalid cron expression: {cron}",
        )
        return

    now = _now()
    existing = _read_registry_row(plugin_id)
    last_enqueued_at: Optional[datetime] = (
        existing["last_enqueued_at"] if existing else None
    )

    # B183: anchor logic.
    #   - Warm state (last_enqueued_at non-NULL): anchor on the prior
    #     successful enqueue so we advance one slot per poll. Existing
    #     ENQUEUE_DEDUP_WINDOW_SEC guards double-fires.
    #   - Cold state (last_enqueued_at IS NULL — fresh install OR API
    #     deleted the row on override save/clear): anchor on the most
    #     recent past slot via compute_prev_fire, with a grace window so
    #     we only fire if we're at or just past a slot boundary.
    #     Mid-period polls wait for the upcoming slot. No back-firing of
    #     arbitrarily old missed slots.
    if last_enqueued_at:
        next_fire_at = compute_next_fire(cron, last_enqueued_at)
    else:
        prev_slot = compute_prev_fire(cron, now)
        grace_sec = POLL_INTERVAL_SEC + POLL_JITTER_SEC + 5
        if prev_slot is not None and (now - prev_slot).total_seconds() <= grace_sec:
            # We're at or just past a slot boundary — fire that slot.
            next_fire_at = prev_slot
        else:
            # Past the grace window for the prior slot — wait for the
            # next future slot instead.
            next_fire_at = compute_next_fire(cron, now)

    # Decide whether to enqueue THIS poll
    should_enqueue = (
        next_fire_at is not None
        and next_fire_at <= now
        and (
            last_enqueued_at is None
            or (now - last_enqueued_at).total_seconds() >= ENQUEUE_DEDUP_WINDOW_SEC
        )
    )

    if should_enqueue:
        # B277 v0.9.11.17.1: active-run guard. State-based, not just
        # time-window. If the prior run is still in flight (queued /
        # running / cancelling), skip the enqueue — the platform's
        # contract is one in-flight run per plugin at a time.
        active = _has_active_run(plugin_id)
        if active is not None:
            active_id, active_status = active
            log_job_event(
                "info",
                (
                    f"Scheduler skipped enqueue for {plugin_id}: "
                    f"prior run #{active_id} still {active_status}"
                ),
                {
                    "cron": cron,
                    "cron_source": cron_source,
                    "skipped_fire_at": next_fire_at.isoformat() if next_fire_at else None,
                    "active_run_id": active_id,
                    "active_status": active_status,
                    "reason": "active_run_in_flight",
                },
                source="scheduler",
                plugin_id=plugin_id,
            )
            # Don't update last_enqueued_at — the slot was skipped, not
            # consumed. Next poll will re-evaluate against current state.
        else:
            run_id = _enqueue_run(plugin_id, next_fire_at, cron, cron_source)
            if run_id:
                _record_enqueue(plugin_id, run_id, next_fire_at)
                log_job_event(
                    "info",
                    f"Scheduled sync queued for {plugin_id} (run {run_id})",
                    {
                        "cron": cron,
                        "cron_source": cron_source,
                        "fire_at": next_fire_at.isoformat(),
                    },
                    source="scheduler",
                    plugin_id=plugin_id,
                    run_id=run_id,
                )
                # Compute the *next* next_fire_at, so the registry shows the
                # following fire (not the one we just consumed).
                next_fire_at = compute_next_fire(cron, now)

    # Refresh registry. updated_at touches every poll → predicate stays alive.
    _upsert_registry(
        plugin_id, cron, cron_source, next_fire_at,
        last_error=None,
    )


# ── Outer loop ──────────────────────────────────────────────────────


_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info("scheduler received signal %s — shutting down", signum)
    _running = False


def main():
    import signal
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("scheduler starting (id=%s, poll=%ss)", SCHEDULER_ID, POLL_INTERVAL_SEC)

    while _running:
        loop_start = time.monotonic()
        try:
            installed = _list_installed_plugins()
            for slug in installed:
                if not _running:
                    break
                try:
                    _process_plugin(slug)
                except Exception as exc:
                    logger.warning("plugin pass failed for %s: %s", slug, exc, exc_info=True)
            reaped = _reap_uninstalled(installed)
            if reaped:
                logger.info("reaped %d uninstalled plugins from registry", reaped)
        except Exception as exc:
            logger.error("scheduler loop error: %s", exc, exc_info=True)

        # Sleep with jitter; check _running between sub-sleeps so SIGTERM
        # is responsive.
        elapsed = time.monotonic() - loop_start
        sleep_for = max(0.5, POLL_INTERVAL_SEC + random.uniform(0, POLL_JITTER_SEC) - elapsed)
        end_at = time.monotonic() + sleep_for
        while _running and time.monotonic() < end_at:
            time.sleep(min(1.0, end_at - time.monotonic()))

    logger.info("scheduler stopped")


if __name__ == "__main__":
    main()
