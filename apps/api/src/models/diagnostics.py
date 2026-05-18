"""B272 (v0.9.11.18) — typed responses for /api/system/diagnostics."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FindingAffected(BaseModel):
    """One thing the finding is about (a table, sync, index, etc.).

    `detail` is freeform plain-language extra context (size, row count,
    timestamp). The frontend renders these as small chips on the
    expanded card — they're meant to give the operator enough context
    to act without expanding further.
    """
    type: str = Field(..., description="'table' | 'sync' | 'index' | 'plugin' | 'db' | 'host'.")
    name: str
    detail: Optional[str] = None


class FindingAction(BaseModel):
    """Action button on a finding card.

    Phase 1 (v0.9.11.18) supports `external` (link) and `manual`
    (copy-to-clipboard SQL/shell). The Phase 2 `sql_with_confirmation`
    type — execute privileged DROP / VACUUM via a confirmation modal
    — is deferred pending its own audit + RBAC review.
    """
    type: Literal["external", "manual"]
    label: str
    url: Optional[str] = Field(default=None, description="Route URL for `external` actions.")
    sql: Optional[str] = Field(default=None, description="SQL to copy-paste for `manual` actions.")
    shell: Optional[str] = Field(default=None, description="Shell command for `manual` actions.")


class Finding(BaseModel):
    """One actionable issue surfaced by the diagnostic engine."""
    id: str = Field(..., description="Stable rule identifier (used for dedup, history lookup).")
    severity: Literal["info", "warn", "critical"]
    title: str = Field(..., description="One-line summary shown collapsed.")
    evidence: str = Field(
        ...,
        description="2-4 lines explaining what was measured and why it triggered the rule.",
    )
    recommendation: str = Field(
        ...,
        description="Plain-language guidance — what to do about it.",
    )
    affected: list[FindingAffected] = Field(default_factory=list)
    action: Optional[FindingAction] = None
    detected_at: str
    last_alerted_at: Optional[str] = Field(
        default=None,
        description=(
            "B274 (v0.9.11.20): ISO timestamp of the most recent webhook "
            "alert dispatched for this (finding_id, affected_key). Null "
            "when no alert has fired (severity below threshold, or the "
            "subscription set is empty). Drives the `alert sent N min ago` "
            "badge on the FindingCard."
        ),
    )


class DiagnosticsSummary(BaseModel):
    critical: int
    warn: int
    info: int


class DiagnosticsResponse(BaseModel):
    """GET /api/system/diagnostics."""
    collected_at: str
    summary: DiagnosticsSummary
    findings: list[Finding]
