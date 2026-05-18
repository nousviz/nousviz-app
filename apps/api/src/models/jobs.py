"""B215 (v0.9.10.2): typed responses for /api/jobs/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobSchedulerState(BaseModel):
    """sync_schedule_registry row attached to plugin sync jobs (B150).

    Surfaced under JobEntry.scheduler — tells the operator UI whether
    the v0.9.3 scheduler is actively tracking this plugin and when it
    last enqueued a run.
    """
    cron_expression: Optional[str] = None
    cron_source: Optional[str] = Field(default=None, description="'manifest' | 'override'.")
    next_fire_at: Optional[str] = None
    last_enqueued_at: Optional[str] = None
    last_run_id: Optional[int] = None
    last_error: Optional[str] = None
    age_sec: Optional[int] = Field(
        default=None,
        description="Seconds since the registry row was last touched. <300 means scheduler is alive.",
    )


class JobEntry(BaseModel):
    """Single row in /api/jobs response — one schedulable job.

    Plugin sync jobs carry the additional fields `manifest_schedule`,
    `override`, and `scheduler` (B150 — surfacing the v0.9.3 scheduler
    state to the operator UI). Core jobs (alerts-runner, health-monitor)
    omit those.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Job slug, e.g. 'starter-plugin-sync', 'alerts-runner'.")
    name: str
    description: str
    owner: str = Field(..., description="'Core' for built-in jobs, plugin display name otherwise.")
    command: str
    recommended_schedule: str = Field(..., description="Cron expression suggested for this job.")
    recommended_label: Optional[str] = Field(default=None, description="Human-readable label for the cron.")
    last_run: Optional[str] = None
    last_run_label: Optional[str] = None
    status: str = Field(..., description="'healthy' | 'stale' | 'never' | etc.")
    cron_active: bool = Field(..., description="True iff a cron entry was found scheduling this job.")
    cron_source: Optional[str] = Field(default=None, description="'pm2' | 'crontab' | 'manifest' | 'override' | None.")
    next_run_at: Optional[str] = None
    manifest_schedule: Optional[str] = Field(
        default=None,
        description="Cron from plugin.yaml. Plugin sync jobs only.",
    )
    override: Optional[bool] = Field(
        default=None,
        description="True iff a per-plugin schedule override is set (B148). Plugin sync jobs only.",
    )
    scheduler: Optional[JobSchedulerState] = Field(
        default=None,
        description="v0.9.3 scheduler state for plugin sync jobs. Null for core jobs.",
    )


class CrontabEntry(BaseModel):
    """A single line from the system crontab as parsed by jobs.py."""
    model_config = ConfigDict(extra="allow")

    schedule: str
    command: str


class JobsListResponse(BaseModel):
    """GET /api/jobs — every known scheduled job + crontab/PM2 metadata.

    `cron_source` flips between 'crontab' and 'pm2' to drive the
    frontend's "how to schedule" hint.
    """
    jobs: list[JobEntry]
    crontab: list[CrontabEntry] = Field(
        default_factory=list,
        description="System crontab entries containing 'nousviz' — empty on PM2 deployments.",
    )
    pm2: list[CrontabEntry] = Field(
        default_factory=list,
        description="PM2-managed processes with cron_restart — empty on crontab-only deployments.",
    )
    has_crontab: bool
    has_pm2_cron: bool
    cron_source: str = Field(..., description="'pm2' | 'crontab' | 'mixed' | 'none'.")


class JobRunRow(BaseModel):
    """A single job_runs row — used by /api/jobs/runs and /api/jobs/{run_id}.

    Datetimes are ISO-8601 strings. Extra fields are allowed because the
    detail endpoint returns more columns than the list endpoint
    (claimed_by, heartbeat_at, progress, etc).
    """
    model_config = ConfigDict(extra="allow")

    id: int
    job_id: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = Field(..., description="'queued' | 'running' | 'success' | 'error' | 'timeout' | 'cancelled' | 'cancelling' | 'paused' | 'skipped'.")
    duration_ms: Optional[int] = None
    rows_written: Optional[int] = None
    error: Optional[str] = None
    source: Optional[str] = None
    exit_code: Optional[int] = None
    details: Optional[dict[str, Any]] = None
    progress: Optional[dict[str, Any]] = None
    cancelled_at: Optional[str] = None
    paused_at: Optional[str] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    heartbeat_at: Optional[str] = None


