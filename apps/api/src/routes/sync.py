"""
/api/plugins/:id/sync — Trigger plugin sync

B205 (v0.9.6): manual triggers always enqueue and return immediately.
The HTTP request never blocks on subprocess execution. The async worker
(apps/worker/src/run_jobs.py) picks up queued rows and runs the plugin's
sync script. Live progress is reported via nousviz_sdk.progress.report
into job_runs.progress, polled by the unified Sync card on the plugin
Settings tab and /system/jobs row expansion.

This module also serves /setup and /health-check endpoints which remain
synchronous (they're short-lived and not part of the sync job pipeline).
"""

import json
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn
from ..plugin_subprocess import plugin_sync_env as _plugin_env  # S107
from ..plugin_sync import resolve_sync_script  # B201

from fastapi import Depends

from .auth import get_me
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.sync import PluginScriptRunResponse

logger = logging.getLogger("nousviz.api.sync")

router = APIRouter(tags=["sync"])

# B227 + B228: register all sync routes.
register_route("POST", "/api/plugins/{plugin_id}/sync", "data.sync")
register_route("POST", "/api/plugins/{plugin_id}/setup", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/health-check", "plugins.configure")

PLUGINS_DIR = Path(__file__).resolve().parents[4] / "plugins" / "installed"


class SyncRequest(BaseModel):
    mode: str = "incremental"  # incremental | full | days
    days: int | None = None


class SyncResponse(BaseModel):
    status: str
    output: str = ""
    exit_code: int | None = None
    # P107: present when the plugin's execution_mode is async
    run_id: int | None = None
    enqueued: bool = False


def _load_sync_config(plugin_id: str) -> dict:
    """Read the sync block from plugin.yaml. Returns a dict with
    execution_mode + concurrency_policy (both with sensible defaults)."""
    manifest = PLUGINS_DIR / plugin_id / "plugin.yaml"
    if not manifest.exists():
        return {"execution_mode": "sync", "concurrency_policy": "skip_if_running"}
    try:
        import yaml
        meta = yaml.safe_load(manifest.read_text()) or {}
        sync = meta.get("sync") or {}
        return {
            "execution_mode": sync.get("execution_mode", "sync"),
            "concurrency_policy": sync.get("concurrency_policy", "skip_if_running"),
        }
    except Exception:
        return {"execution_mode": "sync", "concurrency_policy": "skip_if_running"}


def _load_execution_mode(plugin_id: str) -> str:
    """Backwards-compatible wrapper — just the execution_mode."""
    return _load_sync_config(plugin_id)["execution_mode"]


def _enforce_concurrency(
    plugin_id: str,
    policy: str,
    *,
    actor_user_id: Optional[str] = None,
) -> Optional[dict]:
    """P108: apply concurrency_policy at enqueue time.

    Returns a dict to short-circuit enqueue (skipped response), or None
    to proceed with the normal enqueue path.

    Policies:
      skip_if_running  — if an active run exists, write a 'skipped' row
                         and return skip info to the caller.
      queue_after      — let the new run queue regardless; worker runs
                         them sequentially.
      cancel_active    — mark the active run as 'cancelling' so the
                         worker ends it, then proceed with enqueue.
    """
    if policy == "queue_after":
        return None

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, status FROM job_runs
                WHERE job_id = %s
                  AND status IN ('queued', 'running', 'cancelling', 'paused')
                ORDER BY id DESC LIMIT 1
                """,
                (f"sync:{plugin_id}",),
            )
            active = cur.fetchone()
            if not active:
                return None
            active_id, active_status = active

            if policy == "cancel_active":
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = 'cancelling', cancelled_at = now()
                    WHERE id = %s AND status IN ('queued', 'running')
                    """,
                    (active_id,),
                )
                conn.commit()
                return None  # proceed with new enqueue

            # Default: skip_if_running
            skipped_details = {
                "skipped_because": "skip_if_running",
                "active_run_id": active_id,
                "active_status": active_status,
            }
            # B212 (v0.9.6.3): stamp actor on the skipped row so /system/logs
            # can attribute "you tried to sync but it was already running"
            # events to the right user.
            if actor_user_id:
                skipped_details["actor_user_id"] = actor_user_id
            cur.execute(
                """
                INSERT INTO job_runs (
                    job_id, started_at, completed_at, status, source,
                    duration_ms, details
                )
                VALUES (%s, now(), now(), 'skipped', 'manual', 0, %s::jsonb)
                RETURNING id
                """,
                (f"sync:{plugin_id}", json.dumps(skipped_details)),
            )
            skip_row = cur.fetchone()
            conn.commit()
            return {
                "skipped": True,
                "active_run_id": active_id,
                "active_status": active_status,
                "skip_run_id": skip_row[0] if skip_row else None,
            }
    except Exception as e:
        logger.error(f"concurrency check failed for {plugin_id}: {e}")
        # Fail open: don't block the sync over a policy lookup failure.
        return None


