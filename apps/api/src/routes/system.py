"""
B230 / B231 / B233 (v0.9.8.3+) — System / RBAC audit + edit endpoints.

Backs the audit matrix UI at /system/permissions.

Read endpoints (all gated by system.audit, admin+):
- GET /api/system/permissions — full registry snapshot (roles, permissions,
  routes, public allowlist, sensitive flags, plugin-default flags, recent
  audit summary).
- GET /api/system/users-with-permissions — per-user permission audit data
  for the Users tab on the matrix page (B231).

Write endpoints (B233, gated by rbac.edit, superadmin-only):
- POST   /api/system/role-overrides — grant or revoke a permission for a role
- DELETE /api/system/role-overrides/{role}/{permission} — clear an override
- POST   /api/system/custom-roles — create an operator-defined role
- DELETE /api/system/custom-roles/{role} — delete a custom role

Sensitive permissions (per B227 SENSITIVE_PERMISSIONS) cannot be granted
to non-admin roles — the API returns 409 on attempt.
"""
import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..db import get_pg_conn
from ..rbac import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    SENSITIVE_PERMISSIONS,
    ROUTE_PERMISSIONS,
    PUBLIC_ROUTES,
    all_permissions_for_role,
    default_permissions_for_role,
    get_overrides_for_role,
    invalidate_override_cache,
    requires,
    requires_step_up,
    register_route,
)
from ..models import ErrorDetail, RBACErrorDetail, StepUpRequiredDetail
from ..models.system import (
    CustomRoleCreateResponse,
    PermissionsMatrixResponse,
    RbacAuditLogResponse,
    RoleOverrideResponse,
    UsersWithPermissionsResponse,
)

logger = logging.getLogger("nousviz.api.system")

router = APIRouter(prefix="/api/system", tags=["system"])

# Read endpoints (B230 / B231)
register_route("GET", "/api/system/permissions", "system.audit")
register_route("GET", "/api/system/users-with-permissions", "system.audit")

# Write endpoints (B233). All gated by rbac.edit, which only superadmin
# holds in the static catalog. v0.9.9.4 (B236) adds step-up auth on top.
register_route("POST", "/api/system/role-overrides", "rbac.edit")
register_route("DELETE", "/api/system/role-overrides/{role}/{permission}", "rbac.edit")
register_route("POST", "/api/system/custom-roles", "rbac.edit")
register_route("DELETE", "/api/system/custom-roles/{role}", "rbac.edit")

# Roles that the override system knows about. Built-ins are always
# present; custom roles are looked up in rbac_custom_roles.
_BUILT_IN_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS.keys())

# Slug rule mirrors the CHECK constraint in migration 054.
_CUSTOM_ROLE_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


# Core router prefixes — used to detect which routes are plugin-author
# routes (and therefore got auto-default permissions in B229) vs. core
# routes (where the permission was explicitly chosen during B228).
_CORE_API_PREFIXES = (
    "/api/auth",
    "/api/health",
    "/api/dashboards",
    "/api/plugins",
    "/api/sync",
    "/api/jobs",
    "/api/datasets",
    "/api/settings",
    "/api/connections",
    "/api/data-port",
    "/api/catalog",
    "/api/fusions",
    "/api/insights",
    "/api/alerts",
    "/api/annotations",
    "/api/notes",
    "/api/share",
    "/api/shares",
    "/api/admin",
    "/api/launchpad",
    "/api/query",
    "/api/docs",
    "/api/activity",
    "/api/widget-runtime",
    "/api/system",
)

# Methods → default permission applied by the plugin auto-register pass
# (B229 _auto_register_plugin_routes). If a route's (method, permission)
# matches the default for its method AND the route is plugin-owned, it
# was set by the auto-register and should be flagged "default" in the UI.
_PLUGIN_AUTO_DEFAULTS = {
    "GET": "plugins.read",
    "POST": "plugins.configure",
    "PATCH": "plugins.configure",
    "PUT": "plugins.configure",
    "DELETE": "plugins.configure",
}


def _is_plugin_route(method: str, path: str) -> bool:
    """True if the route is plugin-owned (not part of a core router).

    Plugin routes:
      - Anything under /api/plugins/<concrete_slug>/* (NOT the core
        templated /api/plugins/{plugin_id}/* routes — those are core
        endpoints that operate on a plugin by ID).
      - Anything under a non-core /api/* prefix (e.g. plugin extra_routers
        like /api/webhooks/in/{slug}).
    """
    if path.startswith("/api/plugins/"):
        # /api/plugins/{plugin_id}/...  → core route templated on plugin_id
        # /api/plugins/avizo-jira/...   → plugin route (concrete slug)
        return "{plugin_id}" not in path
    if not path.startswith("/api/"):
        return False
    # Other /api/* — check against known core prefixes.
    return not any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in _CORE_API_PREFIXES
    )


def _is_plugin_default(method: str, path: str, permission: str) -> bool:
    """True if this (method, path, permission) was set by the plugin
    auto-register pass — i.e., the operator hasn't yet expressed an
    explicit policy for it.
    """
    if not _is_plugin_route(method, path):
        return False
    return _PLUGIN_AUTO_DEFAULTS.get(method) == permission


