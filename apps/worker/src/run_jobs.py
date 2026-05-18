"""
run_jobs.py — Async job worker for NousViz plugin sync.

Polls the job_runs table for queued rows, claims them atomically via
FOR UPDATE SKIP LOCKED, and runs the plugin's sync script as a subprocess.

Scheduler model:
  - PM2 runs this script with `cron_restart: '*/2 * * * *'` style? No —
    the worker runs continuously (long-running process), not cron-triggered.
    PM2 is configured with autorestart: true to respawn on crashes.
  - Plugin syncs enqueue into job_runs with status='queued'. The worker
    dequeues them. PM2 cron entries (cron_restart) still trigger scheduled
    runs — they enqueue instead of executing inline when execution_mode
    is async.

Crash recovery:
  - On startup, the worker finds 'running' rows whose heartbeat_at is
    older than 2× their timeout and marks them as 'error' with a clear
    message. Plugins decide their own resume semantics.

Env security:
  - Subprocesses use plugin_hook_env() / plugin_sync_env() from
    apps/api/src/plugin_subprocess.py (S107 v0.8.1) so plugin code never
    sees NOUSVIZ_ENCRYPTION_KEY or other core secrets.
  - Integrity check from plugin_loader.py (S109 v0.8.1) runs before
    spawning the subprocess.

Cancellation:
  - Worker periodically (every poll tick) checks whether the running
    row's status has flipped to 'cancelling'. If so, it waits for the
    plugin's next check_cancelled() call to exit cleanly.
  - If the plugin ignores cancel for 60 seconds, the worker escalates
    to SIGTERM, then SIGKILL after 10 more seconds.

Timeout:
  - Plugins declare `timeout_seconds` in plugin.yaml sync block (default
    3600). Worker kills the subprocess after that.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# Local .env load so the worker picks up POSTGRES_PASSWORD etc. like the API.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

from apps.api.src.db import get_pg_conn  # noqa: E402
from apps.api.src.plugin_subprocess import plugin_sync_env  # noqa: E402
from apps.api.src.plugin_loader import (  # noqa: E402
    _verify_plugin_integrity,
    IntegrityError,
)
from apps.api.src.log_events import log_job_event  # noqa: E402  (P114 v0.8.4)
from apps.api.src.plugin_sync import resolve_sync_script  # noqa: E402  (B201)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nousviz.jobs-worker")

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

# Poll interval for dequeue. Kept short (2s) so operators see cancellation
# and new queued rows respond quickly. Jitter avoids thundering herd if
# multiple workers are ever added.
POLL_INTERVAL_SEC = 2.0
POLL_JITTER_SEC = 0.5

# Timeout default if a plugin omits `sync.timeout_seconds` in its manifest.
DEFAULT_JOB_TIMEOUT_SEC = 3600  # 1h

# Grace period between "cancel requested" and SIGTERM. Gives the plugin
# time to check_cancelled() and exit cleanly before we escalate.
COOP_CANCEL_GRACE_SEC = 60

# Between SIGTERM and SIGKILL.
SIGTERM_GRACE_SEC = 10

# Heartbeat staleness threshold for orphan recovery.
#
# B277 v0.9.11.17.1: tightened from 2 × DEFAULT_JOB_TIMEOUT_SEC (7200s)
# to 120s. Pre-16.4 heartbeats were only written at claim time, so the
# pre-tightened threshold had to outlast the longest legitimate run.
# Now (v0.9.11.16.4+) workers heartbeat every 10s during a job — a
# missed heartbeat for >2 minutes definitively means the worker is
# gone. Combined with the periodic sweep below, this prevents the
# orphan-during-PM2-reload pattern that left two 'running' rows for
# the same plugin until the next 2-hour cleanup.
ORPHAN_HEARTBEAT_STALE_SEC = 120

# B277 v0.9.11.16.4: live-worker heartbeat cadence. The worker writes
# heartbeat_at = now() this often during a long-running job so the
# dashboard's worker-alive check (90s threshold) can detect dead
# workers in real time, not just at startup. Cheap UPDATE on a
# primary-key row; runs once per claim per cadence interval.
LIVE_HEARTBEAT_INTERVAL_SEC = 10.0

# B277 v0.9.11.17.1: how often the worker's outer loop sweeps for
# orphans. 60s gives a comfortable margin over LIVE_HEARTBEAT_INTERVAL
# (10s) and ORPHAN_HEARTBEAT_STALE_SEC (120s); orphans are surfaced
# within ~3 minutes of the worker dying.
ORPHAN_SWEEP_INTERVAL_SEC = 60.0


def _sweep_orphans(*, source_label: str = "runtime") -> int:
    """Mark 'running' / 'cancelling' rows whose heartbeat is stale as
    error/cancelled. Returns count cleaned. Used both at startup and
    every ORPHAN_SWEEP_INTERVAL_SEC during the outer poll loop so a
    worker that crashes mid-run gets cleaned up within ~3 minutes
    instead of waiting for the next worker startup.

    B277 v0.9.11.17.1: introduced the 'cancelling' branch + periodic
    sweep + tightened threshold. Pre-this, a 'cancelling' row whose
    worker was killed before observing the cancel hung forever.

    A 'running' orphan is finalised as 'error' (the run never produced
    a result). A 'cancelling' orphan is finalised as 'cancelled' (the
    operator's intent was to cancel; we just couldn't deliver it).
    """
    cleaned_total = 0
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE job_runs
                SET status = 'error',
                    completed_at = now(),
                    error = 'Worker died mid-run (orphan cleanup, ' || %s || ')',
                    duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000
                WHERE status = 'running'
                  AND (heartbeat_at IS NULL OR heartbeat_at < now() - interval '%s seconds')
                RETURNING id, job_id
                """,
                (source_label, ORPHAN_HEARTBEAT_STALE_SEC),
            )
            running_orphans = cur.fetchall()

            cur.execute(
                """
                UPDATE job_runs
                SET status = 'cancelled',
                    completed_at = now(),
                    cancelled_at = COALESCE(cancelled_at, now()),
                    error = COALESCE(error, 'Worker died while cancelling ('|| %s ||')'),
                    duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000
                WHERE status = 'cancelling'
                  AND (heartbeat_at IS NULL OR heartbeat_at < now() - interval '%s seconds')
                RETURNING id, job_id
                """,
                (source_label, ORPHAN_HEARTBEAT_STALE_SEC),
            )
            cancelling_orphans = cur.fetchall()

            conn.commit()

        if running_orphans or cancelling_orphans:
            cleaned_total = len(running_orphans) + len(cancelling_orphans)
            running_ids = [r[1] for r in running_orphans]
            cancelling_ids = [r[1] for r in cancelling_orphans]
            logger.warning(
                f"Orphan sweep ({source_label}): cleaned "
                f"{len(running_orphans)} running + {len(cancelling_orphans)} cancelling: "
                f"running={running_ids} cancelling={cancelling_ids}"
            )
            log_job_event(
                "warning",
                (
                    f"Orphan sweep ({source_label}): cleaned "
                    f"{len(running_orphans)} running + {len(cancelling_orphans)} cancelling"
                ),
                {
                    "source": source_label,
                    "running_orphans": running_ids,
                    "cancelling_orphans": cancelling_ids,
                    "stale_threshold_sec": ORPHAN_HEARTBEAT_STALE_SEC,
                },
            )
    except Exception as e:
        logger.error(f"Orphan sweep failed: {e}", exc_info=True)
    return cleaned_total


