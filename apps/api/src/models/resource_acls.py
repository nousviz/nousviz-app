"""B248 (v0.9.10.7): typed responses for /api/resource-acls/* routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AclGrantRow(BaseModel):
    """A single resource_acls row."""
    id: int
    resource_type: str
    resource_id: str
    principal_kind: str
    principal_id: str
    permission: str
    granted_by: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class AclListResponse(BaseModel):
    """GET /api/resource-acls/{type}/{id}."""
    resource_type: str
    resource_id: str
    default_policy: str
    grants: list[AclGrantRow]


class AclGrantResponse(BaseModel):
    """POST /api/resource-acls/{type}/{id} — grant created or upserted."""
    id: int
    ok: bool = True


class AclRevokeResponse(BaseModel):
    """DELETE /api/resource-acls/{type}/{id}/{grant_id}."""
    ok: bool
    revoked: bool


class AclDefaultPolicyResponse(BaseModel):
    """GET / PUT /api/resource-acls/defaults/{type}."""
    resource_type: str
    policy: str
