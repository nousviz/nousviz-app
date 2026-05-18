"""B248 (v0.9.10.7) Phase 5: per-resource ACL admin endpoints.

Backs the Access tab on dashboard / fusion / connection / share / plugin
detail pages. Operators with `rbac.edit` can list, grant, and revoke
per-resource ACL rows; the resolver in rbac/resource_acls.py honours
them at request time.

Permission model: rbac.edit gates *all* mutations and reads of grants,
matching the existing /api/system/permissions admin surface. Per-resource
visibility (e.g. dashboard owners seeing their own ACL) is intentionally
deferred — owners already have implicit grant + can change owners via
the existing admin flow.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..db import get_pg_conn
from ..rbac import requires, register_route
from ..rbac.config_audit import log_config_change
from ..rbac.resource_acls import (
    grant as acl_grant,
    revoke as acl_revoke,
    list_grants,
    get_default_policy,
    set_default_policy,
    known_resource_types,
)
from ..models import ErrorDetail, RBACErrorDetail
from ..models.resource_acls import (
    AclDefaultPolicyResponse,
    AclGrantResponse,
    AclGrantRow,
    AclListResponse,
    AclRevokeResponse,
)
from .auth import get_me

logger = logging.getLogger("nousviz.resource_acls")
router = APIRouter(prefix="/api/resource-acls", tags=["resource-acls"])


def _validate_type(resource_type: str) -> None:
    if resource_type not in known_resource_types():
        raise HTTPException(
            400,
            f"unknown resource_type {resource_type!r}; expected one of "
            f"{list(known_resource_types())}",
        )


def _audit(action: str, **kwargs) -> None:
    """Insert one rbac_config_audit row in its own transaction. ACL
    mutations and the audit row don't share a connection (the helper
    functions in rbac/resource_acls.py manage their own), so audit
    failures are logged but do not roll back the underlying write —
    the operation already committed by the time we get here. This is a
    deliberate trade-off vs. the role-override path which co-commits;
    ACL writes are idempotent (UNIQUE constraint upserts) so duplicate
    audit on retry is acceptable."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            log_config_change(cur, action=action, **kwargs)
    except Exception:
        logger.exception("[acls] audit insert failed for action=%s kwargs=%s", action, kwargs)


# ── List grants on a resource ────────────────────────────────────────

register_route("GET", "/api/resource-acls/{resource_type}/{resource_id}", "rbac.edit")


@router.get(
    "/{resource_type}/{resource_id}",
    operation_id="resource_acls.list",
    response_model=AclListResponse,
    response_model_exclude_none=True,
    summary="List per-resource ACL grants + default policy for a resource",
    responses={
        400: {"model": ErrorDetail, "description": "Unknown resource_type."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rbac.edit."},
    },
)
def list_resource_grants(
    resource_type: str,
    resource_id: str,
    _: None = Depends(requires("rbac.edit")),
):
    _validate_type(resource_type)
    grants = list_grants(resource_type, resource_id)
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "default_policy": get_default_policy(resource_type),
        "grants": [
            AclGrantRow(
                id=g.id,
                resource_type=g.resource_type,
                resource_id=g.resource_id,
                principal_kind=g.principal_kind,
                principal_id=g.principal_id,
                permission=g.permission,
                granted_by=g.granted_by,
                note=g.note,
                created_at=g.created_at,
            )
            for g in grants
        ],
    }


# ── Create / upsert a grant ──────────────────────────────────────────

class GrantCreate(BaseModel):
    principal_kind: str = Field(..., description="'role' or 'user'.")
    principal_id: str = Field(..., description="Role name or user_id.")
    permission: str = Field(..., description="e.g. dashboards.read, fusions.write.")
    note: Optional[str] = None


register_route("POST", "/api/resource-acls/{resource_type}/{resource_id}", "rbac.edit")


