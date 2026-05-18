"""
Auth Middleware — protects all API routes except explicitly public ones.

Checks for authentication via (in order):
1. API key (X-API-Key header, SHA-256 hashed lookup)
2. Session token (X-Session-Token header, SHA-256 hashed lookup)

Public routes (no auth required):
- /api/health, /api/auth/status, /api/auth/setup, /api/auth/login, /api/auth/verify
- /api/shares/ (password checked by endpoint)
- /api/query (unauthenticated: plugin tables only)
- /api/activity (page view logging)
- /api/oauth/callback/ (B312 — provider redirects can't carry a session token;
  single-use state token bound to the originating user gates dispatch)
- /openapi.json, /openapi.yaml
- GET /api/plugins (list), /api/plugins/{slug}, /api/plugins/{slug}/dashboards/{name},
  /api/plugins/{slug}/widget/{file} — exactly the reads share-viewers + the host
  custom-widget loader need. Everything else under /api/plugins/* requires auth.
- GET /api/widget-runtime/* (host React shim served to plugin widget bundles)

Set AUTH_REQUIRED=false in .env to disable (for local development).
"""
import os
import re
import hashlib
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("nousviz.auth.middleware")

# Routes that don't require authentication
PUBLIC_PREFIXES = [
    "/api/health",
    "/api/auth/status",
    "/api/auth/setup",
    "/api/auth/login",
    "/api/auth/register",           # first-user registration + invite-based registration
    "/api/auth/accept-invite",      # invite acceptance (link-click flow)
    "/api/auth/verify",
    "/api/auth/setup/config",
    "/api/auth/forgot-password",    # B251: forgot-password (pre-auth)
    "/api/auth/reset-password",     # B251: reset-password consumption (pre-auth)
    # Share viewer paths only — management (list/update/revoke/access log) is auth-gated.
    # /api/shares/{id}           GET — viewer metadata (title, has_password, expires_at)
    # /api/shares/{id}/access    POST — password verify
    # Matched by PUBLIC_SHARE_VIEWER_PATTERNS below so PATCH/DELETE/log endpoints fall through to auth.
    "/api/query",                # read-only SQL proxy — has its own guardrails (blocked tables, row limits)
    "/api/activity",             # activity logging (no auth needed to record page views)
    "/api/webhooks/in/",         # inbound webhook ingestion (validated by endpoint slug + optional secret)
    # B312 (v0.10.3): plugin OAuth callback. Provider redirects can't carry a
    # NousViz session token, so the entry point is public. Single-use `state`
    # token bound to the originating user gates dispatch; see routes/oauth.py.
    "/api/oauth/callback/",
    "/openapi.json",
    "/openapi.yaml",
]

# Public GET-only patterns (read-only public access).
#
# B160 (v0.9.4.9): switched from prefix-startswith to regex-fullmatch.
# The previous "/api/plugins/" prefix matched every GET under that
# namespace — including plugin-shipped data routes and core admin
# endpoints — which leaked operationally sensitive plugin payloads to
# unauthenticated callers. The allowlist below is exactly the four
# read shapes that share-viewers + the host custom-widget loader need:
#
#   GET /api/plugins                            — list (loader on app boot)
#   GET /api/plugins/{slug}                     — manifest detail
#   GET /api/plugins/{slug}/dashboards/{name}   — dashboard spec
#   GET /api/plugins/{slug}/widget/{file}       — widget bundle (native ESM)
#
# Everything else under /api/plugins/... falls through to the auth
# check, regardless of whether it's a core route or a plugin-shipped
# route mounted via app.include_router.
#
# /api/widget-runtime/ stays public for the same reason as v0.9.4.7:
# native ESM import(url) can't carry session tokens, and the shim
# content is just a re-export of the host's React.
#
# Reserved slug guard: routes like /api/plugins/audit-log and
# /api/plugins/updates are core admin endpoints that share the URL
# shape of a manifest fetch. The {slug} regex below explicitly excludes
# them; anything matching one of these names falls through to the auth
# check rather than being treated as a public manifest read.
_RESERVED_PLUGIN_SLUGS = ("audit-log", "updates", "capabilities", "catalog")
_RESERVED_SLUG_ALT = "|".join(_RESERVED_PLUGIN_SLUGS)
# Negative lookahead: slug is one or more non-slash chars, but NOT one
# of the reserved names (with optional trailing slash so we don't allow
# /api/plugins/audit-log to slip through).
_SLUG = rf"(?!(?:{_RESERVED_SLUG_ALT})/?$)[^/]+"

