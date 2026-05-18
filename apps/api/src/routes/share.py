"""
/api/shares — Shareable links with password protection and expiry.

Generates shareable links for dashboard pages. Links can be password-protected
(bcrypt) and have configurable expiry. Access is logged for audit.
"""

import json
import secrets
import logging
from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn
from ..rbac import requires, requires_resource, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.share import (
    ShareAccessLogResponse,
    ShareAccessResponse,
    ShareCreateResponse,
    ShareDetailResponse,
    ShareListResponse,
    ShareRevokeResponse,
    ShareUpdateResponse,
)

logger = logging.getLogger("nousviz.api.shares")

# Rate limiting for share password attempts
from ..rate_limit import RateLimiter
_share_limiter = RateLimiter(max_attempts=5, window_sec=60, max_keys=1000)


def _check_share_rate(share_id: str, ip: str) -> bool:
    """Returns True if rate limit exceeded."""
    return _share_limiter.is_limited(f"{share_id}:{ip}")

router = APIRouter(tags=["share"])

# B228: register share-management routes. The share-VIEWER routes
# (GET /api/shares/{id} and POST /api/shares/{id}/access) are in
# PUBLIC_ROUTES — they're how external share viewers access the link
# without auth. The CRUD routes here are admin-managed.
register_route("POST", "/api/shares", "shares.write")
register_route("GET", "/api/shares", "shares.read")
register_route("PATCH", "/api/shares/{share_id}", "shares.write")
register_route("DELETE", "/api/shares/{share_id}", "shares.write")
register_route("GET", "/api/shares/{share_id}/log", "shares.read")

SHAREABLE_TYPES = {"dashboard", "plugin_dashboard"}


class ShareCreate(BaseModel):
    page_path: str
    title: str | None = None
    resource_type: str = "dashboard"
    filters: dict = {}
    password: str | None = None
    expires_hours: int = 168


class ShareAccess(BaseModel):
    password: str | None = None


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


@router.post(
    "/shares",
    operation_id="shares.create",
    response_model=ShareCreateResponse,
    response_model_exclude_none=True,
    summary="Create a shareable link (optional password + expiry)",
    responses={
        400: {"model": ErrorDetail, "description": "Resource type not shareable."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the shares.write permission."},
    },
)
async def create_share(
    req: ShareCreate,
    request: Request,
    _: None = Depends(requires("shares.write")),
):
    if req.resource_type not in SHAREABLE_TYPES:
        raise HTTPException(400, f"Cannot share resource type '{req.resource_type}'. Only dashboards can be shared.")

    share_id = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=req.expires_hours)
    pw_hash = _hash_password(req.password) if req.password else None

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO shared_links (share_id, resource_type, page_path, title, filters, password_hash, expires_at, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING share_id, expires_at
        """, (
            share_id, req.resource_type, req.page_path,
            req.title or req.page_path.split("/")[-1],
            json.dumps(req.filters), pw_hash, expires_at, "user",
        ))
        row = cur.fetchone()
        conn.commit()

    from .activity import record_activity
    record_activity(
        action="share_create",
        detail={"title": req.title, "resource_type": req.resource_type, "has_password": pw_hash is not None},
    )

    return {
        "share_id": row[0],
        "url": f"/shared/{row[0]}",
        "has_password": pw_hash is not None,
        "expires_at": row[1].isoformat() if row[1] else None,
    }


@router.get(
    "/shares",
    operation_id="shares.list",
    response_model=ShareListResponse,
    response_model_exclude_none=True,
    summary="List all shared links (active and revoked)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the shares.read permission."},
    },
)
async def list_shares(_: None = Depends(requires("shares.read"))):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT share_id, title, page_path, resource_type, notes,
                   password_hash IS NOT NULL as has_password,
                   created_at, expires_at, access_count, last_accessed, revoked,
                   expires_at < now() as expired
            FROM shared_links ORDER BY created_at DESC
        """)
        cols = [d[0] for d in cur.description]
        links = []
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            for k in ("created_at", "expires_at", "last_accessed"):
                if r.get(k) and hasattr(r[k], "isoformat"):
                    r[k] = r[k].isoformat()
            links.append(r)
    return {"links": links, "count": len(links)}