@router.post(
    "/{resource_type}/{resource_id}",
    operation_id="resource_acls.grant",
    response_model=AclGrantResponse,
    response_model_exclude_none=True,
    summary="Grant a permission on a resource to a role or user",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid principal_kind or unknown resource_type."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rbac.edit."},
    },
)
def create_grant(
    resource_type: str,
    resource_id: str,
    body: GrantCreate,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
):
    _validate_type(resource_type)
    if body.principal_kind not in ("role", "user"):
        raise HTTPException(400, "principal_kind must be 'role' or 'user'")

    admin = get_me(request) or {}
    granted_by = admin.get("id")

    try:
        new_id = acl_grant(
            resource_type=resource_type,
            resource_id=resource_id,
            principal_kind=body.principal_kind,
            principal_id=body.principal_id,
            permission=body.permission,
            granted_by=granted_by,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if new_id is None:
        raise HTTPException(500, "grant insert failed; see server logs")
    _audit(
        "acl_grant",
        actor_user_id=granted_by,
        actor_role=admin.get("role"),
        target_permission=body.permission,
        target_resource_type=resource_type,
        target_resource_id=resource_id,
        after_state={
            "id": new_id,
            "principal_kind": body.principal_kind,
            "principal_id": body.principal_id,
            "permission": body.permission,
            "note": body.note,
        },
        note=body.note,
    )
    return {"id": new_id, "ok": True}


# ── Revoke a grant ───────────────────────────────────────────────────

register_route(
    "DELETE",
    "/api/resource-acls/{resource_type}/{resource_id}/{grant_id}",
    "rbac.edit",
)


@router.delete(
    "/{resource_type}/{resource_id}/{grant_id}",
    operation_id="resource_acls.revoke",
    response_model=AclRevokeResponse,
    summary="Revoke a per-resource ACL grant by id",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rbac.edit."},
        404: {"model": ErrorDetail, "description": "Grant not found."},
    },
)
def revoke_grant(
    resource_type: str,
    resource_id: str,
    grant_id: int,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
):
    revoked = acl_revoke(grant_id)
    if not revoked:
        raise HTTPException(404, "Grant not found")
    admin = get_me(request) or {}
    _audit(
        "acl_revoke",
        actor_user_id=admin.get("id"),
        actor_role=admin.get("role"),
        target_resource_type=resource_type,
        target_resource_id=resource_id,
        before_state={"id": grant_id},
    )
    return {"ok": True, "revoked": True}


# ── Default-policy admin ─────────────────────────────────────────────

class DefaultPolicyUpdate(BaseModel):
    policy: str = Field(..., description="'allow' or 'deny'.")


register_route("GET", "/api/resource-acls/defaults/{resource_type}", "rbac.edit")


@router.get(
    "/defaults/{resource_type}",
    operation_id="resource_acls.get_default_policy",
    response_model=AclDefaultPolicyResponse,
    summary="Get the default policy for a resource type",
    responses={
        400: {"model": ErrorDetail, "description": "Unknown resource_type."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rbac.edit."},
    },
)
def get_default(
    resource_type: str,
    _: None = Depends(requires("rbac.edit")),
):
    _validate_type(resource_type)
    return {"resource_type": resource_type, "policy": get_default_policy(resource_type)}


register_route("PUT", "/api/resource-acls/defaults/{resource_type}", "rbac.edit")


@router.put(
    "/defaults/{resource_type}",
    operation_id="resource_acls.set_default_policy",
    response_model=AclDefaultPolicyResponse,
    summary="Set the default policy for a resource type ('allow' or 'deny')",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid policy or unknown resource_type."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rbac.edit."},
    },
)
def put_default(
    resource_type: str,
    body: DefaultPolicyUpdate,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
):
    _validate_type(resource_type)
    if body.policy not in ("allow", "deny"):
        raise HTTPException(400, "policy must be 'allow' or 'deny'")
    admin = get_me(request) or {}
    before = get_default_policy(resource_type)
    ok = set_default_policy(resource_type, body.policy, updated_by=admin.get("id"))
    if not ok:
        raise HTTPException(500, "set_default_policy failed; see server logs")
    _audit(
        "set_default_policy",
        actor_user_id=admin.get("id"),
        actor_role=admin.get("role"),
        target_resource_type=resource_type,
        before_state={"policy": before},
        after_state={"policy": body.policy},
    )
    return {"resource_type": resource_type, "policy": body.policy}
