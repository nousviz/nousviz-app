"""B216 (v0.9.10.3): typed responses for /api/launchpad."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertsSummary(BaseModel):
    """Aggregate alert counts surfaced in the launchpad block."""
    total: int = 0
    enabled: int = 0
    triggered_24h: int = 0
    recent_triggers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recent alert_events rows; row shape varies by alert type.",
    )


class LaunchpadResponse(BaseModel):
    """GET /api/launchpad — single-call data feed for the Overview page.

    Each block is best-effort populated from a separate query inside the
    handler; failures roll back the inner transaction and leave the
    block at its empty default.
    """
    model_config = ConfigDict(extra="allow")

    recent_activity: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Up to 20 non-page-view activity events.",
    )
    recent_data_changes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-plugin sync recency (job_runs success + plugin_settings._last_sync union).",
    )
    alerts_summary: AlertsSummary = Field(
        default_factory=AlertsSummary,
        description="Alert-system counts (total / enabled / triggered_24h) + recent triggers.",
    )
    health_snapshot: Optional[dict[str, Any]] = None
    needs_attention: list[dict[str, Any]] = Field(
        default_factory=list,
        description="System-level items needing operator action (e.g. expiring SSL, missing migrations).",
    )
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="{annotations, active_shares} aggregate counts.",
    )