@router.get(
    "/shares/{share_id}",
    operation_id="shares.detail",
    response_model=ShareDetailResponse,
    response_model_exclude_none=True,
    summary="Public metadata for a share landing page",
    responses={
        404: {"model": ErrorDetail, "description": "Share link not found."},
        410: {"model": ErrorDetail, "description": "Link has been revoked or has expired."},
    },
)
async def get_share_metadata(share_id: str):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT title, page_path, resource_type,
                   password_hash IS NOT NULL as has_password,
                   expires_at, revoked, expires_at < now() as expired
            FROM shared_links WHERE share_id = %s
        """, (share_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Share link not found")

    title, page_path, resource_type, has_password, expires_at, revoked, expired = row
    if revoked:
        raise HTTPException(410, "This share link has been revoked")
    if expired:
        raise HTTPException(410, "This share link has expired")

    return {
        "share_id": share_id,
        "title": title,
        "page_path": page_path,
        "resource_type": resource_type,
        "has_password": has_password,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@router.post(
    "/shares/{share_id}/access",
    operation_id="shares.access",
    response_model=ShareAccessResponse,
    response_model_exclude_none=True,
    summary="Access a share link (public; password-gated when applicable)",
    responses={
        401: {"model": ErrorDetail, "description": "Password required or incorrect."},
        404: {"model": ErrorDetail, "description": "Share link not found."},
        410: {"model": ErrorDetail, "description": "Share link revoked or expired."},
        429: {"model": ErrorDetail, "description": "Rate-limited (5 attempts / 60s per share+IP)."},
    },
)
async def access_share(share_id: str, req: ShareAccess, request: Request):
    # Rate limit password attempts per share per IP
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if _check_share_rate(share_id, client_ip):
        raise HTTPException(429, "Too many access attempts. Try again in 60 seconds.")

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT page_path, title, filters, password_hash, expires_at, revoked
            FROM shared_links WHERE share_id = %s
        """, (share_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(404, "Share link not found")

        page_path, title, filters, pw_hash, expires_at, revoked = row

        if revoked:
            raise HTTPException(410, "This share link has been revoked")
        if expires_at and datetime.now(timezone.utc) > expires_at:
            raise HTTPException(410, "This share link has expired")

        if pw_hash:
            if not req.password:
                _log_access(cur, share_id, request, success=False)
                conn.commit()
                raise HTTPException(401, "This link requires a password")
            if not _check_password(req.password, pw_hash):
                _log_access(cur, share_id, request, success=False)
                conn.commit()
                raise HTTPException(401, "Incorrect password")

        cur.execute("""
            UPDATE shared_links SET access_count = access_count + 1, last_accessed = now()
            WHERE share_id = %s
        """, (share_id,))
        _log_access(cur, share_id, request, success=True)
        conn.commit()

    return {
        "page_path": page_path,
        "title": title,
        "filters": filters if isinstance(filters, dict) else json.loads(filters) if filters else {},
    }


class ShareUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None


@router.patch(
    "/shares/{share_id}",
    operation_id="shares.update",
    response_model=ShareUpdateResponse,
    summary="Update a share link's title and/or notes",
    responses={
        400: {"model": ErrorDetail, "description": "Empty body."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the shares.write permission."},
        404: {"model": ErrorDetail, "description": "Share link not found or already revoked."},
    },
)
async def update_share(
    share_id: str,
    req: ShareUpdate,
    request: Request,
    # B248: per-resource ACL on this share's id.
    _: None = Depends(requires_resource("share", "shares.write", id_param="share_id")),
):
    """Update share title and/or notes."""
    updates = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.notes is not None:
        updates["notes"] = req.notes
    if not updates:
        raise HTTPException(400, "Nothing to update")

    with get_pg_conn() as conn:
        cur = conn.cursor()
        set_parts = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE shared_links SET {set_parts} WHERE share_id = %s AND revoked = false RETURNING share_id",
            list(updates.values()) + [share_id],
        )
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(404, "Share link not found or revoked")
    return {"ok": True, "share_id": share_id}


@router.get(
    "/shares/{share_id}/log",
    operation_id="shares.access_log",
    response_model=ShareAccessLogResponse,
    response_model_exclude_none=True,
    summary="Last 50 access attempts for a share link",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the shares.read permission."},
    },
)
async def get_share_access_log(
    share_id: str,
    # B248: per-resource ACL on this share's id.
    _: None = Depends(requires_resource("share", "shares.read", id_param="share_id")),
):
    """Return access log for a share link."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT accessed_at, ip_address, user_agent, success
            FROM share_access_log
            WHERE share_id = %s
            ORDER BY accessed_at DESC
            LIMIT 50
        """, (share_id,))
        cols = [d[0] for d in cur.description]
        rows = []
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            if r.get("accessed_at") and hasattr(r["accessed_at"], "isoformat"):
                r["accessed_at"] = r["accessed_at"].isoformat()
            rows.append(r)
    return {"log": rows, "count": len(rows)}


@router.delete(
    "/shares/{share_id}",
    operation_id="shares.revoke",
    response_model=ShareRevokeResponse,
    summary="Revoke a share link",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the shares.write permission."},
        404: {"model": ErrorDetail, "description": "Share link not found or already revoked."},
    },
)
async def revoke_share(
    share_id: str,
    request: Request,
    # B248: per-resource ACL on this share's id.
    _: None = Depends(requires_resource("share", "shares.write", id_param="share_id")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE shared_links SET revoked = true WHERE share_id = %s AND revoked = false
            RETURNING share_id
        """, (share_id,))
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(404, "Share link not found or already revoked")

    from .activity import record_activity
    record_activity(action="share_revoke", detail={"share_id": share_id})

    return {"status": "revoked", "share_id": share_id}


def _log_access(cur, share_id: str, request: Request, success: bool):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:256]
    cur.execute("""
        INSERT INTO share_access_log (share_id, ip_address, user_agent, success)
        VALUES (%s, %s, %s, %s)
    """, (share_id, ip, ua, success))