def _last_accessed_per_route() -> dict[tuple[str, str, str], str | None]:
    """For each (method, path, user_role), the timestamp of the most
    recent allow decision in auth_audit. Used to populate the matrix's
    'last accessed by role X' column.

    Returns ISO-8601 timestamps. Keys are (method, path, role).
    Roles include None for unauthenticated successful access (rare —
    only for PUBLIC_ROUTES that were nonetheless logged).
    """
    rows: dict[tuple[str, str, str], str | None] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Use the partial index — registry-permission rows only,
            # not _role.* shadow markers — to keep the query fast.
            cur.execute(
                """
                SELECT route_method, route_path, user_role,
                       MAX(occurred_at)::text AS last_at
                FROM auth_audit
                WHERE decision = 'allow'
                  AND permission NOT LIKE '\\_role.%%' ESCAPE '\\'
                  AND occurred_at > now() - interval '30 days'
                GROUP BY route_method, route_path, user_role
                """
            )
            for method, path, role, last_at in cur.fetchall():
                rows[(method, path, role or "")] = last_at
    except Exception:
        # Fail open — if auth_audit is unavailable, the UI just shows
        # blank "last accessed" columns rather than 500-ing the page.
        logger.exception("[rbac] _last_accessed_per_route failed (returning empty)")
    return rows


def _audit_summary(window_hours: int = 24) -> dict[str, Any]:
    """High-level summary of recent permission decisions.

    Returns counts of allow/deny by mode (shadow vs enforced) for the
    last N hours, plus the most-denied permissions (helps operators
    spot misconfigurations or attempted abuse).
    """
    summary: dict[str, Any] = {
        "window_hours": window_hours,
        "decisions": {"allow": 0, "deny": 0, "shadow_mismatch": 0},
        "top_denials": [],
    }
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT decision, COUNT(*)
                FROM auth_audit
                WHERE occurred_at > now() - (%s || ' hours')::interval
                  AND permission NOT LIKE '\\_role.%%' ESCAPE '\\'
                GROUP BY decision
                """,
                (window_hours,),
            )
            for decision, count in cur.fetchall():
                if decision in summary["decisions"]:
                    summary["decisions"][decision] = int(count)

            cur.execute(
                """
                SELECT permission, COUNT(*) AS denials
                FROM auth_audit
                WHERE occurred_at > now() - (%s || ' hours')::interval
                  AND decision = 'deny'
                  AND permission NOT LIKE '\\_role.%%' ESCAPE '\\'
                GROUP BY permission
                ORDER BY denials DESC
                LIMIT 10
                """,
                (window_hours,),
            )
            summary["top_denials"] = [
                {"permission": p, "count": int(c)} for p, c in cur.fetchall()
            ]
    except Exception:
        logger.exception("[rbac] _audit_summary failed (returning empty)")
    return summary


@router.get(
    "/permissions",
    operation_id="system.permissions",
    response_model=PermissionsMatrixResponse,
    response_model_exclude_none=True,
    summary="Full RBAC matrix snapshot for /system/permissions",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def get_permissions(
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict[str, Any]:
    """Full RBAC registry snapshot for the audit matrix UI.

    Response shape:
    {
      "permissions": {
        "<name>": {"description": "...", "sensitive": bool}
      },
      "roles": {
        "<role>": ["<permission>", ...]
      },
      "routes": [
        {
          "method": "GET",
          "path": "/api/...",
          "permission": "plugins.read",
          "is_plugin_route": bool,
          "is_plugin_default": bool,
          "last_accessed": {
            "viewer": "<iso ts>" | null,
            "analyst": "<iso ts>" | null,
            ...
          }
        }
      ],
      "public_routes": [["GET", "/api/health"], ...],
      "audit_summary": {
        "window_hours": 24,
        "decisions": {"allow": N, "deny": M, "shadow_mismatch": K},
        "top_denials": [{"permission": "...", "count": N}, ...]
      },
      "shadow_mode": bool,
      "version": "0.9.8.3"
    }
    """
    last_accessed = _last_accessed_per_route()

    routes_out = []
    for (method, path), permission in ROUTE_PERMISSIONS.items():
        is_plugin = _is_plugin_route(method, path)
        is_default = _is_plugin_default(method, path, permission)

        # Group last-accessed timestamps by role for this route.
        per_role: dict[str, str | None] = {}
        for role in ROLE_PERMISSIONS.keys():
            per_role[role] = last_accessed.get((method, path, role))

        routes_out.append({
            "method": method,
            "path": path,
            "permission": permission,
            "is_plugin_route": is_plugin,
            "is_plugin_default": is_default,
            "last_accessed": per_role,
        })

    # Stable order: by path then method, so the UI can render predictably.
    routes_out.sort(key=lambda r: (r["path"], r["method"]))

    # Detect shadow mode at request time (the dependency module's flag).
    from ..rbac.dependency import SHADOW_MODE
    from ..rbac.audit import VALID_DECISIONS  # noqa: F401 — import-side checks

    # Pull version from the central VERSION file the rest of the app uses.
    try:
        from ..routes.health import APP_VERSION
        version = APP_VERSION
    except Exception:
        version = "unknown"

    # B232 (v0.9.9.0) + B233 (v0.9.9.1): expose default + resolved +
    # override metadata for each role. Built-ins have static defaults;
    # custom roles' "default" is empty and their effective set lives
    # entirely in rbac_role_overrides as 'grant' rows.
    role_data: dict[str, Any] = {}
    for role in ROLE_PERMISSIONS.keys():
        defaults = sorted(list(default_permissions_for_role(role)))
        resolved = sorted(list(all_permissions_for_role(role)))
        role_data[role] = {
            "kind": "built_in",
            "display_name": role,
            "default_permissions": defaults,
            "permissions": resolved,
            "overrides": get_overrides_for_role(role),
        }

    # B233: include custom roles in the matrix.
    for slug, meta in _list_custom_roles().items():
        role_data[slug] = {
            "kind": "custom",
            "display_name": meta.get("display_name") or slug,
            "description": meta.get("description"),
            "based_on": meta.get("based_on"),
            "default_permissions": [],  # custom roles have no static default
            "permissions": sorted(list(all_permissions_for_role(slug))),
            "overrides": get_overrides_for_role(slug),
            "created_by": meta.get("created_by"),
            "created_at": meta.get("created_at"),
        }

    return {
        "permissions": {
            name: {
                "description": desc,
                "sensitive": name in SENSITIVE_PERMISSIONS,
            }
            for name, desc in PERMISSIONS.items()
        },
        # Backward-compatible: keep `roles` as flat name→[permissions] for
        # any caller that hasn't migrated to `role_data` yet. This is the
        # resolved (post-override) set in v0.9.9.0+.
        "roles": {
            role: data["permissions"]
            for role, data in role_data.items()
        },
        # B232: richer per-role data — defaults, resolved, and override deltas.
        "role_data": role_data,
        "routes": routes_out,
        "public_routes": sorted([list(p) for p in PUBLIC_ROUTES]),
        "audit_summary": _audit_summary(window_hours=24),
        "shadow_mode": SHADOW_MODE,
        "version": version,
    }


@router.get(
    "/users-with-permissions",
    operation_id="system.users_with_permissions",
    response_model=UsersWithPermissionsResponse,
    response_model_exclude_none=True,
    summary="Per-user permission audit data (Users tab on the matrix page)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def get_users_with_permissions(
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict[str, Any]:
    """B231 (v0.9.8.4) — per-user permission audit data.

    Backs the Users tab on the matrix page. For each user, returns:
      - identity (id, email, name, role, is_active)
      - their resolved permission set (from role -> permissions catalog)
      - their most-recent allow decision in auth_audit (last 30d)

    The resolved permission set comes from the static catalog because
    v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
    top — this endpoint will return the post-override resolved set so
    the frontend contract doesn't change.

    Sorted by email for stable rendering. An empty list is valid —
    e.g. a fresh install before the wizard creates the first superadmin.
    """
    users_out: list[dict[str, Any]] = []
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT u.id::text, u.email, u.name, u.role, u.is_active,
                       la.last_activity_at, la.last_activity_route
                FROM users u
                LEFT JOIN LATERAL (
                    SELECT a.occurred_at AS last_activity_at,
                           (a.route_method || ' ' || a.route_path) AS last_activity_route
                    FROM auth_audit a
                    WHERE a.user_id = u.id::text
                      AND a.decision = 'allow'
                      AND a.permission NOT LIKE '\\_role.%%' ESCAPE '\\'
                      AND a.occurred_at > now() - interval '30 days'
                    ORDER BY a.occurred_at DESC
                    LIMIT 1
                ) la ON true
                ORDER BY u.email
                """
            )
            for uid, email, name, role, is_active, last_at, last_route in cur.fetchall():
                users_out.append({
                    "id": uid,
                    "email": email,
                    "name": name,
                    "role": role,
                    "is_active": bool(is_active),
                    "permissions": sorted(all_permissions_for_role(role or "")),
                    "last_activity_at": last_at.isoformat() if last_at else None,
                    "last_activity_route": last_route,
                })
    except Exception:
        # Fresh install before the wizard runs, or DB unavailable.
        # Fail open — return empty list so the UI renders an empty state
        # rather than a 500.
        logger.exception("[rbac] users-with-permissions query failed (returning empty)")

    return {"users": users_out}


