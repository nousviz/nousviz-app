"""B273 (v0.9.11.19) — typed responses for /api/system/*/history."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HistoryPoint(BaseModel):
    """One sample in a metric time-series."""
    snapshot_at: str
    value: Optional[float] = Field(
        default=None,
        description=(
            "Metric value at this snapshot. Null when the metric isn't "
            "applicable to the snapshot — e.g. a plugin that wasn't yet "
            "installed. The UI renders nulls as gaps, not zero."
        ),
    )


class ResourcesHistoryResponse(BaseModel):
    """GET /api/system/resources/history?metric=...&days=N."""
    metric: str
    plugin: Optional[str] = None
    days: int
    points: list[HistoryPoint]


class FindingHistoryPoint(BaseModel):
    """One sample in a finding presence time-series."""
    snapshot_at: str
    present: bool
    severity: Optional[str] = Field(
        default=None,
        description="Severity at this snapshot. Null when present=false.",
    )


class DiagnosticsHistoryResponse(BaseModel):
    """GET /api/system/diagnostics/history?id=...&days=N."""
    finding_id: str
    days: int
    points: list[FindingHistoryPoint]
    first_detected_at: Optional[str] = Field(
        default=None,
        description=(
            "Earliest snapshot in the queried window where the finding was "
            "present. Null when the finding has never been present in the "
            "queried window."
        ),
    )
