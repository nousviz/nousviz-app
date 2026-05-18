"""B215 (v0.9.10.2): typed responses for /api/shares/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ShareCreateResponse(BaseModel):
    """POST /api/shares — link issued."""
    share_id: str
    url: str = Field(..., description="Relative URL of the share landing page (/shared/<id>).")
    has_password: bool
    expires_at: Optional[str] = None


class ShareLink(BaseModel):
    """Single shared_links row from /api/shares list."""
    share_id: str
    title: Optional[str] = None
    page_path: str
    resource_type: str
    notes: Optional[str] = None
    has_password: bool
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[str] = None
    revoked: bool = False
    expired: bool = Field(..., description="True iff the link's expiry has passed at query time.")


class ShareListResponse(BaseModel):
    """GET /api/shares."""
    links: list[ShareLink]
    count: int


class ShareDetailResponse(BaseModel):
    """GET /api/shares/{share_id} — public metadata for the share landing page.

    Returns 410 (gone) for revoked or expired links — the response below
    is the success path only.
    """
    share_id: str
    title: Optional[str] = None
    page_path: str
    resource_type: str
    has_password: bool
    expires_at: Optional[str] = None


class ShareUpdateResponse(BaseModel):
    """PATCH /api/shares/{share_id}."""
    ok: bool = True
    share_id: str


class ShareRevokeResponse(BaseModel):
    """DELETE /api/shares/{share_id}."""
    status: str = Field(default="revoked", description="Always 'revoked' on success.")
    share_id: str


class ShareAccessResponse(BaseModel):
    """POST /api/shares/{share_id}/access — public landing-page access.

    Returns the page-path + filters needed to render the shared view.
    Filters is a free-form JSONB blob defined by the dashboard author.
    """
    page_path: str
    title: Optional[str] = None
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form filter state (date range, dimension selections, etc.) — dashboard-author-defined shape.",
    )


class ShareAccessLogEntry(BaseModel):
    """A single share_access_log row."""
    accessed_at: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: Optional[bool] = None


class ShareAccessLogResponse(BaseModel):
    """GET /api/shares/{share_id}/log — last 50 access attempts."""
    log: list[ShareAccessLogEntry]
    count: int
