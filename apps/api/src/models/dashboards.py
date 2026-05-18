"""B216 (v0.9.10.3): typed responses for /api/dashboards/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    """Compact dashboard row from the list endpoint — widgets blob
    replaced by `widget_count`.
    """
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    sources: list[Any] = Field(
        default_factory=list,
        description="Plugin/dataset references; shape is dashboard-author-defined.",
    )
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    widget_count: int = 0


class DashboardsListResponse(BaseModel):
    """GET /api/dashboards — every user-created dashboard, newest-first."""
    dashboards: list[DashboardSummary]


class DashboardDetail(BaseModel):
    """Full dashboard row.

    `widgets` and `layout` are JSONB blobs whose shape is defined by the
    dashboard editor / widget runtime. We accept them verbatim with
    `extra='allow'` covering any future top-level columns.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    widgets: list[Any] = Field(
        default_factory=list,
        description="Widget specs — shape is widget-runtime-defined.",
    )
    layout: Optional[dict[str, Any]] = Field(
        default=None,
        description="Layout JSONB — react-grid-layout shape, but accepted verbatim.",
    )
    sources: list[Any] = Field(
        default_factory=list,
        description="Plugin/dataset references; shape is dashboard-author-defined.",
    )
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DashboardDeleteResponse(BaseModel):
    """DELETE /api/dashboards/{slug}."""
    deleted: bool = True
