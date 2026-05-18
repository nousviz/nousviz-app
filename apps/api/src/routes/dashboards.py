"""
User Dashboards — user-created dashboard views.
Layer 3 of the dashboard architecture:
  1. Plugin dashboards (YAML, read-only)
  2. Fusions (cross-plugin data composition)
  3. User dashboards (presentation layer — this module)

CRUD for dashboard configs. Widget data is fetched client-side via POST /api/query.
"""
import json
import re
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn
from ..rbac import requires, requires_resource, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.dashboards import (
    DashboardDeleteResponse,
    DashboardDetail,
    DashboardsListResponse,
)

logger = logging.getLogger("nousviz.dashboards")

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


def _serialize(row: dict) -> dict:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _unique_slug(cur, base_slug: str) -> str:
    """Ensure slug uniqueness by appending -1, -2, etc. if needed."""
    slug = base_slug
    suffix = 0
    while True:
        cur.execute("SELECT 1 FROM user_dashboards WHERE slug = %s", (slug,))
        if not cur.fetchone():
            return slug
        suffix += 1
        slug = f"{base_slug}-{suffix}"


COLS = [
    "id", "name", "slug", "description", "widgets", "layout",
    "sources", "created_by", "created_at", "updated_at",
]


# ── List all dashboards ──────────────────────────────────────────────

# B228: previously silent-leak (no _require_*). Now requires dashboards.read.
register_route("GET", "/api/dashboards/", "dashboards.read")


@router.get(
    "/",
    operation_id="dashboards.list",
    response_model=DashboardsListResponse,
    response_model_exclude_none=True,
    summary="List user-created dashboards (no widgets blob)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.read permission."},
    },
)
def list_dashboards(_: None = Depends(requires("dashboards.read"))):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, slug, description, sources, created_by,
                   created_at, updated_at,
                   jsonb_array_length(widgets) AS widget_count
            FROM user_dashboards
            ORDER BY updated_at DESC
        """)
        cols = [d[0] for d in cur.description]
        dashboards = [_serialize(dict(zip(cols, row))) for row in cur.fetchall()]
    return {"dashboards": dashboards}


# ── Get a single dashboard ───────────────────────────────────────────

# B227 dual-check: registry says dashboards.read, inline says (none — currently public).
# After B229's default-deny flip, this will require viewer+ to access.
register_route("GET", "/api/dashboards/{slug}", "dashboards.read")


@router.get(
    "/{slug}",
    operation_id="dashboards.detail",
    response_model=DashboardDetail,
    response_model_exclude_none=True,
    summary="Get a user dashboard with widgets + layout",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.read permission."},
        404: {"model": ErrorDetail, "description": "Dashboard not found."},
    },
)
def get_dashboard(
    slug: str,
    # B248: per-resource ACL check on dashboard with given slug.
    # The check internally handles role-permission fallback + default
    # policy, so we don't need a separate `Depends(requires(...))`.
    _: None = Depends(requires_resource("dashboard", "dashboards.read")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT " + ", ".join(COLS) + " FROM user_dashboards WHERE slug = %s",
            (slug,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Dashboard not found")
    return _serialize(dict(zip(COLS, row)))


# ── Create dashboard ─────────────────────────────────────────────────

class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    widgets: list = []
    layout: Optional[dict] = None
    sources: list = []


register_route("POST", "/api/dashboards/", "dashboards.write")


@router.post(
    "/",
    operation_id="dashboards.create",
    response_model=DashboardDetail,
    response_model_exclude_none=True,
    summary="Create a user dashboard",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.write permission."},
    },
)
def create_dashboard(
    req: DashboardCreate,
    request: Request,
    _: None = Depends(requires("dashboards.write")),
):
    user_id = getattr(request.state, "user_id", None)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        slug = _unique_slug(cur, _slugify(req.name))
        cur.execute("""
            INSERT INTO user_dashboards (name, slug, description, widgets, layout, sources, created_by)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
            RETURNING """ + ", ".join(COLS),
            (req.name, slug, req.description,
             json.dumps(req.widgets), json.dumps(req.layout or {}),
             json.dumps(req.sources), user_id),
        )
        row = cur.fetchone()
    return _serialize(dict(zip(COLS, row)))


# ── Update dashboard ─────────────────────────────────────────────────

register_route("PUT", "/api/dashboards/{slug}", "dashboards.write")


@router.put(
    "/{slug}",
    operation_id="dashboards.update",
    response_model=DashboardDetail,
    response_model_exclude_none=True,
    summary="Replace a user dashboard's name/description/widgets/layout/sources",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.write permission."},
        404: {"model": ErrorDetail, "description": "Dashboard not found."},
    },
)
def update_dashboard(
    slug: str,
    req: DashboardCreate,
    request: Request,
    # B248: per-resource ACL check (role permission honoured internally).
    _: None = Depends(requires_resource("dashboard", "dashboards.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_dashboards
            SET name = %s, description = %s, widgets = %s::jsonb,
                layout = %s::jsonb, sources = %s::jsonb, updated_at = now()
            WHERE slug = %s
            RETURNING """ + ", ".join(COLS),
            (req.name, req.description,
             json.dumps(req.widgets), json.dumps(req.layout or {}),
             json.dumps(req.sources), slug),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Dashboard not found")
    return _serialize(dict(zip(COLS, row)))


# ── Delete dashboard ─────────────────────────────────────────────────

register_route("DELETE", "/api/dashboards/{slug}", "dashboards.write")


@router.delete(
    "/{slug}",
    operation_id="dashboards.delete",
    response_model=DashboardDeleteResponse,
    summary="Delete a user dashboard",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.write permission."},
        404: {"model": ErrorDetail, "description": "Dashboard not found."},
    },
)
def delete_dashboard(
    slug: str,
    request: Request,
    # B248: per-resource ACL check (role permission honoured internally).
    _: None = Depends(requires_resource("dashboard", "dashboards.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_dashboards WHERE slug = %s RETURNING slug", (slug,))
        if not cur.fetchone():
            raise HTTPException(404, "Dashboard not found")
    return {"deleted": True}
