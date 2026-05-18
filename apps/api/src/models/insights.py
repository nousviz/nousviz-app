"""B216 (v0.9.10.3): typed responses for /api/insights/* routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InsightEntry(BaseModel):
    """Single insight from a Tier 1 (YAML) or Tier 2 (plugin endpoint) source.

    Insight shape is plugin-author-defined; the consistent envelope is
    `severity` + a free-form payload. extra='allow' covers
    plugin-specific fields like `metric`, `evidence`, `actions`, etc.
    """
    model_config = ConfigDict(extra="allow")

    severity: Optional[str] = Field(
        default=None,
        description="'critical' | 'warning' | 'info' | 'good' | 'tip'.",
    )
    title: Optional[str] = None
    description: Optional[str] = None
    plugin_id: Optional[str] = None


class InsightsListResponse(BaseModel):
    """GET /api/insights — aggregated insights from all installed plugins.

    Sorted by severity (critical → warning → info → good → tip), then
    truncated to `limit`. `total` is the un-truncated count.
    """
    insights: list[InsightEntry]
    total: int
