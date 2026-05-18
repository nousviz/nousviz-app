"""B216 (v0.9.10.3): typed responses for /api/activity/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ActivityEventRow(BaseModel):
    """A single activity_events row.

    Has many optional columns added over time; extra='allow' keeps the
    model honest as new columns land.
    """
    model_config = ConfigDict(extra="allow")

    id: Optional[Any] = None
    action: Optional[str] = None
    category: Optional[str] = None
    page_path: Optional[str] = None
    plugin_id: Optional[str] = None
    detail: Optional[Any] = None
    duration_ms: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[str] = None


class ActivityLogResponse(BaseModel):
    """POST /api/activity — event recorded."""
    status: str = Field(default="logged", description="Always 'logged' on success.")


class ActivityListResponse(BaseModel):
    """GET /api/activity — recent events, newest first."""
    events: list[ActivityEventRow]
    count: int


class PageViewEntry(BaseModel):
    """Resolved page view used by the dashboard-usage analytics."""
    path: str
    label: str
    views: int


class PluginActivityEntry(BaseModel):
    """Aggregate event count for one plugin."""
    plugin: str = Field(..., description="Display name when known, slug otherwise.")
    events: int


class DailyActivityEntry(BaseModel):
    """One row of the daily activity histogram."""
    date: str
    events: int


class DashboardUsageResponse(BaseModel):
    """GET /api/activity/dashboard-usage — analytics aggregate.

    `unused_dashboards` enumerates manifest-declared dashboard paths
    that received zero page_view events in the period.
    """
    period_days: int
    total_events: int
    page_views: list[PageViewEntry]
    plugin_activity: list[PluginActivityEntry]
    action_breakdown: dict[str, int]
    daily_activity: list[DailyActivityEntry]
    unused_dashboards: list[str]


class TimePerPageEntry(BaseModel):
    """Per-page time-spent estimate."""
    path: str
    minutes: float


class UserAnalyticsResponse(BaseModel):
    """GET /api/activity/analytics — admin analytics overview.

    `devices`, `browsers`, `ip_activity`, `hourly_distribution` are
    histogram-style maps keyed by the categorical value; treated as
    open-ended dicts since the keys are inferred from user-agent / IP /
    timestamp parsing.
    """
    period_days: int
    total_events: int
    total_page_views: int
    estimated_time_minutes: float
    estimated_time_display: str
    sessions: int
    avg_session_minutes: float
    devices: dict[str, int]
    browsers: dict[str, int]
    unique_ips: list[str]
    ip_activity: dict[str, int]
    peak_hour: str
    hourly_distribution: dict[str, int]
    time_per_page: list[TimePerPageEntry]