# ─────────────────────────────────────────────────────────────────────
# B233 (v0.9.9.1) — Write endpoints for editable RBAC.
# All gated by rbac.edit (superadmin in the static catalog).
# ─────────────────────────────────────────────────────────────────────


def _list_custom_roles() -> dict[str, dict[str, Any]]:
    """Fetch the rbac_custom_roles table as a dict keyed by role name.
    Empty dict if the table doesn't exist (pre-migration safety) or is
    empty. Used for slug-collision checks and to validate role refs in
    other endpoints."""
    out: dict[str, dict[str, Any]] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT role, display_name, description, based_on, created_by, "
                "       created_at::text "
                "FROM rbac_custom_roles ORDER BY role"
            )
            for role, dn, desc, based, by, at in cur.fetchall():
                out[role] = {
                    "role": role, "display_name": dn, "description": desc,
                    "based_on": based, "created_by": by, "created_at": at,
                }
    except Exception:
        logger.exception("[rbac] _list_custom_roles failed (returning empty)")
    return out


def _role_exists(role: str) -> bool:
    if role in _BUILT_IN_ROLES:
        return True
    return role in _list_custom_roles()


def _user_id_or_anon(request: Request) -> str:
    """Best-effort actor-id extraction for created_by columns. Falls
    back to 'anonymous' if the user can't be resolved (shouldn't happen
    on an admin-gated endpoint, but defensive)."""
    try:
        from .auth import get_me
        u = get_me(request)
        return str(u.get("id") or "unknown")
    except Exception:
        return "anonymous"


