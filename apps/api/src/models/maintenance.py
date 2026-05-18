"""B279 (v0.9.11.17): typed responses for /api/maintenance/* routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RetentionPolicyState(BaseModel):
    """One row in the /settings/maintenance retention table.

    `rows_total` and `rows_would_prune` are computed live (cached at
    request time, no caching layer above) so the operator sees an
    accurate "click 'Run now' and N rows will be deleted" preview.
    """
    key: str = Field(..., description="Canonical policy identifier (e.g. 'app_logs', 'job_runs:success').")
    table: str = Field(..., description="SQL table the policy prunes.")
    field: str = Field(..., description="Timestamp field used for the retention cutoff.")
    description: str = Field(..., description="Human-readable summary of what the policy keeps.")
    retention_days: int = Field(..., ge=0, description="Current retention threshold in days. 0 means immediate purge of rows matching `additional_where`.")
    paused: bool = Field(..., description="When true, the cron worker skips this policy. Default for every policy at install.")
    rows_total: int = Field(..., description="Current total rows in the policy's scope (bounded by additional_where if any).")
    rows_would_prune: int = Field(..., description="Rows that exceed the retention threshold and would be deleted on the next run.")
    last_run_at: Optional[str] = None
    last_run_rows_deleted: Optional[int] = None
    last_run_error: Optional[str] = None
    updated_at: Optional[str] = None


class RetentionListResponse(BaseModel):
    """GET /api/maintenance/retention — every policy + live state."""
    policies: list[RetentionPolicyState]
    collected_at: str = Field(..., description="ISO timestamp when this snapshot was assembled.")


class UpdateRetentionPolicyBody(BaseModel):
    """PUT /api/maintenance/retention/{policy_key} body.

    Either field may be omitted; pass only what's changing.
    """
    retention_days: Optional[int] = Field(default=None, ge=0, le=3650, description="New retention threshold (0 means immediate purge of additional_where matches).")
    paused: Optional[bool] = Field(default=None, description="True to pause the policy; false to activate.")


class RetentionRunResponse(BaseModel):
    """POST /api/maintenance/retention/{policy_key}/run response."""
    policy_key: str
    rows_deleted: int
    duration_ms: int


class RetentionRunAllResponse(BaseModel):
    """POST /api/maintenance/retention/run-all response."""
    summary: dict[str, int | str] = Field(
        ...,
        description="Per-policy outcome. int = rows_deleted; 'paused' = skipped; 'error: <type>' = failed.",
    )
    duration_ms: int


# ── B274 (v0.9.11.20): diagnostic alert subscriptions ───────────────


class DiagnosticAlertSubscription(BaseModel):
    """One outbound webhook + its diagnostic-alert subscription state.

    v0.9.11.24 (B283) renamed `webhook_slug` → `webhook_id` and added
    `channel_type`. Existing slug-keyed subscriptions were backfilled
    by migration 070; the API now exposes the UUID directly.
    """
    webhook_id: str = Field(..., description="webhook_endpoints.id (UUID).")
    name: str
    url: Optional[str] = None
    is_active: bool
    channel_type: str = Field(
        default="generic",
        description="Channel type from webhook_endpoints: generic / slack / discord / teams.",
    )
    subscribed: bool = Field(
        ...,
        description="True iff the operator has explicitly subscribed this webhook to diagnostic alerts.",
    )
    updated_at: Optional[str] = None


class DiagnosticAlertSubscriptionListResponse(BaseModel):
    """GET /api/maintenance/diagnostic-alerts/subscriptions."""
    subscriptions: list[DiagnosticAlertSubscription]


class UpdateDiagnosticAlertSubscriptionBody(BaseModel):
    """PUT /api/maintenance/diagnostic-alerts/subscriptions/{webhook_id}."""
    enabled: bool


class DiagnosticAlertTestResponse(BaseModel):
    """POST /api/maintenance/diagnostic-alerts/test."""
    delivered: int = Field(..., description="Webhooks the synthetic payload reached successfully.")
    subscribed_webhooks: int = Field(..., description="Total currently-subscribed webhooks.")


# ── B284 (v0.9.11.23): per-job-run failure alert subscriptions ──────


class JobAlertSubscription(BaseModel):
    """One row in the job_alert_subscriptions table joined with the
    referenced webhook's display info. webhook_name / webhook_url are
    null when the webhooks plugin is uninstalled (orphan subscription)."""
    id: str
    plugin_id: str = Field(
        ...,
        description="'*' for any plugin, or a specific plugin slug.",
    )
    on_status: list[str] = Field(
        ...,
        description="Terminal statuses this subscription fires on (subset of error/timeout/cancelled).",
    )
    webhook_id: str
    webhook_name: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_active: bool = False
    webhook_channel_type: Optional[str] = Field(
        default=None,
        description="Channel type of the referenced webhook (generic/slack/discord/teams). Null when the webhooks plugin is uninstalled (orphan subscription).",
    )
    enabled: bool
    updated_at: Optional[str] = None


class JobAlertSubscriptionListResponse(BaseModel):
    """GET /api/maintenance/job-alerts."""
    subscriptions: list[JobAlertSubscription]


class CreateJobAlertSubscriptionBody(BaseModel):
    """POST /api/maintenance/job-alerts."""
    plugin_id: str = Field(..., description="'*' for any plugin, or a specific plugin slug.")
    on_status: list[str] = Field(
        ...,
        description="Statuses to alert on. Allowed values: 'error', 'timeout', 'cancelled'.",
        min_length=1,
    )
    webhook_id: str = Field(..., description="UUID of an outbound webhook_endpoints row.")


class UpdateJobAlertSubscriptionBody(BaseModel):
    """PUT /api/maintenance/job-alerts/{id}. Pass only the fields you're changing."""
    on_status: Optional[list[str]] = None
    enabled: Optional[bool] = None


class JobAlertTestResponse(BaseModel):
    """POST /api/maintenance/job-alerts/{id}/test."""
    delivered: int
    skipped: int
    reason: Optional[str] = None


class AvailableWebhook(BaseModel):
    """One outbound webhook surfaced for the job-alert create-form picker."""
    id: str = Field(..., description="webhook_endpoints.id (UUID) — pass as `webhook_id` when creating a subscription.")
    name: str
    url: Optional[str] = None
    is_active: bool


class AvailableWebhooksResponse(BaseModel):
    """GET /api/maintenance/job-alerts/webhooks."""
    webhooks: list[AvailableWebhook]
