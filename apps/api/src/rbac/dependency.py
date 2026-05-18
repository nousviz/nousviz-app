"""
B227 (v0.9.8.0) — `requires(permission)` FastAPI dependency, plus check_access().

SHADOW MODE in v0.9.8.0: the dependency runs on every migrated route, logs
its verdict to auth_audit, but never raises 403. The inline `_require_*`
helpers in routes/auth.py are still the actual enforcement.

In v0.9.8.2 (B229) the SHADOW_MODE flag flips to False and registry verdicts
become authoritative. v0.9.9.0 layers a DB override table on top of the
built-in role-permission map.
"""
import logging
from typing import Callable, Optional

from fastapi import Request, HTTPException

from .permissions import role_has_permission
from .audit import log_decision

logger = logging.getLogger("nousviz.rbac.dependency")


# Module-level toggle. Shadow mode logs registry verdicts to auth_audit
# but never raises — inline _require_* shims do the actual gating.
# Enforced mode raises 403 on permission deny — registry is authoritative.
#
# Sequence:
#   v0.9.8.0-v0.9.9.2 — shadow=True (registry runs alongside inline shims)
#   v0.9.9.3 (B235)   — flipped to False; inline shims removed in same release
#   v0.9.9.4+         — stays False
SHADOW_MODE = False


def requires(permission: str) -> Callable:
    """Returns a FastAPI dependency function gating on `permission`.

    In shadow mode (v0.9.8.0): logs the would-be verdict to auth_audit but
    never raises 403. Inline `_require_*` calls (still active on every route)
    do the real enforcement.

    In enforced mode (v0.9.8.2+): raises 403 if the user doesn't hold the
    permission.

    Usage:
        from fastapi import Depends
        from src.rbac import requires

        @router.post("/api/widgets")
        def create_widget(_: None = Depends(requires("widgets.write"))):
            ...
    """
    def dep(request: Request) -> None:
        # B235 hotfix: defer to the auth middleware's public-route allowlist.
        # Some registered routes (e.g. GET /api/plugins/{slug}, /api/query)
        # are intentionally public — share viewers and the unauth plugin-
        # table query path depend on them. Pre-flip, shadow mode logged but
        # didn't enforce, so the conflict between "registered with permission"
        # and "public per middleware" was invisible. Now we short-circuit
        # here when the path is public, log an allow row for observability,
        # and skip the permission check entirely.
        from ..middleware.auth import is_public_route

        path = str(request.url.path)
        method = request.method
        if is_public_route(path, method):
            log_decision(
                user_id=None,
                user_role=None,
                permission=permission,
                route_method=method,
                route_path=path,
                decision="allow",
                mode="shadow" if SHADOW_MODE else "enforced",
                reason="public route",
            )
            return

        # Late import: routes/auth.py will import from us in B228+.
        # Lifting this to module scope creates a circular import.
        try:
            from ..routes.auth import get_me
            user = get_me(request)
            user_id = user.get("id")
            user_role = user.get("role")
        except HTTPException:
            # Unauthenticated request. Log as deny; don't enforce in shadow mode.
            user_id = None
            user_role = None
        except Exception:
            # Anything else (e.g. session lookup error): log as deny but
            # don't 403 in shadow mode. Inline check will surface the real
            # error to the user.
            logger.exception("[rbac] get_me failed during shadow check (continuing)")
            user_id = None
            user_role = None

        allowed = role_has_permission(user_role or "", permission)

        # B236 (v0.9.10.0): when the session is impersonating, get_me has
        # already resolved to the *effective* user (target). The actor is
        # discoverable via the session row's user_id; we surface it on the
        # audit row via acting_as_user_id so the trail records both.
        acting_as = getattr(request.state, "acting_as_user_id", None)

        log_decision(
            user_id=user_id,
            user_role=user_role,
            permission=permission,
            route_method=method,
            route_path=path,
            decision="allow" if allowed else "deny",
            mode="shadow" if SHADOW_MODE else "enforced",
            reason=None if allowed else (
                f"role={user_role!r} lacks {permission!r}"
                if user_role else "unauthenticated"
            ),
            acting_as_user_id=acting_as,
        )

        if SHADOW_MODE:
            return  # logged, but don't enforce

        if not allowed:
            raise HTTPException(
                403,
                f"Permission denied: this action requires {permission}.",
            )

    # Stash the permission on the function for introspection by the matrix
    # UI in B230. FastAPI doesn't preserve the closure variable otherwise.
    dep.__rbac_permission__ = permission  # type: ignore[attr-defined]
    return dep