PUBLIC_GET_PATTERNS = [
    re.compile(r"^/api/plugins/?$"),
    re.compile(rf"^/api/plugins/{_SLUG}/?$"),
    re.compile(rf"^/api/plugins/{_SLUG}/dashboards/[^/]+/?$"),
    re.compile(rf"^/api/plugins/{_SLUG}/widget/[^/]+$"),
    re.compile(r"^/api/widget-runtime/.+$"),
]

# B304 (v0.10.0.5): plugin admin-proxy paths.
# Matches `/api/plugins/<slug>/admin/...` and captures <slug>. Used by
# _verify_admin_session_cookie to scope cookie validation to opted-in
# plugins only.
_ADMIN_PROXY_PATH = re.compile(r"^/api/plugins/([^/]+)/admin(?:/|$)")


def _is_share_viewer_path(path: str, method: str) -> bool:
    """Match only the external viewer paths: GET /api/shares/{id} and POST /api/shares/{id}/access.
    Management endpoints (list, create, update, revoke, log) fall through to auth."""
    if not path.startswith("/api/shares/"):
        return False
    tail = path[len("/api/shares/"):]
    # Empty tail, or path containing "/" with anything other than "access" after it = not viewer
    if not tail:
        return False
    if "/" not in tail:
        # /api/shares/{id} — viewer metadata, GET only
        return method == "GET"
    share_id, rest = tail.split("/", 1)
    # /api/shares/{id}/access — password verify, POST only
    if rest == "access":
        return method == "POST"
    return False


def is_public_route(path: str, method: str) -> bool:
    """Check if a route is public (no auth required)."""
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    if method == "GET":
        for pattern in PUBLIC_GET_PATTERNS:
            if pattern.fullmatch(path):
                return True
    if _is_share_viewer_path(path, method):
        return True
    return False


def _verify_api_key(raw_key: str) -> str | None:
    """Check the key against the api_keys table. Returns the key name if valid."""
    try:
        from ..db import get_pg_conn
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE api_keys SET last_used_at = now() WHERE key_hash = %s AND revoked_at IS NULL RETURNING name",
                (hashed,),
            )
            row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        import logging
        logging.getLogger("nousviz.auth.middleware").error(f"API key verification failed: {e}")
        return None


