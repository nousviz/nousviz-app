"""B216 (v0.9.10.3): typed responses for /api/alerts/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertRow(BaseModel):
    """A single alert_rules row.

    extra='allow' covers any future columns and the human-readable
    `frequency_label` / `period_label` injected by `_serialize_alert`.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    label: str
    description: Optional[str] = None
    plugin_id: str
    dataset: str
    metric: str
    aggregation: Optional[str] = None
    condition_type: Optional[str] = None
    threshold: Optional[float] = None
    compare_to: Optional[str] = None
    scope: Optional[str] = None
    group_by: Optional[str] = None
    scope_filters: Optional[dict[str, Any]] = None
    check_frequency: Optional[str] = None
    check_period: Optional[str] = None
    cooldown_hours: Optional[int] = None
    min_baseline: Optional[float] = None
    notify_channels: Optional[list[str]] = None
    enabled: Optional[bool] = None
    is_template: Optional[bool] = None
    last_triggered: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    frequency_label: Optional[str] = Field(
        default=None,
        description="Human-readable injection — 'Runs every hour', 'Runs once a day', etc.",
    )
    period_label: Optional[str] = None


class AlertsListResponse(BaseModel):
    """GET /api/alerts — alert configs, newest-first."""
    alerts: list[AlertRow]
    count: int


class AlertColumn(BaseModel):
    """A column in the alert-source schema dropdown."""
    name: str
    type: str


class AlertSourceEntry(BaseModel):
    """Single source entry under postgres / connections / plugins."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    source_type: str = Field(..., description="'postgres' | 'plugin_postgres' | 'plugin' | 'connection'.")
    source_label: str
    plugin_id: Optional[str] = None
    table: Optional[str] = None
    columns: list[AlertColumn] = Field(
        default_factory=list,
        description="Column metadata when introspectable (postgres + plugin_postgres); empty for connection sources.",
    )


class AlertSourcesResponse(BaseModel):
    """GET /api/alerts/sources — grouped by origin (postgres / connections / plugins)."""
    postgres: list[AlertSourceEntry]
    connections: list[AlertSourceEntry]
    plugins: list[AlertSourceEntry]


class AlertDeleteResponse(BaseModel):
    """DELETE /api/alerts/{alert_id}."""
    status: str = Field(default="deleted", description="Always 'deleted' on success.")


class AlertTestTriggeredRow(BaseModel):
    """A single triggered evaluation in the test-run response."""
    model_config = ConfigDict(extra="allow")


class AlertTestResponse(BaseModel):
    """POST /api/alerts/{alert_id}/test — dry-run evaluation result.

    `error` is set when the alert worker module isn't importable or the
    evaluation raised; otherwise `fired` + `rows_checked` + `triggered_rows`
    describe the test outcome.
    """
    alert_id: str
    fired: Optional[bool] = None
    message: Optional[str] = None
    rows_checked: Optional[int] = None
    triggered_rows: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Up to 5 rows that would have triggered.",
    )
    error: Optional[str] = None


class AlertSparklineDay(BaseModel):
    """Per-day cell in the sparkline."""
    date: str
    count: int
    score: Optional[str] = Field(
        default=None,
        description="Dominant semantic score for the day: 'useful' | 'neutral' | 'useless'.",
    )


class AlertSparklineResponse(BaseModel):
    """GET /api/alerts/{alert_id}/sparkline — last N days of trigger activity."""
    alert_id: str
    alert_label: str
    check_frequency: Optional[str] = None
    frequency_label: Optional[str] = None
    check_period: Optional[str] = None
    period_label: Optional[str] = None
    cooldown_hours: Optional[int] = None
    days: list[AlertSparklineDay]
    total_triggers: int
    semantic_summary: dict[str, int] = Field(
        ...,
        description="Counts keyed by 'useful' | 'neutral' | 'useless'.",
    )