def _cleanup_orphans_on_startup() -> None:
    """Run a sweep at worker startup. Kept as a named function so the
    log entry is clearly attributed to startup vs runtime."""
    _sweep_orphans(source_label="startup")


def _claim_next_job() -> Optional[dict]:
    """Atomically claim one queued row. Returns None if none available."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # FOR UPDATE SKIP LOCKED: if another worker is claiming the same
            # row at the same time, each of us takes a different row. No
            # contention, no double-claim.
            cur.execute(
                """
                UPDATE job_runs
                SET status = 'running',
                    claimed_by = %s,
                    claimed_at = now(),
                    heartbeat_at = now()
                WHERE id = (
                    SELECT id FROM job_runs
                    WHERE status = 'queued'
                    ORDER BY started_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, job_id, source, started_at, details
                """,
                (WORKER_ID,),
            )
            row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            run_id, job_id, source, started_at, details = row
            return {
                "id": run_id,
                "job_id": job_id,
                "source": source,
                "started_at": started_at,
                "details": details or {},
            }
    except Exception as e:
        logger.error(f"claim_next_job failed: {e}", exc_info=True)
        return None


def _finalize_run(
    run_id: int,
    status: str,
    exit_code: Optional[int] = None,
    error: Optional[str] = None,
    extra_details: Optional[dict] = None,
) -> None:
    """Write final status to job_runs. Computes duration from started_at.

    B284 (v0.9.11.23): after the row is committed, dispatches a webhook
    alert to any matching `job_alert_subscriptions` when the terminal
    status is in {error, timeout, cancelled}. Dispatch happens AFTER
    commit so an alert-delivery failure cannot roll back the
    finalization. Dispatch errors are logged + swallowed (the run is
    correctly persisted regardless).
    """
    finalized_job_id: Optional[str] = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            details_sql = ""
            params: list = [status, exit_code, error]
            if extra_details:
                details_sql = ", details = details || %s::jsonb"
                params.append(json.dumps(extra_details))
            params.append(run_id)
            cur.execute(
                f"""
                UPDATE job_runs
                SET completed_at = now(),
                    status = %s,
                    exit_code = %s,
                    error = %s,
                    duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000
                    {details_sql}
                WHERE id = %s
                RETURNING job_id, started_at,
                          EXTRACT(EPOCH FROM (now() - started_at))::bigint * 1000
                """,
                params,
            )
            row = cur.fetchone()
            if row:
                finalized_job_id = row[0]
            conn.commit()
    except Exception as e:
        logger.error(f"finalize_run failed for {run_id}: {e}", exc_info=True)
        return

    # B284: per-run failure alert dispatch. Only fires for terminal
    # statuses that operators care about. Lazy import keeps the worker
    # startup unchanged when no subscriptions are configured.
    if status in {"error", "timeout", "cancelled"}:
        try:
            from apps.api.src.services.job_alerts import process_run_failure
            process_run_failure({
                "id": run_id,
                "job_id": finalized_job_id,
                "status": status,
                "error": error,
            })
        except Exception as exc:
            logger.warning(
                "job_alerts dispatch failed for run %s (status=%s): %s",
                run_id, status, exc,
            )


def _get_run_status(run_id: int) -> Optional[str]:
    """Fast-path lookup of a run's current status. Used to detect
    operator-initiated cancellation mid-run."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM job_runs WHERE id = %s", (run_id,))
            row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _write_heartbeat(run_id: int) -> None:
    """B277 v0.9.11.16.4: refresh heartbeat_at on the active run.

    Called from the inner poll loop every LIVE_HEARTBEAT_INTERVAL_SEC.
    Lets /api/jobs/dashboard distinguish a live worker from a dead one
    so force-cancel can be safely gated. Failures are logged but
    non-fatal — a missed heartbeat just means the row looks stale for
    one tick, no harm done.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE job_runs SET heartbeat_at = now() WHERE id = %s",
                (run_id,),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"heartbeat update failed for run {run_id}: {e}")


def _parse_plugin_id(job_id: str) -> Optional[str]:
    """Extract plugin_id from a job_id like 'sync:my-plugin'."""
    if not job_id.startswith("sync:"):
        return None
    return job_id[len("sync:"):]


def _parse_hook_job_id(job_id: str) -> Optional[tuple[str, str]]:
    """Extract (plugin_id, hook_name) from 'hook:<plugin>:<hook>'."""
    if not job_id.startswith("hook:"):
        return None
    rest = job_id[len("hook:"):]
    if ":" not in rest:
        return None
    plugin_id, hook_name = rest.rsplit(":", 1)
    return plugin_id, hook_name


def _load_plugin_sync_config(plugin_id: str) -> Optional[dict]:
    """Read plugin.yaml and return the sync block."""
    plugin_dir = REPO_ROOT / "plugins" / "installed" / plugin_id
    manifest = plugin_dir / "plugin.yaml"
    if not manifest.exists():
        return None
    try:
        import yaml
        meta = yaml.safe_load(manifest.read_text()) or {}
    except Exception as e:
        logger.error(f"Could not parse {manifest}: {e}")
        return None
    sync = meta.get("sync") or {}
    # B201: route the script-path resolution through the shared helper so
    # all four sync-trigger sites (worker, two API routes, CLI) agree.
    _sync_path, sync_script_rel = resolve_sync_script(plugin_dir)
    return {
        "plugin_dir": plugin_dir,
        "script": sync_script_rel,
        "execution_mode": sync.get("execution_mode", "sync"),
        "timeout_seconds": int(sync.get("timeout_seconds", DEFAULT_JOB_TIMEOUT_SEC)),
    }


def _run_hook_job(job: dict) -> None:
    """P118: Run a plugin lifecycle hook subprocess end-to-end.

    Job shape: job_id = "hook:<plugin>:<hook_name>".
    Target comes from job.details.target (module:function).
    Worker spawns `python -m nousviz_sdk._hook_runner <target>` with cwd
    set to the plugin dir and S107-hardened sync env (same env used for
    sync scripts — hooks and sync have identical privilege needs).
    """
    run_id = job["id"]
    # B212 (v0.9.6.3): actor stamped at enqueue (by trigger_sync / Admin CLI /
    # plugin install) is read back here so log entries are attributed to the
    # operator who triggered the run. None for autonomous (cron-fired) runs.
    actor_user_id = (job.get("details") or {}).get("actor_user_id")
    parsed = _parse_hook_job_id(job["job_id"])
    if not parsed:
        err = f"Unsupported hook job_id shape: {job['job_id']!r}"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Hook rejected: {err}", run_id=run_id, actor_user_id=actor_user_id)
        return

    plugin_id, hook_name = parsed
    details = job.get("details") or {}
    target = details.get("target")
    if not target:
        err = f"Hook job missing target in details: run {run_id}"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Hook failed for {plugin_id}/{hook_name}: missing target",
                      {"hook_name": hook_name},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    plugin_dir = REPO_ROOT / "plugins" / "installed" / plugin_id
    if not plugin_dir.exists():
        err = f"Plugin not installed: {plugin_id}"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Hook failed for {plugin_id}/{hook_name}: plugin missing",
                      {"hook_name": hook_name},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    # Integrity check (S109) — same as sync.
    try:
        _verify_plugin_integrity(plugin_id, plugin_dir)
    except IntegrityError as e:
        _finalize_run(run_id, "error", error=f"Integrity check failed: {e}")
        log_job_event("error", f"Hook blocked for {plugin_id}/{hook_name}: integrity failed",
                      {"hook_name": hook_name, "error": str(e)},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    # S107-hardened env + hook context via env vars.
    env = plugin_sync_env()
    env["NOUSVIZ_JOB_RUN_ID"] = str(run_id)
    env["NOUSVIZ_PLUGIN_ID"] = plugin_id
    env["NOUSVIZ_HOOK_NAME"] = hook_name
    env["NOUSVIZ_HOOK_PAYLOAD"] = json.dumps(details.get("payload") or {})

    # B136 (v0.9.2): non-secret connection fields are NO LONGER passed via
    # subprocess env. Plugin code uses `nousviz_sdk.get_connection_field()`
    # to read host/port/db from the plugin_settings table over the same
    # path it uses for `get_credential()`. One contract, no env transport,
    # no parent-env mutation, no cross-plugin contamination.

    # P208: register a one-shot broker token for this spawn and pass the
    # socket path + token to the subprocess via env. These are NOT secrets
    # (token is single-use, expires in 30s).
    if _broker is not None:
        broker_token = _broker.register_spawn(plugin_id=plugin_id, run_id=run_id)
        env["NOUSVIZ_CREDS_SOCKET"] = _broker._socket_path  # noqa: SLF001
        env["NOUSVIZ_CREDS_TOKEN"] = broker_token

    # Hooks have a shorter default timeout than sync — they're meant to be
    # quick. 5 min is plenty for credential checks or a remote ping.
    HOOK_TIMEOUT_SEC = 300
    cmd = [sys.executable, "-m", "nousviz_sdk._hook_runner", target]
    logger.info(f"Running hook {plugin_id}/{hook_name} (run {run_id}, target={target})")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(plugin_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=HOOK_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        _finalize_run(run_id, "timeout",
                      error=f"Hook exceeded timeout of {HOOK_TIMEOUT_SEC}s")
        log_job_event("warning", f"Hook timed out for {plugin_id}/{hook_name}",
                      {"hook_name": hook_name, "timeout_sec": HOOK_TIMEOUT_SEC},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    # The runner prints HookResult JSON on its last stdout line.
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    last_line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    hook_message = None
    hook_ok = proc.returncode == 0
    try:
        parsed_result = json.loads(last_line) if last_line else {}
        if isinstance(parsed_result, dict):
            hook_ok = bool(parsed_result.get("ok", hook_ok))
            hook_message = parsed_result.get("message")
    except Exception:
        pass

    status = "success" if hook_ok else "error"
    _finalize_run(
        run_id,
        status,
        exit_code=proc.returncode,
        error=None if hook_ok else (hook_message or stderr[-1000:] or "Hook failed"),
        extra_details={
            "hook_name": hook_name,
            "plugin_id": plugin_id,
            "target": target,
            "stdout_tail": stdout[-500:],
            "stderr_tail": stderr[-500:],
            "message": hook_message,
        },
    )

    if hook_ok:
        log_job_event(
            "info",
            f"Hook {hook_name} succeeded for {plugin_id}"
            + (f": {hook_message}" if hook_message else ""),
            {"hook_name": hook_name, "source": "hook"},
            plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
        )
    else:
        # P204 (v0.9.0): detect hook-module import failures and emit a
        # dedicated hook_runner source entry with a targeted hint. The
        # most common failure is a plugin author putting hooks/ under
        # src/ instead of at the plugin root.
        is_import_err = "ModuleNotFoundError" in (stderr or "") or "ModuleNotFoundError" in (hook_message or "")
        if is_import_err:
            log_job_event(
                "error",
                f"Plugin {plugin_id} hook {hook_name} failed to load: ModuleNotFoundError",
                {
                    "hook_name": hook_name,
                    "target": target,
                    "exit_code": proc.returncode,
                    "stderr_tail": stderr[-500:],
                    "source": "hook_runner",
                    "hint": "Ensure the hook module is importable from the plugin root (not inside src/).",
                },
                plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
            )
        else:
            log_job_event(
                "error",
                f"Hook {hook_name} failed for {plugin_id}"
                + (f": {hook_message}" if hook_message else ""),
                {"hook_name": hook_name,
                 "exit_code": proc.returncode, "stderr_tail": stderr[-500:],
                 "source": "hook"},
                plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
            )


def _run_job(job: dict) -> None:
    """Run a single claimed job end-to-end."""
    run_id = job["id"]
    # B212 (v0.9.6.3): actor stamped at enqueue (by trigger_sync / Admin CLI)
    # is read back here so log entries are attributed to the operator who
    # triggered the run. None for autonomous (cron-fired) runs.
    actor_user_id = (job.get("details") or {}).get("actor_user_id")

    # P118: hook jobs use their own runner, not the sync pipeline.
    if job["job_id"].startswith("hook:"):
        _run_hook_job(job)
        return

    plugin_id = _parse_plugin_id(job["job_id"])

    if not plugin_id:
        err = f"Unsupported job_id shape: {job['job_id']!r} (expected 'sync:<plugin>')"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Sync rejected: {err}", run_id=run_id, actor_user_id=actor_user_id)
        return

    cfg = _load_plugin_sync_config(plugin_id)
    if not cfg:
        err = f"Plugin not installed: {plugin_id}"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Sync failed for {plugin_id}: {err}",
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    plugin_dir = cfg["plugin_dir"]
    sync_script = plugin_dir / cfg["script"]
    if not sync_script.exists():
        err = f"Sync script not found: {sync_script}"
        _finalize_run(run_id, "error", error=err)
        log_job_event("error", f"Sync failed for {plugin_id}: script missing",
                      {"path": str(sync_script)},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    # Integrity check (S109). Skip if override allows.
    try:
        _verify_plugin_integrity(plugin_id, plugin_dir)
    except IntegrityError as e:
        _finalize_run(run_id, "error", error=f"Integrity check failed: {e}")
        log_job_event("error", f"Sync blocked for {plugin_id}: integrity failed",
                      {"error": str(e)},
                      plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id)
        return

    # Subprocess env — hardened sync env + run_id for the SDK to find.
    env = plugin_sync_env()
    env["NOUSVIZ_JOB_RUN_ID"] = str(run_id)
    env["NOUSVIZ_PLUGIN_ID"] = plugin_id

    # B136 (v0.9.2): non-secret connection fields are NO LONGER passed via
    # subprocess env. Plugin code uses `nousviz_sdk.get_connection_field()`
    # to read host/port/db from the plugin_settings table.

    # P208: register a one-shot broker token for this spawn. Subprocess's
    # SDK uses it to fetch credentials over the Unix socket.
    if _broker is not None:
        broker_token = _broker.register_spawn(plugin_id=plugin_id, run_id=run_id)
        env["NOUSVIZ_CREDS_SOCKET"] = _broker._socket_path  # noqa: SLF001
        env["NOUSVIZ_CREDS_TOKEN"] = broker_token

    timeout_sec = cfg["timeout_seconds"]
    logger.info(
        f"Running {plugin_id} (run {run_id}, timeout={timeout_sec}s, mode=async)"
    )

    cmd = [sys.executable, str(sync_script), "--source=cron"]
    # Start the subprocess detached so we can signal it cleanly.
    proc = subprocess.Popen(
        cmd,
        cwd=str(plugin_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # own process group — makes SIGTERM propagate
    )

    start = time.monotonic()
    cancel_requested_at: Optional[float] = None
    sigterm_sent_at: Optional[float] = None
    # B277 v0.9.11.16.4: track last live-heartbeat write so we refresh
    # heartbeat_at every LIVE_HEARTBEAT_INTERVAL_SEC. Initial claim
    # already wrote heartbeat_at = now() so we start the clock here.
    last_heartbeat_at = time.monotonic()
    # P114: set once timeout/cancel finalized the run so subsequent
    # proc exit doesn't overwrite the row or double-log.
    terminal_logged = False

    while True:
        ret = proc.poll()
        if ret is not None:
            # Plugin exited on its own.
            stdout, stderr = proc.communicate()
            status = "success" if ret == 0 else "error"

            # If the plugin exited after we asked for cancel, record as cancelled
            # (it's more informative than 'success' when the exit was coordinated).
            if cancel_requested_at is not None:
                status = "cancelled"

            duration_ms = int((time.monotonic() - start) * 1000)

            # If we already finalized+logged as 'timeout' during the
            # timeout branch below, don't overwrite the row or log a
            # second terminal event. The subprocess exit is just the
            # cleanup from our SIGTERM/SIGKILL escalation.
            if not terminal_logged:
                _finalize_run(
                    run_id, status,
                    exit_code=ret,
                    error=(stderr or "")[-1000:] if status in ("error", "timeout") else None,
                    extra_details={
                        "stdout_tail": (stdout or "")[-500:],
                        "stderr_tail": (stderr or "")[-500:],
                        "exit_code": ret,
                    },
                )
                # P114 v0.8.4: surface terminal transitions in the Logs panel.
                # No "claimed" event — the terminal event already implies claim.
                if status == "success":
                    log_job_event(
                        "info",
                        f"Sync succeeded for {plugin_id}",
                        {"duration_ms": duration_ms},
                        plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
                    )
                    # P118: fire on_first_run_success if this is the first success.
                    # Helper checks COUNT and is a no-op for subsequent runs.
                    try:
                        from apps.api.src.plugin_hooks import fire_first_sync_success_hook
                        fire_first_sync_success_hook(plugin_id)
                    except Exception as _hook_err:
                        logger.warning(
                            f"on_first_run_success enqueue failed for {plugin_id}: {_hook_err}"
                        )
                elif status == "cancelled":
                    log_job_event(
                        "info",
                        f"Sync cancelled for {plugin_id}",
                        {"duration_ms": duration_ms},
                        plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
                    )
                else:
                    log_job_event(
                        "error",
                        f"Sync failed for {plugin_id}",
                        {
                            "exit_code": ret,
                            "duration_ms": duration_ms,
                            "stderr_tail": (stderr or "")[-500:],
                        },
                        plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
                    )
            logger.info(f"Run {run_id} completed: status={status}, exit={ret}")
            return

        elapsed = time.monotonic() - start

        # Timeout enforcement
        if elapsed > timeout_sec and cancel_requested_at is None:
            logger.warning(
                f"Run {run_id} exceeded timeout={timeout_sec}s — terminating"
            )
            cancel_requested_at = time.monotonic()
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                sigterm_sent_at = time.monotonic()
            except ProcessLookupError:
                pass
            _finalize_run(
                run_id, "timeout",
                error=f"Exceeded timeout of {timeout_sec}s",
            )
            # P114: surface timeout in Logs as warning.
            log_job_event(
                "warning",
                f"Sync timed out for {plugin_id}",
                {"timeout_sec": timeout_sec},
                plugin_id=plugin_id, run_id=run_id, actor_user_id=actor_user_id,
            )
            terminal_logged = True  # don't log again when subprocess exits
            # Don't return yet — still need to kill and collect
            # Loop continues and handles SIGKILL if needed

        # Poll for operator cancellation
        if cancel_requested_at is None:
            status = _get_run_status(run_id)
            if status == "cancelling":
                logger.info(f"Run {run_id}: cancel requested by operator")
                cancel_requested_at = time.monotonic()

        # Escalate to SIGTERM after grace
        if (
            cancel_requested_at is not None
            and sigterm_sent_at is None
            and time.monotonic() - cancel_requested_at > COOP_CANCEL_GRACE_SEC
        ):
            logger.warning(
                f"Run {run_id}: plugin didn't exit after {COOP_CANCEL_GRACE_SEC}s "
                f"of cancel request — sending SIGTERM"
            )
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                sigterm_sent_at = time.monotonic()
            except ProcessLookupError:
                pass

        # Escalate to SIGKILL after SIGTERM grace
        if (
            sigterm_sent_at is not None
            and time.monotonic() - sigterm_sent_at > SIGTERM_GRACE_SEC
        ):
            logger.error(
                f"Run {run_id}: plugin still alive after SIGTERM — sending SIGKILL"
            )
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Next poll will see exit code and finalize.

        # B277 v0.9.11.16.4: live heartbeat. Skip while the run is
        # already heading terminal (timeout/cancel) so we don't refresh
        # a row that's about to be finalized.
        if not terminal_logged and (
            time.monotonic() - last_heartbeat_at >= LIVE_HEARTBEAT_INTERVAL_SEC
        ):
            _write_heartbeat(run_id)
            last_heartbeat_at = time.monotonic()

        time.sleep(1.0)


_broker = None  # CredentialBroker instance, started in main()


def main() -> None:
    logger.info(f"jobs-worker starting (id={WORKER_ID})")

    # P205 (v0.9.0): verify nousviz_sdk is importable before we claim
    # any jobs. The worker spawns subprocesses that `python -m
    # nousviz_sdk._hook_runner ...` — if the module isn't importable in
    # the worker's venv, every hook fires ModuleNotFoundError and the
    # operator only discovers it via failed job_runs. Fail loud instead.
    try:
        import nousviz_sdk
        logger.info(f"nousviz_sdk v{nousviz_sdk.__version__} importable")
    except ImportError as _sdk_err:
        msg = f"nousviz_sdk not importable: {_sdk_err}. Run pip install -e sdk/ in the worker venv."
        logger.error(msg)
        try:
            log_job_event("error", "jobs-worker refusing to start: nousviz_sdk unavailable",
                          {"exception_message": str(_sdk_err), "source": "startup"})
        except Exception:
            pass
        raise SystemExit(1)

    # P208 (v0.9.0): start the credential broker before claiming any jobs.
    # Every spawn we do from here onward will register a token with this
    # broker and pass it to the subprocess via env. The subprocess's SDK
    # init exchanges the token for its credentials over the Unix socket.
    global _broker
    try:
        from apps.worker.src.credential_broker import CredentialBroker, DEFAULT_SOCKET_PATH
        socket_path = os.environ.get("NOUSVIZ_CREDS_SOCKET", DEFAULT_SOCKET_PATH)
        _broker = CredentialBroker(socket_path=socket_path)
        _broker.start()
        logger.info(f"credential broker listening on {socket_path}")
    except Exception as exc:
        logger.error(
            f"credential broker failed to start: {exc}. "
            f"Subprocesses WILL NOT be able to fetch credentials. "
            f"Refusing to claim jobs.",
            exc_info=True,
        )
        try:
            log_job_event(
                "error",
                "jobs-worker refusing to start: credential broker unavailable",
                {"reason": str(exc)},
            )
        except Exception:
            pass
        raise SystemExit(1)

    _cleanup_orphans_on_startup()

    # B277 v0.9.11.17.1: track when we last swept for orphans during
    # the runtime poll loop (in addition to startup). With live
    # heartbeats, an orphan is anything in 'running'/'cancelling'
    # whose heartbeat is older than ORPHAN_HEARTBEAT_STALE_SEC.
    last_orphan_sweep_at = time.monotonic()
    logger.info(f"Polling job_runs (interval={POLL_INTERVAL_SEC}s)")
    try:
        import random
        while True:
            # Periodic orphan sweep — runs even when the queue is busy.
            if time.monotonic() - last_orphan_sweep_at >= ORPHAN_SWEEP_INTERVAL_SEC:
                _sweep_orphans(source_label="periodic")
                last_orphan_sweep_at = time.monotonic()

            job = _claim_next_job()
            if job is not None:
                try:
                    _run_job(job)
                except Exception as e:
                    logger.error(
                        f"_run_job threw unexpected exception for run {job['id']}: {e}",
                        exc_info=True,
                    )
                    _finalize_run(
                        job["id"], "error",
                        error=f"Worker error: {e.__class__.__name__}: {e}",
                    )
                # Immediately loop to drain the queue — don't sleep if there
                # are still queued rows.
                continue
            # No work — sleep with jitter before next poll.
            time.sleep(POLL_INTERVAL_SEC + random.uniform(0, POLL_JITTER_SEC))
    except KeyboardInterrupt:
        logger.info("jobs-worker shutting down (KeyboardInterrupt)")


if __name__ == "__main__":
    main()
