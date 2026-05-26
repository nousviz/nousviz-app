"""
Scheduled Jobs API.

Returns sync + alert + health-monitor jobs with real last-run timestamps,
schedules sourced from PM2 or system crontab, and a classification of
which scheduling mechanism the server is using (B193).

- Plugin sync last_run reads from job_runs (job_id = 'sync:<plugin_id>',
  most recent status='success' row). Written by BaseSyncScript.main() and
  POST /api/plugins/:id/sync. Falls back to plugin_settings._last_sync for
  legacy plugins that still write the old key directly.
- Alert runner last_run reads MAX(triggered_at) from alert_events.
- Health monitor last_run reads MAX(created_at) from health_log.
- Cron schedules come from PM2 (`pm2 jlist`) + system crontab. The response
  includes a `cron_source` field the frontend uses to show an appropriate
  "how to schedule" hint instead of the generic install-crontab block.
"""
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends
from ..db import get_pg_conn
from ..plugin_sync import resolve_sync_script  # B202
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.jobs import (
    FireNowResponse,
    JobRunControlResponse,
    JobRunRow,
    JobRunsListResponse,
    JobsDashboardResponse,
    JobsListResponse,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# B228: register jobs routes. cancel/pause/resume/fire-now are write
# operations (analyst+ inline); using jobs.write which is admin+ would
# narrow access. The closest analyst+ permission semantically is jobs.read
# is viewer+, so we have a gap — introducing jobs.control here mirrors the
# inline _require_analyst exactly.
register_route("GET", "/api/jobs", "jobs.read")
register_route("GET", "/api/jobs/dashboard", "jobs.read")
register_route("GET", "/api/jobs/runs", "jobs.read")
register_route("GET", "/api/jobs/{run_id}", "jobs.read")
register_route("POST", "/api/jobs/{run_id}/cancel", "jobs.write")
register_route("POST", "/api/jobs/{run_id}/pause", "jobs.write")
register_route("POST", "/api/jobs/{run_id}/resume", "jobs.write")
register_route("POST", "/api/jobs/{job_id}/fire-now", "jobs.write")

REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"
COMMUNITY_DIR = REPO_ROOT / "plugins" / "community"


# ── Schedule helpers ──────────────────────────────────────────────────

_SCHEDULE_LABELS = {
    "*/5 * * * *":   "Every 5 minutes",
    "*/10 * * * *":  "Every 10 minutes",
    "*/15 * * * *":  "Every 15 minutes",
    "*/30 * * * *":  "Every 30 minutes",
    "0 * * * *":     "Every hour",
    "0 */2 * * *":   "Every 2 hours",
    "0 */4 * * *":   "Every 4 hours",
    "0 */6 * * *":   "Every 6 hours",
    "0 */12 * * *":  "Every 12 hours",
    "0 6 * * *":     "Daily at 6:00 AM",
    "0 0 * * *":     "Daily at midnight",
    "0 0 * * 1":     "Weekly (Monday)",
}


def _next_run_at(cron_expr: str) -> str | None:
    """P108: compute the next cron firing after now.

    Returns an ISO 8601 timestamp string (UTC) or None if:
      - The cron expression is invalid
      - croniter isn't installed (shouldn't happen post-install but we
        guard because this helper runs on every /api/jobs call)

    Uses croniter which handles all 5-field Vixie cron expressions we
    declare in plugin.yaml / ecosystem.config.js.
    """
    if not cron_expr:
        return None
    try:
        from croniter import croniter
        base = datetime.now(timezone.utc)
        nxt = croniter(cron_expr, base).get_next(datetime)
        # croniter returns naive datetime in some versions; normalise to UTC.
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        return nxt.isoformat()
    except Exception:
        return None


def _schedule_max_age(cron: str) -> timedelta:
    """Map a cron expression to the maximum expected interval between runs.

    Returns a timedelta. Unknown patterns default to 24 hours (conservative
    — won't flag staleness unless the job is really silent).
    Used to classify `ok` vs `stale` in list_jobs().
    """
    mapping: dict[str, timedelta] = {
        "*/5 * * * *":   timedelta(minutes=5),
        "*/10 * * * *":  timedelta(minutes=10),
        "*/15 * * * *":  timedelta(minutes=15),
        "*/30 * * * *":  timedelta(minutes=30),
        "0 * * * *":     timedelta(hours=1),
        "0 */2 * * *":   timedelta(hours=2),
        "0 */4 * * *":   timedelta(hours=4),
        "0 */6 * * *":   timedelta(hours=6),
        "0 */12 * * *":  timedelta(hours=12),
        "0 6 * * *":     timedelta(hours=24),
        "0 0 * * *":     timedelta(hours=24),
        "0 0 * * 1":     timedelta(days=7),
    }
    return mapping.get(cron, timedelta(hours=24))


def _classify_status(last_run_iso: str | None, schedule: str) -> str:
    """Return 'ok' | 'stale' | 'never' based on last run vs 2× the schedule."""
    if not last_run_iso:
        return "never"
    try:
        last_dt = datetime.fromisoformat(str(last_run_iso).replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_dt
        # Stale threshold: 2× the declared interval (gives one grace period)
        return "stale" if age > _schedule_max_age(schedule) * 2 else "ok"
    except Exception:
        return "ok" if last_run_iso else "never"


# ── Schedule sources ──────────────────────────────────────────────────


def _crontab_entries() -> list[dict]:
    """Parse current user's crontab for NousViz-related entries. System-crontab
    deploys only — on PM2 deploys this returns [] and _pm2_cron_entries
    picks up the schedules instead."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return []
        entries = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "nousviz" in line.lower():
                parts = line.split(None, 5)
                if len(parts) >= 6:
                    entries.append({
                        "source": "crontab",
                        "name": parts[5].split()[0] if parts[5] else "(crontab entry)",
                        "schedule": " ".join(parts[:5]),
                        "command": parts[5],
                        "raw": line,
                    })
        return entries
    except Exception:
        return []


def _pm2_cron_entries() -> list[dict]:
    """Return PM2-managed processes that have a cron_restart schedule.

    `pm2 jlist` outputs JSON describing every PM2-managed process. We pull
    the ones that define `cron_restart` (alerts, health-monitor, per-plugin
    sync workers added from ecosystem.config.js) and report them with the
    same shape as crontab entries so downstream code doesn't care about the
    source.
    """
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        procs = json.loads(result.stdout or "[]")
    except FileNotFoundError:
        # pm2 not installed (local dev) — no PM2 schedules to report
        return []
    except Exception:
        return []

    entries: list[dict] = []
    for p in procs:
        env = p.get("pm2_env") or {}
        cron = env.get("cron_restart")
        if not cron:
            continue
        name = env.get("name") or p.get("name") or ""
        # `pm2_exec_path` is the interpreter; `args` is the script path
        args = env.get("args") or []
        if isinstance(args, list):
            command = " ".join(str(a) for a in args)
        else:
            command = str(args)
        entries.append({
            "source": "pm2",
            "name": name,
            "schedule": cron,
            "command": command,
            "raw": f"pm2:{name} {cron} {command}",
        })
    return entries


def _classify_cron_source(crontab: list[dict], pm2: list[dict]) -> str:
    """'pm2' | 'crontab' | 'both' | 'none' — which scheduling mechanism is in use."""
    has_cron = len(crontab) > 0
    has_pm2 = len(pm2) > 0
    if has_pm2 and has_cron:
        return "both"
    if has_pm2:
        return "pm2"
    if has_cron:
        return "crontab"
    return "none"


def _cron_active(job_identifiers: list[str], schedule_entries: list[dict]) -> tuple[bool, str | None]:
    """Returns (is_active, source) — is any schedule entry running this job? What's the source?

    `job_identifiers` is a list of substrings to match against the entry's
    command or name (e.g., ["starter-plugin", "run_alerts.py", "health/record"]).
    """
    for entry in schedule_entries:
        haystack = (entry.get("command") or "") + " " + (entry.get("name") or "")
        for needle in job_identifiers:
            if needle and needle in haystack:
                return True, entry.get("source", "crontab")
    return False, None


# ── Plugin sync jobs ──────────────────────────────────────────────────


def _plugin_last_sync_map() -> dict[str, str]:
    """Return {plugin_id: iso_timestamp} of the most recent successful sync.

    Reads from job_runs. Three job_id shapes have existed historically:
      - 'sync:<plugin>'  (pre-v0.9.3 legacy, BaseSyncScript path)
      - '<plugin>'       (v0.9.3 scheduler enqueues with the plain slug)
      - 'manual:<plugin>' (some action endpoints — not relevant here)

    B150 (v0.9.3.2): we union both 'sync:<plugin>' and the plain slug so
    runs from the new scheduler show up in /system/jobs. The plain slug
    is matched by joining against plugin_registry to avoid colliding with
    other job_id values (e.g. core jobs).

    Falls back to plugin_settings._last_sync for plugins that still write
    the legacy key directly.
    """
    result: dict[str, str] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Primary: job_runs. Match either 'sync:<slug>' (legacy) or
            # plain '<slug>' (new scheduler). The plain-slug arm joins
            # against plugin_registry so we don't accidentally pick up
            # arbitrary job_id values.
            cur.execute(
                """
                SELECT plugin_id, MAX(completed_at) AS last_completed
                FROM (
                    SELECT split_part(job_id, ':', 2) AS plugin_id, completed_at
                    FROM job_runs
                    WHERE job_id LIKE 'sync:%'
                      AND status = 'success'
                      AND completed_at IS NOT NULL
                    UNION ALL
                    SELECT jr.job_id AS plugin_id, jr.completed_at
                    FROM job_runs jr
                    INNER JOIN plugin_registry pr ON pr.slug = jr.job_id
                    WHERE jr.status = 'success'
                      AND jr.completed_at IS NOT NULL
                ) AS combined
                WHERE plugin_id IS NOT NULL AND plugin_id != ''
                GROUP BY plugin_id
                """
            )
            for plugin_id, last_completed in cur.fetchall():
                if plugin_id and last_completed:
                    result[plugin_id] = last_completed.isoformat()

            # Fallback: legacy _last_sync for plugins that haven't migrated.
            # Only fill in entries we don't already have from job_runs, OR
            # where the legacy value is newer than the job_runs value.
            cur.execute(
                "SELECT plugin_id, value FROM plugin_settings WHERE key = '_last_sync'"
            )
            for plugin_id, value in cur.fetchall():
                if not plugin_id:
                    continue
                ts = None
                if isinstance(value, dict):
                    ts = value.get("timestamp")
                elif isinstance(value, str):
                    ts = value
                if not ts:
                    continue
                existing = result.get(plugin_id)
                if existing is None or str(ts) > existing:
                    result[plugin_id] = str(ts)
    except Exception:
        pass
    return result


def _plugin_sync_jobs(schedule_entries: list[dict]) -> list[dict]:
    """Build a job entry for every installed plugin that ships src/sync.py.

    B150 (v0.9.3.2): plugin scheduling is now driven by the v0.9.3 scheduler,
    not pm2/crontab. We read sync_schedule_registry for cron_active +
    cron_source, and plugin_settings._sync_schedule (the key B148's
    override endpoint writes) for override values. The legacy pm2/crontab
    grep path stays for core jobs (alert-runner, health-monitor) but is no
    longer consulted for plugin sync jobs.

    The `schedule_entries` parameter is kept in the signature for back-compat
    with callers, but no longer used in plugin scheduling decisions.
    """
    del schedule_entries  # unused — plugin scheduling moved to sync_schedule_registry
    import yaml as _yaml

    # Load overrides from plugin_settings._sync_schedule (B148 contract).
    # JSONB storage: a saved string round-trips as a Python str, but older
    # values may be raw text — accept both.
    overrides: dict[str, str] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT plugin_id, value FROM plugin_settings WHERE key = '_sync_schedule'"
            )
            for plugin_id, value in cur.fetchall():
                if isinstance(value, str) and value.strip():
                    overrides[plugin_id] = value.strip()
    except Exception:
        pass

    # Load registry rows: per-plugin scheduler state (B147).
    registry: dict[str, dict] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT plugin_id, cron_expression, cron_source, next_fire_at,
                       last_enqueued_at, last_run_id, last_error,
                       EXTRACT(EPOCH FROM (NOW() - updated_at))::int AS age_sec
                FROM sync_schedule_registry
                """
            )
            for row in cur.fetchall():
                registry[row[0]] = {
                    "cron_expression": row[1],
                    "cron_source": row[2],
                    "next_fire_at": row[3].isoformat() if row[3] else None,
                    "last_enqueued_at": row[4].isoformat() if row[4] else None,
                    "last_run_id": row[5],
                    "last_error": row[6],
                    "age_sec": row[7],
                }
    except Exception:
        pass

    last_sync_map = _plugin_last_sync_map()

    jobs = []
    for plugin_dir in sorted([*INSTALLED_DIR.glob("*/"), *COMMUNITY_DIR.glob("*/")]):
        # B202: honor manifest sync.script; the prior hardcoded src/sync.py
        # check excluded plugins like plugin-plausible whose script is
        # slug-prefixed.
        sync_file, sync_rel = resolve_sync_script(plugin_dir)
        if not sync_file.exists():
            continue
        slug = plugin_dir.name

        # Read schedule from manifest
        manifest_schedule = "0 6 * * *"
        manifest_path = plugin_dir / "plugin.yaml"
        if manifest_path.exists():
            try:
                manifest = _yaml.safe_load(manifest_path.read_text())
                sync_cfg = manifest.get("sync") or {}
                manifest_schedule = sync_cfg.get("schedule", manifest_schedule)
            except Exception:
                pass

        schedule = overrides.get(slug, manifest_schedule)
        label = _SCHEDULE_LABELS.get(schedule, schedule)

        last_run = last_sync_map.get(slug)
        status = _classify_status(last_run, schedule)
        last_run_label = f"Last run: {last_run}" if last_run else "Never run"

        # B150: cron_active comes from the registry's freshness, not pm2/crontab.
        # Same semantics as the schedule_active predicate: row exists, age <5 min,
        # no last_error.
        reg = registry.get(slug)
        if reg and reg["age_sec"] is not None and reg["age_sec"] < 300 and not reg["last_error"]:
            is_active = True
            cron_source = reg["cron_source"]  # 'manifest' or 'override'
        else:
            is_active = False
            cron_source = None

        # Pull the plugin's display name for a friendlier owner label
        display_name = slug.replace("-", " ").title()
        if manifest_path.exists():
            try:
                m = _yaml.safe_load(manifest_path.read_text())
                display_name = m.get("display_name") or display_name
            except Exception:
                pass

        # B202: cmd reflects the actual resolved script path, not src/sync.py.
        cmd = f"plugins/installed/{slug}/{sync_rel}"
        jobs.append({
            "id": f"{slug}-sync",
            "name": f"{display_name} Sync",
            "description": f"Data sync for the {slug} plugin",
            "owner": f"Plugin: {display_name}",
            "command": cmd,
            "recommended_schedule": schedule,
            "recommended_label": label,
            "manifest_schedule": manifest_schedule,
            "override": slug in overrides,
            "last_run": last_run,
            "last_run_label": last_run_label,
            "status": status,
            "cron_active": is_active,
            "cron_source": cron_source,
            # B150: surface scheduler state for the UI.
            "scheduler": reg,
        })
    return jobs


# ── List endpoint ─────────────────────────────────────────────────────


@router.get(
    "",
    operation_id="jobs.list",
    response_model=JobsListResponse,
    response_model_exclude_none=True,
    summary="List all scheduled jobs with status + cron source",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.read permission."},
    },
)
def list_jobs(_: None = Depends(requires("jobs.read"))):
    """Return all known scheduled jobs with status + schedule source.

    Aggregates plugin sync jobs (one per installed plugin), the alert
    runner, and the system health monitor. `cron_source` distinguishes
    PM2-scheduled vs crontab-scheduled deployments — the frontend uses
    it to show the right "how to schedule" hint.
    """
    crontab_entries = _crontab_entries()
    pm2_entries = _pm2_cron_entries()
    schedule_entries = crontab_entries + pm2_entries
    cron_source = _classify_cron_source(crontab_entries, pm2_entries)

    jobs = _plugin_sync_jobs(schedule_entries)

    # Alert runner (core)
    alerts_last = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(triggered_at) FROM alert_events")
            row = cur.fetchone()
            alerts_last = str(row[0]) if row and row[0] else None
    except Exception:
        pass

    alerts_active, alerts_src = _cron_active(
        ["run_alerts", "alerts"],
        schedule_entries,
    )
    jobs.append({
        "id": "alerts-runner",
        "name": "Alert Runner",
        "description": "Check all enabled alerts and fire notifications",
        "owner": "Core",
        "command": "apps/worker/src/run_alerts.py",
        "recommended_schedule": "0 * * * *",
        "recommended_label": "Every hour",
        "last_run": alerts_last,
        "last_run_label": f"Last alert: {alerts_last}" if alerts_last else "Never run",
        "status": _classify_status(alerts_last, "0 * * * *"),
        "cron_active": alerts_active,
        "cron_source": alerts_src,
    })

    # System health monitor (writes to health_log every 5 min via PM2 cron)
    health_last = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(created_at) FROM health_log")
            row = cur.fetchone()
            health_last = str(row[0]) if row and row[0] else None
    except Exception:
        pass

    health_active, health_src = _cron_active(
        ["health/record", "health-monitor"],
        schedule_entries,
    )
    jobs.append({
        "id": "health-monitor",
        "name": "System Health Check",
        "description": "Record a system health snapshot for the /health-overview timeline",
        "owner": "Core",
        "command": "curl -X POST http://127.0.0.1:8000/api/health/record",
        "recommended_schedule": "*/5 * * * *",
        "recommended_label": "Every 5 minutes",
        "last_run": health_last,
        "last_run_label": f"Last check: {health_last}" if health_last else "Never run",
        "status": _classify_status(health_last, "*/5 * * * *"),
        "cron_active": health_active,
        "cron_source": health_src,
    })

    # P108: compute next_run_at for every job with a recommended_schedule.
    for j in jobs:
        j["next_run_at"] = _next_run_at(j.get("recommended_schedule", ""))

    return {
        "jobs": jobs,
        "crontab": crontab_entries,
        "pm2": pm2_entries,
        "has_crontab": len(crontab_entries) > 0,
        "has_pm2_cron": len(pm2_entries) > 0,
        "cron_source": cron_source,
    }


