"""B215 (v0.9.10.2): typed responses for /api/admin/* routes (cli + logs)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CliResponse(BaseModel):
    """POST /api/admin/cli — operator CLI command output.

    `ok` is True only when the command parsed and the handler returned
    without raising. The `output` field is the human-readable text the
    UI prints in the CLI panel.
    """
    output: str
    ok: bool


class LogEntry(BaseModel):
    """A single app_logs row as returned by /api/admin/logs.

    `actor_email` and `run_status` are joined in from users / job_runs.
    `actor_user_id` is the actor's UUID as a string (or null when the
    log entry has no associated actor — e.g. system-emitted events).
    """
    id: int
    level: str = Field(..., description="'info' | 'warning' | 'error' | etc.")
    source: str = Field(..., description="Log source label, e.g. 'plugin', 'plugin_route', 'rbac', 'sync'.")
    message: str
    detail: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured JSONB detail payload — shape depends on the source.",
    )
    created_at: Optional[str] = None
    plugin_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    run_id: Optional[int] = None
    actor_email: Optional[str] = None
    run_status: Optional[str] = None


class LogsListResponse(BaseModel):
    """GET /api/admin/logs — paginated log feed.

    Pagination is keyset on `id` descending. When `next_cursor` is
    non-null, pass it back as the `cursor` query param to fetch the
    next page. A null cursor means the response was shorter than
    `limit` and there are no more rows.
    """
    logs: list[LogEntry]
    next_cursor: Optional[int] = Field(
        default=None,
        description="ID of the last entry; pass back as ?cursor=… to paginate.",
    )


class LogFilterUser(BaseModel):
    """Distinct actor for the /system/logs filter dropdown."""
    id: str
    email: Optional[str] = None


class LogFiltersResponse(BaseModel):
    """GET /api/admin/logs/filters — distinct values for dropdown filters.

    Limited to events from the last 30 days so the dropdowns don't
    accumulate stale plugin slugs or deleted users.
    """
    plugins: list[str]
    users: list[LogFilterUser]