class JobRunsListResponse(BaseModel):
    """GET /api/jobs/runs — recent job runs."""
    runs: list[JobRunRow]


class JobRunControlResponse(BaseModel):
    """POST /api/jobs/{run_id}/{cancel|pause|resume} response.

    `changed` is True when the operation moved the run into a new
    status; False when the operation was a no-op (e.g. cancelling an
    already-terminal run).
    """
    ok: bool = True
    changed: bool
    status: str = Field(..., description="The run's status after the operation.")


class JobsDashboardNowItem(BaseModel):
    """B277: a row in the dashboard's NOW section — a currently-running
    or queued job with elapsed time + collision-prediction context.

    v0.9.11.16.4 adds heartbeat liveness so callers can distinguish
    a live worker from an orphaned 'running' row.
    """
    id: int
    job_id: str
    status: str = Field(..., description="'running' | 'queued' | 'cancelling'.")
    started_at: str
    elapsed_ms: int
    schedule_cron: Optional[str] = None
    next_fire_at: Optional[str] = None
    will_overlap_next: bool = Field(
        default=False,
        description="True when elapsed already exceeds (next_fire_at - started_at).",
    )
    heartbeat_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the worker's most recent heartbeat write. Null until the row is claimed.",
    )
    heartbeat_age_sec: Optional[int] = Field(
        default=None,
        description="Seconds since heartbeat_at (server-computed). Null when heartbeat_at is null.",
    )
    worker_alive: bool = Field(
        default=False,
        description="True iff the worker heartbeated within the last 90s. Force-cancel is gated on this being false for running rows.",
    )


class JobsDashboardRecentItem(BaseModel):
    """B277: a completed job_runs row from the recent-history window."""
    id: int
    job_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error_short: Optional[str] = Field(
        default=None,
        description="First 200 chars of the run's error column, or null.",
    )


class JobsDashboardUpcomingItem(BaseModel):
    """B277: an upcoming scheduled fire with collision prediction."""
    plugin_id: str
    schedule_cron: str
    next_fire_at: str
    ms_until_fire: int
    avg_duration_ms: Optional[int] = None
    may_overlap: bool = Field(
        default=False,
        description="True when avg_duration_ms exceeds 90% of ms_until_fire.",
    )


class JobsDashboardFailingItem(BaseModel):
    """B277 (v0.9.11.16.1): a job with ANY errors in the last 24h.

    Threshold widened from > 50% error rate to errors > 0 per operator
    UX feedback: sporadic failures matter and should surface for
    investigation. Ordered server-side by `last_error_at` DESC so the
    frontend can lead with the most recent failure.
    """
    job_id: str
    runs_24h: int
    errors_24h: int
    error_rate_pct: float
    last_error: Optional[str] = None
    last_error_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the most recent error — anchors the deep-link into /system/logs.",
    )


class JobsDashboardResponse(BaseModel):
    """B277: GET /api/jobs/dashboard — 4-section centralized job state.

    Each section is independently sized, so callers can render whichever
    blocks have content. `collected_at` lets the client tell when a
    cached vs fresh snapshot is being shown.
    """
    collected_at: str
    now: list[JobsDashboardNowItem]
    recent: list[JobsDashboardRecentItem]
    upcoming: list[JobsDashboardUpcomingItem]
    failing: list[JobsDashboardFailingItem]


class FireNowResponse(BaseModel):
    """POST /api/jobs/{job_id}/fire-now response.

    For plugin sync jobs, this returns the same shape as POST
    /api/plugins/{id}/sync (the SyncResponse from B205). The fields
    here mirror that shape with `extra='allow'` to absorb any keys the
    underlying handler adds.
    """
    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="'queued' | 'running' | 'skipped' | etc.")
    enqueued: Optional[bool] = None
    run_id: Optional[int] = None
    output: Optional[str] = None
    exit_code: Optional[int] = None