# ── Job run history ──────────────────────────────────────────────────

@router.get(
    "/runs",
    operation_id="jobs.runs.list",
    response_model=JobRunsListResponse,
    response_model_exclude_none=True,
    summary="List recent job runs",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.read permission."},
    },
)
async def list_job_runs(
    job_id: str | None = None,
    limit: int = 50,
    _: None = Depends(requires("jobs.read")),
):
    """List recent job runs, optionally filtered by job_id.

    Returns up to `limit` runs ordered by `started_at` DESC. Used by
    the System → Jobs page and the per-plugin Sync history block.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            if job_id:
                cur.execute("""
                    SELECT id, job_id, started_at, completed_at, status, duration_ms,
                           rows_written, error, source
                    FROM job_runs WHERE job_id = %s
                    ORDER BY started_at DESC LIMIT %s
                """, (job_id, limit))
            else:
                cur.execute("""
                    SELECT id, job_id, started_at, completed_at, status, duration_ms,
                           rows_written, error, source
                    FROM job_runs ORDER BY started_at DESC LIMIT %s
                """, (limit,))
            cols = [d[0] for d in cur.description]
            runs = []
            for row in cur.fetchall():
                r = dict(zip(cols, row))
                for k in ("started_at", "completed_at"):
                    if r.get(k) and hasattr(r[k], "isoformat"):
                        r[k] = r[k].isoformat()
                runs.append(r)
        return {"runs": runs}
    except Exception:
        return {"runs": []}


# ── B277 (v0.9.11.16): centralized job state dashboard ──────────────
#
# Backs /system/jobs's 4-section view (now / recent / upcoming /
# failing) with a single endpoint. Cached in-process for 30s like
# /api/system/resources; pass `?fresh=true` to bypass.

import time as _time_for_dashboard
from ..services import job_dashboard as _job_dashboard

_DASHBOARD_CACHE: dict = {"snapshot": None, "computed_at": 0.0}
_DASHBOARD_CACHE_TTL_S = 30.0


@router.get(
    "/dashboard",
    operation_id="jobs.dashboard",
    response_model=JobsDashboardResponse,
    response_model_exclude_none=True,
    summary="Centralized job state — running / recent / upcoming / failing (B277)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.read permission."},
    },
)
def get_jobs_dashboard(
    fresh: bool = False,
    _: None = Depends(requires("jobs.read")),
) -> dict:
    """Return the unified job-state snapshot rendered on /system/jobs.

    Sections:
      - now: currently-running + queued jobs with elapsed_ms and
        will_overlap_next (elapsed already exceeds the gap to next fire)
      - recent: last 12h of completed runs ordered by started_at DESC
      - upcoming: next 6h of scheduled fires with may_overlap predictions
      - failing: jobs with > 50% error rate (min 4 runs) over 24h

    Cached in-process for 30 seconds; pass `?fresh=true` to bypass.
    """
    now = _time_for_dashboard.monotonic()
    cached = _DASHBOARD_CACHE.get("snapshot")
    cached_age = now - _DASHBOARD_CACHE.get("computed_at", 0.0)

    if cached is not None and cached_age < _DASHBOARD_CACHE_TTL_S and not fresh:
        return cached

    snap = _job_dashboard.get_dashboard()
    _DASHBOARD_CACHE["snapshot"] = snap
    _DASHBOARD_CACHE["computed_at"] = now
    return snap


# ── P107 v0.8.2: cancel / pause / resume / single-run detail ────────
#
# All endpoints here are operator-facing and require analyst auth. They
# mutate job_runs directly — the jobs-worker polls status changes and
# acts (subprocess termination, re-enqueue after resume, etc).

from fastapi import HTTPException, Request  # noqa: E402  (late import to
                                              # avoid reshuffling existing imports)

# Terminal statuses — cannot be cancelled/paused/resumed further.
_TERMINAL_STATUSES = frozenset({"success", "error", "timeout", "cancelled", "skipped"})


def _get_run(run_id: int) -> dict | None:
    """Load a single job_runs row by id, or None."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, job_id, started_at, completed_at, status,
                       duration_ms, exit_code, rows_written, details,
                       error, source, progress, cancelled_at, paused_at,
                       claimed_by, claimed_at, heartbeat_at
                FROM job_runs WHERE id = %s
                """,
                (run_id,),
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if not row:
            return None
        r = dict(zip(cols, row))
        for k in ("started_at", "completed_at", "cancelled_at",
                  "paused_at", "claimed_at", "heartbeat_at"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
        return r
    except Exception:
        return None


@router.get(
    "/{run_id}",
    operation_id="jobs.run.detail",
    response_model=JobRunRow,
    response_model_exclude_none=True,
    summary="Detail for a single job run",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.read permission."},
        404: {"model": ErrorDetail, "description": "Run not found."},
    },
)
async def get_job_run(
    run_id: int,
    request: Request,
    _: None = Depends(requires("jobs.read")),
):
    """Return detail for a single job_runs row — status, progress, heartbeat."""
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")
    return run


@router.post(
    "/{run_id}/cancel",
    operation_id="jobs.run.cancel",
    response_model=JobRunControlResponse,
    summary="Cancel a queued or running job run",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.write permission."},
        404: {"model": ErrorDetail, "description": "Run not found."},
        409: {"model": ErrorDetail, "description": "Run is in a status that can't be cancelled."},
    },
)
async def cancel_job_run(
    run_id: int,
    request: Request,
    force: bool = False,
    _: None = Depends(requires("jobs.write")),
):
    """Cancel a queued or running run. Cooperative — the plugin sees the
    cancel via check_cancelled() on its next poll.

    - queued  → status='cancelled' (never ran)
    - running → status='cancelling' (plugin exits on next check_cancelled)
    - paused  → status='cancelled'
    - terminal (success/error/timeout/cancelled/skipped) → 200 no-op

    `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
    `cancelled` regardless of current status (skipping the cooperative
    `cancelling` state). Used for **orphaned runs** where the worker is
    confirmed gone — e.g. after a Postgres restart or scheduler crash
    that left rows in `'running'` without any process actively executing
    them. Without `?force=true`, those rows would hang in `cancelling`
    forever (no worker to observe the cancel).

    **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
    is passed against a `'running'` row whose `heartbeat_at` is fresh
    (worker heartbeated within the last 90 seconds), the request is
    refused with 409. The worker is alive — cooperative cancel will
    work, and force-cancel would create a status mismatch where the
    worker still thinks it's running. The dashboard frontend uses
    `JobsDashboardNowItem.worker_alive` to pick the right button
    automatically; this server-side check is the safety net.
    """
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    status = run["status"]
    if status in _TERMINAL_STATUSES:
        return {"ok": True, "changed": False, "status": status}

    # B277 v0.9.11.16.4: liveness-gated force. Worker writes
    # heartbeat_at every ~10s during a job run; if the heartbeat is
    # within 90s, the worker is alive and force-cancel would be unsafe.
    if force and status == "running":
        heartbeat_iso = run.get("heartbeat_at")
        if heartbeat_iso:
            try:
                hb = datetime.fromisoformat(str(heartbeat_iso).replace("Z", "+00:00"))
                if hb.tzinfo is None:
                    hb = hb.replace(tzinfo=timezone.utc)
                age_sec = (datetime.now(timezone.utc) - hb).total_seconds()
                if age_sec < 90:
                    raise HTTPException(
                        409,
                        f"Worker is still active for run {run_id} "
                        f"(last heartbeat {int(age_sec)}s ago, threshold 90s). "
                        f"Use cooperative cancel (omit ?force=true) — the worker "
                        f"will exit at its next checkpoint.",
                    )
            except HTTPException:
                raise
            except Exception:
                # If heartbeat parsing fails, treat as stale and allow force.
                pass

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            if force:
                # B277 v0.9.11.16.3: force-mark terminal regardless of
                # current state. Orphan-cleanup escape hatch (gated by
                # the liveness check above for running rows).
                new_status = "cancelled"
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = 'cancelled',
                        completed_at = COALESCE(completed_at, now()),
                        cancelled_at = COALESCE(cancelled_at, now()),
                        duration_ms = COALESCE(
                            duration_ms,
                            EXTRACT(EPOCH FROM (now() - started_at)) * 1000
                        ),
                        error = COALESCE(
                            error,
                            'force-cancelled (orphan cleanup) — worker confirmed gone'
                        )
                    WHERE id = %s
                      AND status NOT IN ('success','error','timeout','cancelled','skipped')
                    """,
                    (run_id,),
                )
            elif status == "running":
                new_status = "cancelling"
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = 'cancelling', cancelled_at = now()
                    WHERE id = %s AND status = 'running'
                    """,
                    (run_id,),
                )
            elif status in ("queued", "paused"):
                new_status = "cancelled"
                cur.execute(
                    """
                    UPDATE job_runs
                    SET status = 'cancelled',
                        completed_at = now(),
                        cancelled_at = now(),
                        duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000
                    WHERE id = %s AND status IN ('queued', 'paused')
                    """,
                    (run_id,),
                )
            elif status == "cancelling":
                # Already cancelling — nothing to do, but not a no-op from
                # the caller's perspective.
                new_status = "cancelling"
            else:
                raise HTTPException(409, f"Cannot cancel run in status {status!r}")
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Cancel failed: {e.__class__.__name__}")

    return {"ok": True, "changed": True, "status": new_status}


@router.post(
    "/{run_id}/pause",
    operation_id="jobs.run.pause",
    response_model=JobRunControlResponse,
    summary="Pause a queued or running job run",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.write permission."},
        404: {"model": ErrorDetail, "description": "Run not found."},
        409: {"model": ErrorDetail, "description": "Run is in a status that can't be paused."},
    },
)
async def pause_job_run(
    run_id: int,
    request: Request,
    _: None = Depends(requires("jobs.write")),
):
    """Pause a running run. Plugin exits at next check_cancelled(); the
    run lands in 'paused' status (not 'cancelled') so resume re-queues it.

    - running → status='paused' (via cancelling — plugin exits cleanly)
    - queued  → status='paused' directly (never claimed)
    """
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    status = run["status"]
    if status == "paused":
        return {"ok": True, "changed": False, "status": "paused"}
    if status not in ("queued", "running"):
        raise HTTPException(409, f"Cannot pause run in status {status!r}")

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # For queued rows: just mark paused. Worker will ignore them
            # (only claims 'queued'). For running: mark paused + cancelling
            # so the plugin exits; worker observes 'paused' on next write.
            #
            # Simplest model: always mark 'paused' with paused_at. The
            # worker loop interprets 'paused' as cancel-cooperatively-then-
            # stop-without-advancing.
            cur.execute(
                """
                UPDATE job_runs
                SET status = 'paused',
                    paused_at = now()
                WHERE id = %s AND status IN ('queued', 'running')
                """,
                (run_id,),
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(500, f"Pause failed: {e.__class__.__name__}")

    return {"ok": True, "changed": True, "status": "paused"}


@router.post(
    "/{run_id}/resume",
    operation_id="jobs.run.resume",
    response_model=JobRunControlResponse,
    summary="Re-queue a paused job run",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.write permission."},
        404: {"model": ErrorDetail, "description": "Run not found."},
        409: {"model": ErrorDetail, "description": "Only paused runs can be resumed."},
    },
)
async def resume_job_run(
    run_id: int,
    request: Request,
    _: None = Depends(requires("jobs.write")),
):
    """Re-queue a paused run so the worker picks it up fresh.

    Only valid transition: paused → queued.
    """
    run = _get_run(run_id)
    if run is None:
        raise HTTPException(404, f"Run {run_id} not found")

    if run["status"] != "paused":
        raise HTTPException(409, f"Can only resume paused runs (current: {run['status']!r})")

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE job_runs
                SET status = 'queued',
                    paused_at = NULL,
                    claimed_by = NULL,
                    claimed_at = NULL
                WHERE id = %s AND status = 'paused'
                """,
                (run_id,),
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(500, f"Resume failed: {e.__class__.__name__}")

    return {"ok": True, "changed": True, "status": "queued"}


# ── P108: fire-now ───────────────────────────────────────────────────

@router.post(
    "/{job_id}/fire-now",
    operation_id="jobs.fire_now",
    response_model=FireNowResponse,
    response_model_exclude_none=True,
    summary="Immediately trigger a schedulable job",
    responses={
        400: {"model": ErrorDetail, "description": "Job is not fire-now capable (core jobs run on PM2)."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the jobs.write permission."},
    },
)
async def fire_now(
    job_id: str,
    request: Request,
    _: None = Depends(requires("jobs.write")),
):
    """Immediately trigger a schedulable job.

    For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
    the manual-trigger endpoint which honors execution_mode (async vs
    sync). For core jobs (alerts-runner, health-monitor), this is a
    no-op for now — their schedulers are external (PM2 cron_restart).

    job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').
    """

    # Plugin sync jobs: id ends with '-sync'
    if job_id.endswith("-sync"):
        plugin_id = job_id[: -len("-sync")]
        from .sync import trigger_sync, SyncRequest
        # Build a request for incremental mode. Reuse the existing handler
        # so we get async enqueue / sync subprocess behavior for free.
        sync_req = SyncRequest(mode="incremental")
        resp = await trigger_sync(plugin_id, request=request, req=sync_req)
        # Return the sync response verbatim; client already knows how to
        # read {status, run_id, enqueued, ...}.
        return resp

    # Core jobs are scheduled externally — operator can't fire them via
    # this endpoint. Tell them clearly.
    raise HTTPException(
        400,
        f"Job {job_id!r} is not fire-now capable. "
        f"Core jobs (alerts-runner, health-monitor) run on their PM2 schedule.",
    )