def _enqueue_async_run(
    plugin_id: str,
    mode_label: str,
    *,
    actor_user_id: Optional[str] = None,
) -> Optional[int]:
    """P107: insert a row with status='queued' for the jobs-worker to pick up.

    B212 (v0.9.6.3): optional actor_user_id is stamped into details JSONB
    so the worker can read it back when writing lifecycle log events.
    Cron-fired enqueues from run_scheduler.py don't pass this — autonomous
    runs correctly have NULL actor in app_logs.
    """
    try:
        details: dict = {"mode": mode_label}
        if actor_user_id:
            details["actor_user_id"] = actor_user_id
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO job_runs (job_id, status, source, details)
                VALUES (%s, 'queued', 'manual', %s::jsonb)
                RETURNING id
                """,
                (f"sync:{plugin_id}", json.dumps(details)),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0]) if row else None
    except Exception as e:
        logger.error(f"enqueue failed for {plugin_id}: {e}")
        return None


@router.post("/plugins/{plugin_id}/sync", response_model=SyncResponse, operation_id="plugins.sync")
async def trigger_sync(
    plugin_id: str,
    request: Request,
    # B237 (v0.9.10.0.0): default-construct SyncRequest so callers without a
    # body work. The frontend SyncStatusCard POSTs no body, and B221's deletion
    # of the shadow `sync_plugin` handler made this endpoint canonical without
    # adjusting the body requirement — every Sync Now click returned 422 since
    # v0.9.7.1. All SyncRequest fields already had defaults; the param itself
    # just needed one too.
    req: SyncRequest = SyncRequest(),
    _: None = Depends(requires("data.sync")),
):
    """Trigger a plugin sync manually.

    B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
    scheduled runs (the scheduler dispatches them) but ignored here —
    manual triggers always enqueue and return immediately so the HTTP
    request never blocks on subprocess execution. The unified Sync card
    on the plugin Settings tab polls /sync/status for live progress.

    Returns 409 Conflict when an active run already exists (status in
    queued/running/cancelling). Body shape on 409:
        {"detail": {"run_id": <existing>, "status": <status>,
                    "already_running": true}}
    Frontend swaps to the live progress view in this case rather than
    enqueueing a duplicate.
    """
    user = get_me(request)
    # B212 (v0.9.6.3): capture actor so the eventual log entry written by
    # the worker can attribute the sync to the user who clicked Sync Now.
    actor_user_id = str(user.get("id")) if user.get("id") else None
    plugin_dir = PLUGINS_DIR / plugin_id
    sync_script, sync_script_rel = resolve_sync_script(plugin_dir)

    if not sync_script.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Sync script not found for plugin '{plugin_id}' at {sync_script_rel}",
        )

    cfg = _load_sync_config(plugin_id)
    concurrency_policy = cfg["concurrency_policy"]

    # B205: active-run guard. If a run is in flight, return 409 Conflict
    # so the frontend can swap to the live progress view. Honor
    # cancel_active policy by marking the active run cancelling and
    # proceeding with a new enqueue.
    skip_result = _enforce_concurrency(
        plugin_id, concurrency_policy, actor_user_id=actor_user_id,
    )
    if skip_result and skip_result.get("skipped"):
        logger.info(
            f"Sync rejected for {plugin_id}: "
            f"active run {skip_result['active_run_id']} "
            f"(status={skip_result['active_status']})"
        )
        raise HTTPException(
            status_code=409,
            detail={
                "run_id": skip_result["active_run_id"],
                "status": skip_result["active_status"],
                "already_running": True,
                "message": (
                    f"Sync already in progress for {plugin_id} "
                    f"(run_id={skip_result['active_run_id']}, "
                    f"status={skip_result['active_status']})"
                ),
            },
        )

    # B205: always enqueue. Manifest execution_mode is no longer consulted
    # for manual triggers — the inline subprocess path is gone. Scheduled
    # runs continue to honor execution_mode via the scheduler.
    run_id = _enqueue_async_run(plugin_id, req.mode, actor_user_id=actor_user_id)
    if run_id is None:
        raise HTTPException(500, "Failed to enqueue sync run")
    logger.info(f"Enqueued sync for {plugin_id} (run_id={run_id}, mode={req.mode})")
    return SyncResponse(
        status="queued",
        enqueued=True,
        run_id=run_id,
    )


@router.post(
    "/plugins/{plugin_id}/setup",
    operation_id="plugins.setup",
    response_model=PluginScriptRunResponse,
    summary="Run a plugin's setup_schema.py script (60s timeout)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin has no setup_schema.py."},
        500: {"model": ErrorDetail, "description": "Subprocess raised before producing output."},
    },
)
async def setup_schema(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Run the plugin's schema setup script.

    Synchronous (not part of the async sync pipeline) — the response
    blocks until the subprocess exits or the 60s timeout fires. The
    plugin's environment is sanitised by `plugin_subprocess.plugin_sync_env`.
    """
    plugin_dir = PLUGINS_DIR / plugin_id
    setup_script = plugin_dir / "src" / "setup_schema.py"

    if not setup_script.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Setup script not found for plugin '{plugin_id}'",
        )

    try:
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            capture_output=True,
            text=True,
            timeout=60,
            env=_plugin_env(),
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout + result.stderr,
            "exit_code": result.returncode,
        }

    except Exception as e:
        logger.error(f"Schema setup failed for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Schema setup failed. Check server logs for details.")


@router.post(
    "/plugins/{plugin_id}/health-check",
    operation_id="plugins.health_check",
    response_model=PluginScriptRunResponse,
    summary="Run a plugin's health_check.py script (30s timeout)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin has no health_check.py."},
        500: {"model": ErrorDetail, "description": "Subprocess raised before producing output."},
    },
)
async def health_check(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Run the plugin's health check script.

    Synchronous — the response blocks until the subprocess exits or
    the 30s timeout fires. The plugin's environment is sanitised by
    `plugin_subprocess.plugin_sync_env`.
    """
    plugin_dir = PLUGINS_DIR / plugin_id
    health_script = plugin_dir / "src" / "health_check.py"

    if not health_script.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Health check script not found for plugin '{plugin_id}'",
        )

    try:
        result = subprocess.run(
            [sys.executable, str(health_script)],
            capture_output=True,
            text=True,
            timeout=30,
            env=_plugin_env(),
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout + result.stderr,
            "exit_code": result.returncode,
        }

    except Exception as e:
        logger.error(f"Health check failed for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Health check failed. Check server logs for details.")