def _verify_admin_session_cookie(request: Request) -> str | None:
    """B304 (v0.10.0.5): plugin admin-proxy cookie auth.

    For requests under `/api/plugins/<slug>/admin/*` where the plugin's
    manifest declares `frontend.admin_proxy: true`, accept a signed
    `nv_admin_<slug>` cookie as a valid credential.

    Returns the user_id (UUID string) if the cookie is valid, None
    otherwise. None means: no cookie, no matching path, plugin didn't
    opt in, cookie expired, hash mismatch, or DB failure (fail-closed).

    Narrowly scoped — fires only when:
      1. Path matches /api/plugins/<slug>/admin/*  (regex prefilter)
      2. Plugin manifest declares admin_proxy: true (mandatory opt-in)
      3. Request carries `nv_admin_<slug>` cookie (browser auto-attaches
         on path match thanks to Path scoping on the Set-Cookie)
      4. Cookie's SHA256 hash matches a non-expired plugin_admin_sessions
         row whose plugin_id matches the URL slug (slug binding)

    Mismatched cookie / wrong plugin / wrong path → returns None →
    middleware falls through to the existing 401 path. Preserves B160's
    "every /api/plugins/* path authenticated" invariant.
    """
    m = _ADMIN_PROXY_PATH.match(request.url.path)
    if not m:
        return None
    slug = m.group(1)

    raw = request.cookies.get(f"nv_admin_{slug}")
    if not raw:
        return None

    # Mandatory manifest opt-in: a cookie alone never grants access.
    try:
        from ..plugin_loader import is_admin_proxy_enabled
    except Exception:
        return None
    if not is_admin_proxy_enabled(slug):
        return None

    try:
        from ..db import get_pg_conn
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT user_id FROM plugin_admin_sessions
                   WHERE token_hash = %s
                     AND plugin_id = %s
                     AND expires_at > NOW()""",
                (token_hash, slug),
            )
            row = cur.fetchone()
        # v0.10.0.5.3: return `session:<email>` format to match the header
        # path. user_id column now stores the email string (migration 073
        # changed it from UUID after we discovered _verify_session_token
        # returns the email, not the UUID). Downstream code reads
        # request.state.user_identity expecting the `session:<...>` shape.
        return f"session:{row[0]}" if row else None
    except Exception as e:
        logger.error(f"Admin session cookie verification failed: {e}")
        return None


def get_authenticated_identity(request: Request) -> str | None:
    """Extract authenticated identity from request headers."""
    # API key — validate against hashed api_keys table
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_name = _verify_api_key(api_key)
        if key_name:
            return f"apikey:{key_name}"
        # Fall through — invalid key treated as unauthenticated

    # Session token — validate via X-Session-Token header (localStorage-based auth)
    # Note: cookie fallback removed — sessions use header-based tokens, not cookies (no CSRF risk)
    token = request.headers.get("X-Session-Token")
    if token:
        identity = _verify_session_token(token)
        if identity:
            return identity
        # Invalid/expired token falls through to unauthenticated

    # B304 (v0.10.0.5): plugin admin-proxy cookie (path-scoped, opt-in only).
    # Narrowest scope — fires only on /api/plugins/<slug>/admin/* paths AND
    # only when the plugin manifest declares admin_proxy: true. Header-based
    # auth above takes precedence; this path adds a SECOND credential type
    # without loosening anything for non-opted-in plugins.
    admin_user_id = _verify_admin_session_cookie(request)
    if admin_user_id:
        return admin_user_id

    return None


def _clear_expired_impersonation(token_hash: str) -> None:
    """B254 (v0.9.10.0.5): if the session has acting_as_until in the
    past, lazily clear the impersonation flags before the next
    permission resolution sees them.

    Atomic UPDATE with WHERE acting_as_until IS NOT NULL AND
    acting_as_until <= now() — a concurrent request that races to clear
    the same row sees zero affected rows and no-ops. The RETURNING
    clause lets us write an audit row only when this call actually
    cleared something.

    Best-effort: any exception is swallowed (logged to stderr) so the
    request continues. Never raises.
    """
    try:
        import hashlib  # noqa: F401  (already imported at module scope; kept for clarity)
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE user_sessions
                SET acting_as_user_id = NULL,
                    acting_as_until = NULL
                WHERE token_hash = %s
                  AND acting_as_until IS NOT NULL
                  AND acting_as_until <= now()
                RETURNING user_id::text, acting_as_user_id::text
                """,
                (token_hash,),
            )
            # NOTE: this RETURNING returns the POST-update values, so
            # acting_as_user_id is NULL on the affected row. We need
            # the pre-update target for audit; capture it before the
            # UPDATE via a CTE.
            # Re-run as a CTE to capture the prior target.
            row = cur.fetchone()
            if row is None:
                return  # nothing was cleared

            # Audit. We don't have the prior target in `row` (RETURNING
            # post-update), so we look it up from the audit context
            # we just lost. Cleanest: do the UPDATE+capture as a CTE.
            # See follow-up below; this branch rarely fires (only when
            # the lazy-clear actually happens) so a second roundtrip
            # is acceptable.
            actor_user_id = row[0]
            try:
                from ..rbac import log_config_change
                log_config_change(
                    cur,
                    action="impersonate_end",
                    target_role="unknown",
                    target_permission=None,
                    actor_user_id=actor_user_id,
                    actor_role=None,
                    before_state={"reason": "auto-expired"},
                    after_state=None,
                    note="auto-expired",
                )
            except Exception:
                # Audit best-effort; swallow.
                logger.exception("acting_as_until auto-expiry: audit insert failed")
    except Exception:
        logger.exception("acting_as_until auto-expiry failed (continuing)")