def check_access(
    user: dict,
    permission: str,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> bool:
    """Programmatic permission check, for handlers that need to inline-test.

    B248 (v0.9.10.7): when both `resource_type` and `resource_id` are
    provided, the check consults `resource_acls` and the per-type
    default policy. The resolution order is documented in
    `apps.api.src.rbac.resource_acls.check_resource_access`.

    When `resource_type` is None (or `resource_id` is None), falls back
    to the role-permission check. Existing callers that passed only
    `resource_id` (the placeholder no-op since v0.9.8) get the same
    behaviour as before — the parameter is now honoured *only* if both
    are present.
    """
    if not user:
        return False
    if resource_type and resource_id:
        # Late import: resource_acls.py imports permissions.py which
        # imports this module — circular if hoisted to module scope.
        from .resource_acls import check_resource_access
        return check_resource_access(user, permission, resource_type, resource_id)
    role = user.get("role") or ""
    return role_has_permission(role, permission)


def requires_resource(
    resource_type: str,
    permission: str,
    *,
    id_param: str = "slug",
) -> Callable:
    """B248 (v0.9.10.7): FastAPI dep gating on a per-resource ACL plus
    role permission.

    Stack on top of `requires(<permission>)` when you want both: a
    role-level guard AND a per-resource grant. Or use this alone — it
    consults the role permission internally as part of the resolution.

    The path-parameter named `id_param` (default 'slug') is read from
    `request.path_params` to identify the resource. Resource types and
    their id-column conventions live in
    `apps.api.src.rbac.resource_acls._REGISTRY`.

    Usage:

        from src.rbac import requires_resource

        @router.get(
            "/api/dashboards/{slug}",
            dependencies=[Depends(requires_resource('dashboard', 'dashboards.read'))],
        )
        async def get_dashboard(slug: str): ...

    Verdict logging mirrors the role-permission `requires()` dep.
    """
    def dep(request: Request) -> None:
        from ..middleware.auth import is_public_route

        path = str(request.url.path)
        method = request.method
        if is_public_route(path, method):
            log_decision(
                user_id=None,
                user_role=None,
                permission=permission,
                route_method=method,
                route_path=path,
                decision="allow",
                mode="shadow" if SHADOW_MODE else "enforced",
                reason="public route",
            )
            return

        try:
            from ..routes.auth import get_me
            user = get_me(request)
        except HTTPException:
            user = None
        except Exception:
            logger.exception("[rbac] get_me failed during requires_resource (continuing)")
            user = None

        resource_id = request.path_params.get(id_param)
        if not resource_id:
            # No resource id — fall back to role-only check. Logged as
            # such so the trail is honest.
            allowed = bool(user and role_has_permission(user.get("role") or "", permission))
            log_decision(
                user_id=(user or {}).get("id"),
                user_role=(user or {}).get("role"),
                permission=permission,
                route_method=method,
                route_path=path,
                decision="allow" if allowed else "deny",
                mode="shadow" if SHADOW_MODE else "enforced",
                reason=f"no {id_param!r} path-param; role-only check",
            )
            if SHADOW_MODE or allowed:
                return
            raise HTTPException(403, f"Permission denied: this action requires {permission}.")

        from .resource_acls import check_resource_access
        allowed = check_resource_access(user or {}, permission, resource_type, str(resource_id))

        acting_as = getattr(request.state, "acting_as_user_id", None)
        log_decision(
            user_id=(user or {}).get("id"),
            user_role=(user or {}).get("role"),
            permission=permission,
            route_method=method,
            route_path=path,
            decision="allow" if allowed else "deny",
            mode="shadow" if SHADOW_MODE else "enforced",
            reason=None if allowed else (
                f"resource={resource_type}/{resource_id} no grant for "
                f"role={(user or {}).get('role')!r}, user={(user or {}).get('id')!r}"
            ),
            acting_as_user_id=acting_as,
        )

        if SHADOW_MODE:
            return
        if not allowed:
            raise HTTPException(
                403,
                f"Permission denied: this action requires {permission} on {resource_type} {resource_id!r}.",
            )

    dep.__rbac_permission__ = permission  # type: ignore[attr-defined]
    dep.__rbac_resource_type__ = resource_type  # type: ignore[attr-defined]
    return dep


def requires_step_up(request: Request) -> None:
    """B236 (v0.9.10.0): require recent re-authentication for sensitive ops.

    Read user_sessions.step_up_until for the active session. If NULL or
    past, raise 401 with `stepup_required` so the frontend can prompt for
    password and retry.

    Used as a FastAPI dep on RBAC config write endpoints and on
    impersonation. Stack on top of `requires('rbac.edit')` (or whatever
    permission gates the route normally) — both must pass.
    """
    import hashlib
    from datetime import datetime, timezone
    from ..db import get_pg_conn, dict_cursor

    token = request.headers.get("X-Session-Token")
    if not token:
        # Not authenticated at all — let the auth middleware surface this
        # as 401, but we'll still fail loud here for direct callers.
        raise HTTPException(
            status_code=401,
            detail={
                "error": "stepup_required",
                "message": "This action requires re-authentication. Please confirm your password.",
            },
        )

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute(
                """
                SELECT step_up_until FROM user_sessions
                WHERE token_hash = %s AND expires_at > now()
                """,
                (token_hash,),
            )
            row = cur.fetchone()
    except Exception:
        logger.exception("[rbac] step-up check failed")
        raise HTTPException(
            status_code=503,
            detail="Step-up verification failed. Try again.",
        )

    step_up_until = row.get("step_up_until") if row else None
    if not step_up_until or step_up_until <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "stepup_required",
                "message": "This action requires re-authentication. Please confirm your password.",
            },
        )
    # Step-up is valid — pass through.
