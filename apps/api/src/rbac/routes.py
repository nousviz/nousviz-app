"""
B227 (v0.9.8.0) — Route → permission registry, plus PUBLIC_ROUTES allowlist.

Two data structures:

- ROUTE_PERMISSIONS: (METHOD, PATH_TEMPLATE) → permission string. Populated
  via register_route() — typically by code in B228 that pairs each
  Depends(requires(...)) with an explicit registration call.

- PUBLIC_ROUTES: a frozen set of (METHOD, PATH) tuples that are intentionally
  unauthenticated. These bypass auth entirely; v0.9.8.2's default-deny does
  NOT 403 them.

A route that is neither registered nor public will, after v0.9.8.2's flip,
return 403 RBAC_NOT_REGISTERED. That's the desired failure mode — silent
permission leaks become loud failures.
"""
import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple, Optional


# (METHOD, PATH_TEMPLATE) → permission string.
# PATH_TEMPLATE uses FastAPI conventions: "{plugin_id}", "{share_id}", etc.
ROUTE_PERMISSIONS: Dict[Tuple[str, str], str] = {}


def register_route(method: str, path: str, permission: str) -> None:
    """Register that `method path` requires `permission`.

    Raises RuntimeError on conflict (same route registered with two different
    permissions). Idempotent for the same-permission case.
    """
    key = (method.upper(), path)
    existing = ROUTE_PERMISSIONS.get(key)
    if existing and existing != permission:
        raise RuntimeError(
            f"Route conflict: {method} {path} registered as both "
            f"{existing!r} and {permission!r}. Only one permission per route."
        )
    ROUTE_PERMISSIONS[key] = permission


def get_route_permission(method: str, path: str) -> Optional[str]:
    """Return the permission required for this route, or None if unregistered."""
    return ROUTE_PERMISSIONS.get((method.upper(), path))


# ─────────────────────────────────────────────────────────────────────
# B348: plugin route guards — step-up and sensitive levels.
#
# A plugin manifest rule with `step_up: true` or a sensitive level
# (`reveal_secrets`) registers a guard for each route it governs. The
# auth middleware enforces guards before the request reaches the plugin:
# session required (no API keys for step-up), the permission, a recent
# step-up, and — for `reveal_secrets` — a credential_audit_log row after
# a 2xx response.
#
# Unlike ROUTE_PERMISSIONS (looked up by the raw request path), guards
# also match templated paths such as `/api/plugins/x/accounts/{id}/reveal`.
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PluginRouteGuard:
    slug: str
    method: str
    path: str          # route path template, e.g. /api/plugins/x/a/{id}/reveal
    level: str
    permission: str    # plugin.<slug>.<level>
    step_up: bool
    audit_reveal: bool  # True for reveal_secrets: write a `revealed` row
    # Set when the plugin's `permissions:` block uses step_up /
    # reveal_secrets but is invalid: every route of the plugin answers 503
    # instead of falling back to legacy defaults (fail closed).
    blocked: Optional[str] = None


PLUGIN_ROUTE_GUARDS: Dict[Tuple[str, str], PluginRouteGuard] = {}
_GUARD_PATTERNS: List[Tuple[str, "re.Pattern[str]", PluginRouteGuard]] = []


def _compile_template(path: str) -> "re.Pattern[str]":
    """Compile a FastAPI path template to a full-match regex, using the
    same rules Starlette uses to route the request."""
    from starlette.routing import compile_path
    regex, _fmt, _convertors = compile_path(path)
    return regex


def register_plugin_route_guard(guard: PluginRouteGuard) -> None:
    """Register (or replace) the guard for `guard.method guard.path`."""
    key = (guard.method.upper(), guard.path)
    PLUGIN_ROUTE_GUARDS[key] = guard
    _GUARD_PATTERNS[:] = [g for g in _GUARD_PATTERNS if (g[0], g[2].path) != key]
    if "{" in guard.path:
        _GUARD_PATTERNS.append((key[0], _compile_template(guard.path), guard))


def match_plugin_route_guard(method: str, path: str) -> Optional[PluginRouteGuard]:
    """Return the guard for a concrete request (method, path), or None.
    Exact routes first, then templated ones."""
    method = method.upper()
    guard = PLUGIN_ROUTE_GUARDS.get((method, path))
    if guard is not None:
        return guard
    for m, pattern, g in _GUARD_PATTERNS:
        if m == method and pattern.match(path):
            return g
    return None


# ─────────────────────────────────────────────────────────────────────
# PUBLIC_ROUTES: explicit allowlist of unauthenticated routes.
#
# Add to this set ONLY when the route truly needs to be reachable without
# authentication. Each entry should have a comment explaining why.
#
# Anything NOT in PUBLIC_ROUTES and NOT in ROUTE_PERMISSIONS will 403 after
# B229's default-deny flip. That is the desired failure mode.
# ─────────────────────────────────────────────────────────────────────
PUBLIC_ROUTES: FrozenSet[Tuple[str, str]] = frozenset({
    # Healthcheck — load balancer / monitoring; cannot require auth
    ("GET", "/api/health"),
    ("GET", "/api/health/config"),

    # Auth flow — login itself cannot require auth
    ("GET", "/api/auth/status"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/accept-invite"),
    ("GET", "/api/auth/verify"),
    ("POST", "/api/auth/logout"),

    # First-run setup flow — runs before any user exists
    ("POST", "/api/auth/setup/config"),
    ("POST", "/api/auth/setup"),

    # OpenAPI spec (B211 made plugin routes opt-in to spec inclusion;
    # the spec endpoints themselves are public, industry norm)
    ("GET", "/openapi.json"),
    ("GET", "/openapi.yaml"),

    # Share viewer (matches middleware/auth.py:_is_share_viewer_path)
    ("GET", "/api/shares/{share_id}"),
    ("POST", "/api/shares/{share_id}/access"),

    # Widget runtime — static JS shims served to plugin widget bundles.
    # Browser fetches these before user context exists; cannot require auth.
    ("GET", "/api/widget-runtime/react.js"),
    ("GET", "/api/widget-runtime/react-jsx-runtime.js"),

    # B312 (v0.10.3): plugin OAuth callback. The provider redirects the
    # user's browser to this URL after they authorize on the third-party
    # service; the redirect cannot carry a NousViz session token. Auth is
    # established by the single-use `state` token bound to the originating
    # user when the plugin called nousviz_sdk.oauth.start_flow.
    ("GET", "/api/oauth/callback/{plugin_slug}"),
})


def is_public(method: str, path: str) -> bool:
    """Return True if this exact (method, path) is in PUBLIC_ROUTES."""
    return (method.upper(), path) in PUBLIC_ROUTES