def _verify_session_token(token: str) -> str | None:
    """Check the session token against user_sessions table. Returns the
    *effective* user email if valid — when the session is impersonating,
    that's the target user, not the actor. The actor's identity is
    surfaced separately on request.state.real_user_id (set by AuthMiddleware
    after this returns).

    B236 (v0.9.10.0): added impersonation resolution.
    B254 (v0.9.10.0.5): lazily clear acting_as_until before resolving."""
    try:
        import hashlib
        from ..db import get_pg_conn
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # B254: clear past acting_as_until before the JOIN sees it.
        _clear_expired_impersonation(token_hash)

        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Resolve to the EFFECTIVE user: target if impersonating, actor
            # otherwise. JOIN on COALESCE(acting_as_user_id, user_id).
            cur.execute(
                """
                SELECT u.email
                FROM user_sessions s
                JOIN users u ON u.id = COALESCE(s.acting_as_user_id, s.user_id)
                WHERE s.token_hash = %s
                  AND s.expires_at > now()
                  AND u.is_active = true
                """,
                (token_hash,),
            )
            row = cur.fetchone()
        return f"session:{row[0]}" if row else None
    except Exception as e:
        import logging
        logging.getLogger("nousviz.auth.middleware").error(f"Session token verification failed: {e}")
        return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if auth is required
        auth_required = os.environ.get("AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")

        if not auth_required:
            return await call_next(request)

        path = request.url.path
        method = request.method

        # Skip public routes
        if is_public_route(path, method):
            return await call_next(request)

        # Check authentication
        identity = get_authenticated_identity(request)
        if not identity:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Use API key or session token."},
            )

        # Attach identity to request state for downstream use
        request.state.user_identity = identity

        # B236 (v0.9.10.0): if this is a session-token request and the
        # session is impersonating, stash both real_user_id and
        # acting_as_user_id on request.state so the RBAC audit logger and
        # /me endpoint can render the Option B identity shape correctly.
        if identity.startswith("session:"):
            try:
                token = request.headers.get("X-Session-Token")
                if token:
                    th = hashlib.sha256(token.encode()).hexdigest()
                    from ..db import get_pg_conn
                    with get_pg_conn() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            SELECT user_id::text, acting_as_user_id::text
                            FROM user_sessions
                            WHERE token_hash = %s AND expires_at > now()
                            """,
                            (th,),
                        )
                        row = cur.fetchone()
                    if row:
                        request.state.real_user_id = row[0]
                        request.state.acting_as_user_id = row[1]
            except Exception:
                # Audit-side metadata is best-effort; don't break the request
                # if the lookup fails.
                logging.getLogger("nousviz.auth.middleware").exception(
                    "session metadata lookup failed (request continues)"
                )

        # Update last_seen_at (debounced, max once per 60s per user)
        if identity.startswith("session:"):
            _update_last_seen(request)

        # B247 (v0.9.10.6): plugin-route permission enforcement.
        # Plugin routes registered via _auto_register_plugin_routes get a
        # `plugin.<slug>.<level>` permission string in ROUTE_PERMISSIONS.
        # Check it here for authenticated requests — core routes use the
        # per-handler `Depends(requires(...))` pattern and are unaffected.
        rbac_decision = _check_plugin_route_permission(request, method, path)
        if rbac_decision is not None:
            return rbac_decision

        return await call_next(request)


def _check_plugin_route_permission(request: Request, method: str, path: str):
    """B247: gate plugin-prefixed routes by their `plugin.<slug>.<level>`
    permission. Returns a 403 JSONResponse on deny; None on allow / N/A.

    Only plugin routes are checked here — core routes use `Depends(requires(...))`
    and are not double-checked. Detection rule: the route's permission
    string starts with "plugin." (the static-catalog prefix is "plugins.",
    so the dot-vs-s distinction is unambiguous).
    """
    # Late imports — avoid pulling RBAC plumbing at module import time.
    from ..rbac import ROUTE_PERMISSIONS
    from ..rbac.permissions import role_has_permission

    # Plugin auto-register stores `(METHOD, concrete_path)` keys. Look up
    # by the request's raw path; if the route was templated (e.g.
    # /api/plugins/{plugin_id}), the lookup misses and we fall through.
    permission = ROUTE_PERMISSIONS.get((method, path))
    if permission is None or not permission.startswith("plugin."):
        return None

    # Resolve user role from the session row metadata stashed during
    # auth check above.
    role = None
    try:
        from ..routes.auth import get_me
        user = get_me(request)
        role = user.get("role")
    except Exception:
        # Unauthenticated requests would already have been blocked by
        # the auth check above; this branch only fires on transient
        # session-lookup errors. Deny to fail safe.
        pass

    if role and role_has_permission(role, permission):
        return None  # Allowed.

    return JSONResponse(
        status_code=403,
        content={
            "detail": (
                f"Permission denied: this action requires {permission}."
            ),
        },
    )


import time as _time
_last_seen_cache: dict[str, float] = {}

def _update_last_seen(request: Request) -> None:
    token = request.headers.get("X-Session-Token")
    if not token:
        return
    now = _time.time()
    if now - _last_seen_cache.get(token, 0) < 60:
        return
    _last_seen_cache[token] = now
    try:
        from ..db import get_pg_conn
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users SET last_seen_at = now()
                FROM user_sessions s
                WHERE s.user_id = users.id AND s.token_hash = %s
            """, (token_hash,))
    except Exception:
        pass
