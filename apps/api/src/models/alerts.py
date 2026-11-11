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
    # P230: where the data is and how the user mapped it.
    source_id: Optional[str] = Field(default=None, description="pg:<table> | plugin:<id>:<dataset> | conn:<uuid> | query:<plugin>:<id>.")
    source_kind: Optional[str] = None
    db_engine: Optional[str] = None
    connection_id: Optional[str] = None
    date_column: Optional[str] = None
    value_kind: Optional[str] = Field(default=None, description="'column' | 'count' | 'ratio'.")
    denominator: Optional[str] = None
    denominator_aggregation: Optional[str] = None
    group_by_columns: Optional[list[str]] = None
    filters: Optional[list[dict[str, Any]]] = None
    min_volume_column: Optional[str] = None
    min_volume: Optional[float] = None
    currency_column: Optional[str] = None
    query_id: Optional[str] = None
    query_params: Optional[dict[str, Any]] = None
    last_run_at: Optional[str] = None
    last_status: Optional[str] = Field(default=None, description="'fired' | 'ok' | 'no_data' | 'error'.")
    last_error: Optional[str] = None
    last_duration_ms: Optional[int] = None
    last_rows_checked: Optional[int] = None


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
        description="Column metadata when known up front; otherwise load it from /api/alerts/sources/columns.",
    )
    engine: str = Field(default="postgres", description="Where the data is: 'postgres' | 'clickhouse' | 'mysql'.")
    available: bool = Field(default=True, description="False when the engine has no usable connection or the plugin keeps the dataset out of direct alerts.")
    unavailable_reason: Optional[str] = None
    needs_table: bool = Field(default=False, description="True for connections: pick a table with /api/alerts/sources/tables.")


class AlertQueryEntry(BaseModel):
    """A ready-made alert from a plugin's alerts.yaml."""
    model_config = ConfigDict(extra="allow")

    id: str
    query_id: str
    plugin_id: str
    label: str
    description: str = ""
    engine: str
    params: dict[str, Any] = Field(default_factory=dict)
    default_condition: dict[str, Any] = Field(default_factory=dict)
    default_period: str = "yesterday"
    value_label: str = ""
    sql: str = ""
    available: bool = True
    unavailable_reason: Optional[str] = None
    error: Optional[str] = None


class AlertSourcesResponse(BaseModel):
    """GET /api/alerts/sources — grouped by origin (postgres / connections / plugins / ready-made queries)."""
    postgres: list[AlertSourceEntry]
    connections: list[AlertSourceEntry]
    plugins: list[AlertSourceEntry]
    queries: list[AlertQueryEntry] = Field(default_factory=list)


class AlertSourceColumn(BaseModel):
    name: str
    type: str
    kind: str = Field(..., description="'date' | 'datetime' | 'number' | 'text' | 'bool' | 'other'.")


class AlertSourceColumnsResponse(BaseModel):
    """GET /api/alerts/sources/columns — the real columns of a source table."""
    source_id: str
    engine: str
    table: str
    database: Optional[str] = None
    table_engine: Optional[str] = Field(default=None, description="e.g. ReplacingMergeTree (read with FINAL).")
    columns: list[AlertSourceColumn]
    suggested_date_column: Optional[str] = None
    suggested_currency_column: Optional[str] = None


class AlertSourceTablesResponse(BaseModel):
    """GET /api/alerts/sources/tables — tables on a registered connection."""
    source_id: str
    engine: str
    tables: list[str]


class AlertSourceValuesResponse(BaseModel):
    """GET /api/alerts/sources/values — the most common values of a column, for filters."""
    column: str
    values: list[Any]


class AlertEvaluationRow(BaseModel):
    group: str
    current_value: float
    baseline: float
    change_pct: Optional[float] = None
    fired: bool


class AlertPreviewResponse(BaseModel):
    """POST /api/alerts/preview — evaluate an unsaved alert. Nothing is sent or recorded."""
    status: str = Field(..., description="'ok' | 'no_data' | 'error'.")
    engine: str
    sql: str = ""
    rows_checked: int = 0
    elapsed_ms: int = 0
    error: Optional[str] = None
    fired: bool = False
    fired_count: int = 0
    rows: list[AlertEvaluationRow] = Field(default_factory=list)
    period: Optional[list[str]] = Field(default=None, description="[start, end) of the checked period.")


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
    # P230 / B345: the same evaluation the scheduled run does.
    status: Optional[str] = None
    engine: Optional[str] = None
    sql: Optional[str] = None
    elapsed_ms: Optional[int] = None
    rows: Optional[list[AlertEvaluationRow]] = None


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
