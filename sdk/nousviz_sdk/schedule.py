"""
nousviz_sdk.schedule — Read-only schedule info for a plugin.

Plugins that want to self-report their own schedule state (e.g. a plugin
dashboard showing "Next sync in 2h 15m") can read it through the SDK
instead of reaching into apps.* or reading plugin.yaml directly.

    from nousviz_sdk.schedule import get_schedule

    info = get_schedule("my-plugin")
    # {
    #   "plugin_id": "my-plugin",
    #   "cron": "0 6 * * *",
    #   "next_run_at": "2026-04-25T06:00:00+00:00",
    #   "last_run_at": "2026-04-24T06:00:00+00:00",
    #   "active_run_id": None,
    #   "concurrency_policy": "skip_if_running",
    #   "execution_mode": "sync",
    # }

Returns None if the plugin isn't installed or its manifest can't be read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _repo_root() -> Path:
    # sdk/ and apps/ sit side-by-side under the repo root.
    return Path(__file__).resolve().parents[2]


def _read_manifest(plugin_id: str) -> Optional[dict]:
    manifest = _repo_root() / "plugins" / "installed" / plugin_id / "plugin.yaml"
    if not manifest.exists():
        return None
    try:
        import yaml
        return yaml.safe_load(manifest.read_text()) or {}
    except Exception:
        return None


def _next_run_at(cron_expr: str) -> Optional[str]:
    if not cron_expr:
        return None
    try:
        from croniter import croniter
        base = datetime.now(timezone.utc)
        nxt = croniter(cron_expr, base).get_next(datetime)
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        return nxt.isoformat()
    except Exception:
        return None


def get_schedule(plugin_id: str) -> Optional[dict]:
    """Read-only view of a plugin's current schedule + concurrency config.

    Returns None if the plugin isn't installed.

    Shape:
      plugin_id          — echoed back for convenience
      cron               — cron expression from plugin.yaml sync.schedule
      schedule_label     — human-readable label (e.g. "Every 4 hours")
                           or the raw cron expression
      next_run_at        — ISO 8601 UTC of next firing, or None
      last_run_at        — ISO 8601 of last successful run (from job_runs),
                           or None if never run
      active_run_id      — int if a run is queued/running/paused, else None
      active_run_status  — status of the active run, or None
      execution_mode     — "sync" | "async"
      concurrency_policy — "skip_if_running" | "queue_after" | "cancel_active"
    """
    meta = _read_manifest(plugin_id)
    if meta is None:
        return None

    sync = meta.get("sync") or {}
    cron = sync.get("schedule", "")

    # Query job_runs via the shared pool (delegates to apps.api.src.db when
    # running inside core; falls back to direct psycopg2 otherwise).
    from . import get_pg_conn
    last_run_at: Optional[str] = None
    active_run_id: Optional[int] = None
    active_run_status: Optional[str] = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT MAX(completed_at)
                FROM job_runs
                WHERE job_id = %s AND status = 'success'
                """,
                (f"sync:{plugin_id}",),
            )
            row = cur.fetchone()
            if row and row[0]:
                last_run_at = row[0].isoformat()
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
            if active:
                active_run_id = int(active[0])
                active_run_status = active[1]
    except Exception:
        # DB unreachable — schedule info degrades gracefully.
        pass

    # Cheap lookup for human label; matches what the jobs UI uses.
    _LABELS = {
        "0 */4 * * *": "Every 4 hours",
        "0 6 * * *": "Daily at 6am",
        "0 0 * * *": "Daily at midnight",
        "*/5 * * * *": "Every 5 minutes",
        "0 * * * *": "Hourly",
    }

    return {
        "plugin_id": plugin_id,
        "cron": cron,
        "schedule_label": _LABELS.get(cron, cron) if cron else None,
        "next_run_at": _next_run_at(cron) if cron else None,
        "last_run_at": last_run_at,
        "active_run_id": active_run_id,
        "active_run_status": active_run_status,
        "execution_mode": sync.get("execution_mode", "sync"),
        "concurrency_policy": sync.get("concurrency_policy", "skip_if_running"),
    }