def _actor(request: Request) -> tuple[str, Optional[str]]:
    """Return (user_id, role) for the request actor. Used by config
    audit logging — captures who made the change AND what role they
    held at the time (in case the operator's role changes later)."""
    try:
        from .auth import get_me
        u = get_me(request)
        return (str(u.get("id") or "unknown"), u.get("role"))
    except Exception:
        return ("anonymous", None)


# ── Role overrides (grant / revoke / clear) ───────────────────────────

class RoleOverrideRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=64)
    permission: str = Field(..., min_length=1, max_length=128)
    kind: str = Field(..., pattern=r"^(grant|revoke)$")
    note: Optional[str] = Field(default=None, max_length=512)


@router.post(
    "/role-overrides",
    operation_id="system.role_overrides.upsert",
    response_model=RoleOverrideResponse,
    response_model_exclude_none=True,
    summary="Grant or revoke a permission for a role (B233; step-up required)",
    responses={
        400: {"model": ErrorDetail, "description": "Unknown permission/role, or sensitive-revoke blocked."},
        401: {"model": StepUpRequiredDetail, "description": "Step-up auth required (B236)."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the rbac.edit permission."},
        409: {"model": ErrorDetail, "description": "Sensitive permission can't be granted to non-admin role."},
        500: {"model": ErrorDetail, "description": "Failed to write override."},
    },
)
async def upsert_role_override(
    body: RoleOverrideRequest,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
    __: None = Depends(requires_step_up),  # B236
):
    """Grant or revoke a permission for a role. Upserts: if a prior
    override exists for the same (role, permission), it's deleted before
    the new row is inserted. Cache invalidated so the change is visible
    immediately.

    Refuses to grant a sensitive permission to a non-admin role (409).
    """
    role = body.role
    permission = body.permission
    kind = body.kind

    if permission not in PERMISSIONS:
        raise HTTPException(400, f"Unknown permission: {permission!r}")

    if not _role_exists(role):
        raise HTTPException(400, f"Unknown role: {role!r}")

    # Sensitive permission rule. If granting a sensitive permission, the
    # target role must be admin or superadmin (or a custom role that's
    # explicitly admin-tier — but custom roles don't have a tier yet,
    # so we conservatively block them).
    if kind == "grant" and permission in SENSITIVE_PERMISSIONS:
        if role not in ("admin", "superadmin"):
            raise HTTPException(
                409,
                f"Cannot grant sensitive permission {permission!r} to non-admin role "
                f"{role!r}. Sensitive permissions can only be held by admin or "
                f"superadmin roles.",
            )

    # B236 (v0.9.10.0): block revokes that would strand operators.
    # Specifically: revoking any sensitive permission from `superadmin`
    # would lock the deployment out of RBAC editing, since rbac.edit is
    # superadmin-only and only admins+superadmins hold sensitive perms.
    # Allow revokes from `admin` (operator can re-grant) but never from
    # `superadmin` (no recovery path). Custom roles always allowed since
    # they didn't have the permission to begin with.
    if kind == "revoke" and permission in SENSITIVE_PERMISSIONS and role == "superadmin":
        raise HTTPException(
            400,
            {
                "error": "sensitive_revoke_blocked",
                "permission": permission,
                "role": role,
                "message": (
                    f"Cannot revoke sensitive permission {permission!r} from "
                    f"{role!r}. This would lock the deployment out of RBAC "
                    f"administration with no recovery path."
                ),
            },
        )

    actor_id, actor_role = _actor(request)

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Capture the prior override row (if any) BEFORE deletion, so the
            # config audit's before_state reflects what existed.
            cur.execute(
                "SELECT id, kind, created_by, created_at::text, note "
                "FROM rbac_role_overrides WHERE role = %s AND permission = %s",
                (role, permission),
            )
            prior = cur.fetchone()
            before_state = None
            if prior:
                before_state = {
                    "id": prior[0], "kind": prior[1], "created_by": prior[2],
                    "created_at": prior[3], "note": prior[4],
                }

            # Upsert via DELETE+INSERT to satisfy the UNIQUE (role, permission)
            # constraint cleanly. Wrapped in a single transaction with the
            # config audit insert — fail-closed.
            cur.execute(
                "DELETE FROM rbac_role_overrides WHERE role = %s AND permission = %s",
                (role, permission),
            )
            cur.execute(
                "INSERT INTO rbac_role_overrides "
                "(role, permission, kind, created_by, note) "
                "VALUES (%s, %s, %s, %s, %s) "
                "RETURNING id, created_at::text",
                (role, permission, kind, actor_id, body.note),
            )
            row = cur.fetchone()

            # B234: log the config change in the same transaction.
            from ..rbac import log_config_change
            after_state = {
                "id": row[0], "kind": kind, "created_by": actor_id,
                "created_at": row[1], "note": body.note,
            }
            log_config_change(
                cur,
                action=kind,  # 'grant' or 'revoke'
                target_role=role,
                target_permission=permission,
                actor_user_id=actor_id,
                actor_role=actor_role,
                before_state=before_state,
                after_state=after_state,
                note=body.note,
            )
    except Exception as e:
        logger.exception("[rbac] role-override upsert failed")
        raise HTTPException(500, f"Failed to save override: {e!s}") from e

    invalidate_override_cache(role)

    return {
        "id": row[0],
        "role": role,
        "permission": permission,
        "kind": kind,
        "created_by": actor_id,
        "created_at": row[1],
        "note": body.note,
    }


@router.delete(
    "/role-overrides/{role}/{permission}",
    operation_id="system.role_overrides.clear",
    status_code=204,
    summary="Clear an override (idempotent; 204 even on no-op)",
    responses={
        204: {"description": "Override cleared (or didn't exist)."},
        401: {"model": StepUpRequiredDetail, "description": "Step-up auth required (B236)."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the rbac.edit permission."},
        500: {"model": ErrorDetail, "description": "Failed to clear override."},
    },
)
async def clear_role_override(
    role: str,
    permission: str,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
    __: None = Depends(requires_step_up),  # B236
):
    """Clear any override for (role, permission). Idempotent — returns
    204 even when no override existed (no audit row in the no-op case)."""
    actor_id, actor_role = _actor(request)
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Capture the prior row for the audit before_state.
            cur.execute(
                "SELECT id, kind, created_by, created_at::text, note "
                "FROM rbac_role_overrides WHERE role = %s AND permission = %s",
                (role, permission),
            )
            prior = cur.fetchone()
            cur.execute(
                "DELETE FROM rbac_role_overrides WHERE role = %s AND permission = %s",
                (role, permission),
            )
            # B234: log only if there was actually something to clear.
            # Idempotent no-op deletes don't need an audit entry.
            if prior:
                from ..rbac import log_config_change
                before_state = {
                    "id": prior[0], "kind": prior[1], "created_by": prior[2],
                    "created_at": prior[3], "note": prior[4],
                }
                log_config_change(
                    cur,
                    action="clear",
                    target_role=role,
                    target_permission=permission,
                    actor_user_id=actor_id,
                    actor_role=actor_role,
                    before_state=before_state,
                    after_state=None,
                )
    except Exception as e:
        logger.exception("[rbac] role-override delete failed")
        raise HTTPException(500, f"Failed to clear override: {e!s}") from e

    invalidate_override_cache(role)
    return None


# ── Custom roles ─────────────────────────────────────────────────────

class CustomRoleCreateRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=512)
    based_on: Optional[str] = Field(default=None, max_length=64)
    permissions: Optional[list[str]] = None
    # B236 (v0.9.10.0): impersonation rank for the new custom role.
    # 0 = cannot impersonate anyone (default). 1-3 maps onto viewer/analyst/admin
    # tiers for the impersonation hierarchy. 4 (superadmin) is reserved for
    # the built-in role and is rejected if requested here.
    rank: int = Field(default=0, ge=0, le=3)


@router.post(
    "/custom-roles",
    operation_id="system.custom_roles.create",
    status_code=201,
    response_model=CustomRoleCreateResponse,
    response_model_exclude_none=True,
    summary="Create a custom role (B233; step-up required)",
    responses={
        201: {"description": "Custom role created."},
        400: {"model": ErrorDetail, "description": "Invalid slug, unknown permission, or based_on not built-in."},
        401: {"model": StepUpRequiredDetail, "description": "Step-up auth required (B236)."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the rbac.edit permission."},
        409: {"model": ErrorDetail, "description": "Slug collision or sensitive permission requested in seed."},
        500: {"model": ErrorDetail, "description": "Failed to create custom role."},
    },
)
async def create_custom_role(
    body: CustomRoleCreateRequest,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
    __: None = Depends(requires_step_up),  # B236
):
    """Create a new operator-defined role.

    If `permissions` is omitted and `based_on` is a built-in role, the
    new role's permission set starts as a copy of that role's defaults.
    If both are omitted, the role starts empty and overrides must be
    added separately via /role-overrides.

    B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
    rejected with 409 (was silently filtered before — operators were
    creating roles thinking they got the requested permissions).
    `based_on` seeds still filter sensitive perms from the source role's
    defaults, since the operator didn't ask for them explicitly.
    """
    role = body.role.lower()

    if not _CUSTOM_ROLE_SLUG_RE.match(role):
        raise HTTPException(400, f"Invalid role slug {role!r}. Use lowercase letters, "
                                  "digits, '-', and '_'; start with a letter.")

    if role in _BUILT_IN_ROLES:
        raise HTTPException(409, f"Role {role!r} collides with a built-in role.")

    existing = _list_custom_roles()
    if role in existing:
        raise HTTPException(409, f"Custom role {role!r} already exists.")

    based_on = body.based_on
    if based_on is not None and based_on not in _BUILT_IN_ROLES:
        raise HTTPException(400, f"based_on must be a built-in role; got {based_on!r}")

    # Compute the seed permission set.
    seed: set[str] = set()
    if body.permissions is not None:
        # Explicit list — validate each.
        for p in body.permissions:
            if p not in PERMISSIONS:
                raise HTTPException(400, f"Unknown permission in seed set: {p!r}")
        # B236: reject sensitive permissions explicitly requested by the
        # operator. Custom roles can be promoted to admin-tier later via
        # explicit /role-overrides on the admin or superadmin role; they
        # cannot be born with sensitive permissions.
        sensitive_in_seed = set(body.permissions) & SENSITIVE_PERMISSIONS
        if sensitive_in_seed:
            raise HTTPException(
                409,
                {
                    "error": "sensitive_in_seed",
                    "permissions": sorted(sensitive_in_seed),
                    "message": (
                        f"Cannot create custom role {role!r} with sensitive "
                        f"permissions: {sorted(sensitive_in_seed)}. Sensitive "
                        f"permissions can only be held by admin or superadmin "
                        f"roles."
                    ),
                },
            )
        seed = set(body.permissions)
    elif based_on:
        seed = set(default_permissions_for_role(based_on)) - set(SENSITIVE_PERMISSIONS)

    actor_id, actor_role = _actor(request)

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO rbac_custom_roles "
                "(role, display_name, description, based_on, created_by, rank) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (role, body.display_name, body.description, based_on, actor_id, body.rank),
            )
            # Materialise the seed as 'grant' override rows. Custom roles
            # have no static-catalog default, so every permission they
            # hold lives in rbac_role_overrides.
            for permission in sorted(seed):
                cur.execute(
                    "INSERT INTO rbac_role_overrides "
                    "(role, permission, kind, created_by, note) "
                    "VALUES (%s, %s, 'grant', %s, %s)",
                    (role, permission, actor_id,
                     f"Initial seed for custom role (based_on={based_on or 'none'})"),
                )

            # B234: log the role creation in the same transaction.
            from ..rbac import log_config_change
            log_config_change(
                cur,
                action="create_role",
                target_role=role,
                actor_user_id=actor_id,
                actor_role=actor_role,
                before_state=None,
                after_state={
                    "display_name": body.display_name,
                    "description": body.description,
                    "based_on": based_on,
                    "seed_permissions": sorted(seed),
                },
            )
    except Exception as e:
        logger.exception("[rbac] custom role create failed")
        raise HTTPException(500, f"Failed to create custom role: {e!s}") from e

    invalidate_override_cache(role)

    return {
        "role": role,
        "display_name": body.display_name,
        "description": body.description,
        "based_on": based_on,
        "permissions": sorted(seed),
        "created_by": actor_id,
    }


@router.delete(
    "/custom-roles/{role}",
    operation_id="system.custom_roles.delete",
    status_code=204,
    summary="Delete a custom role (refuses if any user is assigned)",
    responses={
        204: {"description": "Custom role deleted."},
        400: {"model": ErrorDetail, "description": "Cannot delete built-in roles, or users still assigned."},
        401: {"model": StepUpRequiredDetail, "description": "Step-up auth required (B236)."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the rbac.edit permission."},
        404: {"model": ErrorDetail, "description": "Custom role not found."},
    },
)
async def delete_custom_role(
    role: str,
    request: Request,
    _: None = Depends(requires("rbac.edit")),
    __: None = Depends(requires_step_up),  # B236
):
    """Delete a custom role. Refuses if any user is assigned this role
    (operator must reassign first). Built-in roles cannot be deleted.
    Override rows for this role are also deleted."""
    if role in _BUILT_IN_ROLES:
        raise HTTPException(400, f"Cannot delete built-in role {role!r}")

    existing = _list_custom_roles()
    if role not in existing:
        raise HTTPException(404, f"Custom role {role!r} not found")

    # Refuse if any user is currently assigned this role.
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users WHERE role = %s", (role,))
            count = cur.fetchone()[0]
    except Exception as e:
        logger.exception("[rbac] custom role delete: user count failed")
        raise HTTPException(500, f"Failed to check users: {e!s}") from e

    if count > 0:
        raise HTTPException(
            409,
            f"Cannot delete role {role!r}: {count} user(s) currently hold it. "
            "Reassign those users first."
        )

    actor_id, actor_role = _actor(request)
    role_meta = existing[role]
    permissions_held = sorted(list(all_permissions_for_role(role)))

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM rbac_role_overrides WHERE role = %s", (role,))
            cur.execute("DELETE FROM rbac_custom_roles WHERE role = %s", (role,))

            # B234: log the role deletion in the same transaction.
            from ..rbac import log_config_change
            log_config_change(
                cur,
                action="delete_role",
                target_role=role,
                actor_user_id=actor_id,
                actor_role=actor_role,
                before_state={
                    "display_name": role_meta.get("display_name"),
                    "description": role_meta.get("description"),
                    "based_on": role_meta.get("based_on"),
                    "permissions": permissions_held,
                },
                after_state=None,
            )
    except Exception as e:
        logger.exception("[rbac] custom role delete failed")
        raise HTTPException(500, f"Failed to delete custom role: {e!s}") from e

    invalidate_override_cache(role)
    return None


# ─────────────────────────────────────────────────────────────────────
# B234 (v0.9.9.2) — RBAC config audit log read endpoint.
# ─────────────────────────────────────────────────────────────────────

# Register read route alongside the write routes.
register_route("GET", "/api/system/rbac-audit-log", "system.audit")


@router.get(
    "/rbac-audit-log",
    operation_id="system.rbac_audit_log",
    response_model=RbacAuditLogResponse,
    response_model_exclude_none=True,
    summary="Paginated RBAC config-mutation audit log",
    responses={
        400: {"model": ErrorDetail, "description": "Unknown action filter."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def get_rbac_audit_log(
    request: Request,
    actor_user_id: Optional[str] = None,
    target_role: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    cursor: Optional[int] = None,
    limit: int = 50,
    _: None = Depends(requires("system.audit")),
) -> dict[str, Any]:
    """Recent RBAC config mutations. Filters: actor / target_role /
    action / time window. Cursor-based pagination (opaque numeric
    cursor = the smallest id from the previous page).

    Joins users.email so renamed users still show up correctly.

    Gated by system.audit (admin+). Read-only.
    """
    limit = max(1, min(limit, 500))

    where_clauses: list[str] = []
    params: list[Any] = []

    if actor_user_id:
        where_clauses.append("a.actor_user_id = %s")
        params.append(actor_user_id)
    if target_role:
        where_clauses.append("a.target_role = %s")
        params.append(target_role)
    if action:
        if action not in ("grant", "revoke", "clear", "create_role", "delete_role"):
            raise HTTPException(400, f"Unknown action filter: {action!r}")
        where_clauses.append("a.action = %s")
        params.append(action)
    if since:
        where_clauses.append("a.occurred_at >= %s::timestamptz")
        params.append(since)
    if until:
        where_clauses.append("a.occurred_at < %s::timestamptz")
        params.append(until)
    if cursor is not None:
        where_clauses.append("a.id < %s")
        params.append(cursor)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = (
        "SELECT a.id, a.occurred_at::text, a.actor_user_id, u.email AS actor_email, "
        "       a.actor_role, a.action, a.target_role, a.target_permission, "
        "       a.before_state, a.after_state, a.note, "
        # B248 (v0.9.10.7): per-resource ACL audit columns. Migration 062
        # adds them; older rows return NULL.
        "       a.target_resource_type, a.target_resource_id "
        "FROM rbac_config_audit a "
        # Cast both sides to text since users.id is uuid and audit stores text.
        "LEFT JOIN users u ON u.id::text = a.actor_user_id "
        f"{where_sql} "
        "ORDER BY a.id DESC "
        f"LIMIT {limit + 1}"  # fetch one extra to detect "more pages"
    )

    entries: list[dict[str, Any]] = []
    next_cursor: Optional[int] = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            for row in rows[:limit]:
                entries.append({
                    "id": row[0],
                    "occurred_at": row[1],
                    "actor_user_id": row[2],
                    "actor_email": row[3],
                    "actor_role": row[4],
                    "action": row[5],
                    "target_role": row[6],
                    "target_permission": row[7],
                    "before_state": row[8],
                    "after_state": row[9],
                    "note": row[10],
                    "target_resource_type": row[11],
                    "target_resource_id": row[12],
                })
            if len(rows) > limit:
                next_cursor = entries[-1]["id"]
    except Exception:
        logger.exception("[rbac] rbac-audit-log query failed (returning empty)")

    return {"entries": entries, "next_cursor": next_cursor}


# ── B271 (v0.9.11.13): /api/system/resources ─────────────────────────


import time as _time_for_resources
from concurrent.futures import ThreadPoolExecutor as _RPoolExec
from datetime import datetime as _datetime, timezone as _timezone

from ..services import server_resources as _server_res
from ..services import postgres_resources as _pg_res
from ..models.system import ResourcesResponse as _ResourcesResponse

register_route("GET", "/api/system/resources", "system.audit")

_RESOURCES_CACHE: dict = {"snapshot": None, "computed_at": 0.0}
_RESOURCES_CACHE_TTL_S = 30.0


def _collect_resources_snapshot() -> dict:
    """Cold-path collector — runs server + postgres queries in parallel.
    Returns a dict ready for JSON serialization."""
    with _RPoolExec(max_workers=2) as ex:
        f_server = ex.submit(_server_res.get_all)
        f_pg = ex.submit(_pg_res.get_all)
        server_snap = f_server.result()
        pg_snap = f_pg.result()

    return {
        "collected_at": _datetime.now(_timezone.utc).isoformat(),
        "server": _server_res.to_dict(server_snap),
        "postgres": pg_snap["postgres"],
        "tables": pg_snap["tables"],
        "plugins": pg_snap["plugins"],
        "syncs": pg_snap["syncs"],
        "indexes_largest": pg_snap["indexes_largest"],
    }


@router.get(
    "/resources",
    operation_id="system.resources",
    response_model=_ResourcesResponse,
    response_model_exclude_none=True,
    summary="System + Postgres + per-plugin resource snapshot (B271)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def get_system_resources(
    request: Request,
    fresh: bool = False,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return server (CPU, memory, swap, disk, load) + Postgres
    (db size, cache hit %, connections, pg_stat_statements installed)
    + per-table + per-plugin + per-sync metrics in one call.

    Cached in-process for 30 seconds; pass `?fresh=true` to bypass the
    cache and force a fresh collection.
    """
    now = _time_for_resources.monotonic()
    cached = _RESOURCES_CACHE.get("snapshot")
    cached_age = now - _RESOURCES_CACHE.get("computed_at", 0.0)

    if cached is not None and cached_age < _RESOURCES_CACHE_TTL_S and not fresh:
        return cached

    snap = _collect_resources_snapshot()
    _RESOURCES_CACHE["snapshot"] = snap
    _RESOURCES_CACHE["computed_at"] = now
    return snap


# ── B272 (v0.9.11.18): /api/system/diagnostics ───────────────────────


from ..services.system_diagnostics import (  # noqa: E402
    evaluate_diagnostics as _evaluate_diagnostics,
    summarize as _summarize_diagnostics,
)
from ..models.diagnostics import DiagnosticsResponse as _DiagnosticsResponse  # noqa: E402

register_route("GET", "/api/system/diagnostics", "system.audit")

_DIAGNOSTICS_CACHE: dict = {"snapshot": None, "computed_at": 0.0}
_DIAGNOSTICS_CACHE_TTL_S = 30.0


def _build_diagnostics_response() -> dict:
    """Compose the diagnostics response from a fresh resources snapshot.

    Reuses `_collect_resources_snapshot()` (defined above) so the
    underlying pg_stat_* + /proc collection runs once. The diagnostics
    endpoint and the resources endpoint maintain separate 30s caches —
    same TTL, different memo keys — so each can be invalidated
    independently and the UI doesn't see stale findings after a manual
    resources refresh.

    B274 (v0.9.11.20): merges `last_alerted_at` from the alert state
    table into each finding so the FindingCard can render an "alert
    sent N minutes ago" badge inline.
    """
    snap = _collect_resources_snapshot()
    findings = _evaluate_diagnostics(snap)
    # Merge last_alerted_at — returns {} when the bridge tables aren't
    # present yet (fresh deploy before migration 067).
    try:
        from ..services.diagnostic_alerts import (
            get_alert_state_for_findings as _get_alert_state,
            _affected_key as _alert_affected_key,
        )
        state = _get_alert_state(findings)
        for f in findings:
            key = (f.get("id"), _alert_affected_key(f))
            f["last_alerted_at"] = state.get(key)
    except Exception:
        # Bridge unavailable — surface findings without the badge data.
        pass
    return {
        "collected_at": snap.get("collected_at"),
        "summary": _summarize_diagnostics(findings),
        "findings": findings,
    }


@router.get(
    "/diagnostics",
    operation_id="system.diagnostics",
    response_model=_DiagnosticsResponse,
    response_model_exclude_none=True,
    summary="Diagnostic findings derived from /system/resources data (B272)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def get_system_diagnostics(
    request: Request,
    fresh: bool = False,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return findings produced by the diagnostic rules engine.

    12 pure-function rules (apps/api/src/services/system_diagnostics.py)
    each produce zero or more named findings with severity, evidence,
    and a recommendation. Cached in-process for 30 seconds; pass
    `?fresh=true` to bypass and re-evaluate.
    """
    now = _time_for_resources.monotonic()
    cached = _DIAGNOSTICS_CACHE.get("snapshot")
    cached_age = now - _DIAGNOSTICS_CACHE.get("computed_at", 0.0)

    if cached is not None and cached_age < _DIAGNOSTICS_CACHE_TTL_S and not fresh:
        return cached

    out = _build_diagnostics_response()
    _DIAGNOSTICS_CACHE["snapshot"] = out
    _DIAGNOSTICS_CACHE["computed_at"] = now
    return out


# ── B273 (v0.9.11.19): /api/system/*/history endpoints ───────────────


from ..services.resources_history import (  # noqa: E402
    SUPPORTED_METRICS as _HISTORY_METRICS,
    get_metric_history as _get_metric_history,
    get_finding_history as _get_finding_history,
)
from ..models.resources_history import (  # noqa: E402
    ResourcesHistoryResponse as _ResourcesHistoryResponse,
    DiagnosticsHistoryResponse as _DiagnosticsHistoryResponse,
)
from fastapi import HTTPException as _HistHTTPException  # noqa: E402

register_route("GET", "/api/system/resources/history", "system.audit")
register_route("GET", "/api/system/diagnostics/history", "system.audit")


@router.get(
    "/resources/history",
    operation_id="system.resources.history",
    response_model=_ResourcesHistoryResponse,
    response_model_exclude_none=True,
    summary="Time-series for one resource metric over the snapshot window (B273)",
    responses={
        400: {"model": ErrorDetail, "description": "Unsupported metric or missing required parameter."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def get_resources_history(
    request: Request,
    metric: str,
    plugin: Optional[str] = None,
    days: int = 30,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return [{snapshot_at, value}] over the last N days for one
    metric. Snapshots come from the daily worker
    `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).

    Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
    `plugin_size` requires the `plugin` parameter.
    """
    if metric not in _HISTORY_METRICS:
        raise _HistHTTPException(
            400,
            f"Unsupported metric: {metric!r}. "
            f"Supported: {', '.join(sorted(_HISTORY_METRICS))}.",
        )
    try:
        points = _get_metric_history(metric, plugin=plugin, days=days)
    except ValueError as e:
        raise _HistHTTPException(400, str(e))
    return {
        "metric": metric,
        "plugin": plugin,
        "days": days,
        "points": [
            {"snapshot_at": p.snapshot_at, "value": p.value}
            for p in points
        ],
    }


@router.get(
    "/diagnostics/history",
    operation_id="system.diagnostics.history",
    response_model=_DiagnosticsHistoryResponse,
    response_model_exclude_none=True,
    summary="Presence-per-snapshot history for one diagnostic finding (B273)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid finding_id."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def get_diagnostics_history(
    request: Request,
    id: str,
    days: int = 30,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return [{snapshot_at, present, severity}] over the last N days
    for one diagnostic finding. The frontend renders this as a
    timeline strip on the expanded FindingCard.

    Snapshots without the finding return `present=false, severity=null`.
    """
    try:
        points = _get_finding_history(id, days=days)
    except ValueError as e:
        raise _HistHTTPException(400, str(e))

    first_detected_at: Optional[str] = None
    for p in points:
        if p.present:
            first_detected_at = p.snapshot_at
            break

    return {
        "finding_id": id,
        "days": days,
        "points": [
            {"snapshot_at": p.snapshot_at, "present": p.present, "severity": p.severity}
            for p in points
        ],
        "first_detected_at": first_detected_at,
    }
