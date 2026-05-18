"""
B227 (v0.9.8.0) — RBAC subsystem.

Public surface:
- requires(permission) — FastAPI dependency factory
- check_access(user, permission, resource_id=None) — programmatic check
- role_has_permission(role, permission) — pure predicate
- ROLE_PERMISSIONS, PERMISSIONS, SENSITIVE_PERMISSIONS — registry data
- ROUTE_PERMISSIONS, PUBLIC_ROUTES — route registry + public allowlist
- register_route, get_route_permission, is_public — route registry helpers
- log_decision — audit logger
- SHADOW_MODE — flips to False in v0.9.8.2 (B229)
"""
from .permissions import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    SENSITIVE_PERMISSIONS,
    BUILTIN_ROLE_RANK,
    role_rank,
    role_has_permission,
    all_permissions_for_role,
    default_permissions_for_role,
)
from .overrides import (
    resolve_role_permissions,
    get_overrides_for_role,
    invalidate_cache as invalidate_override_cache,
    invalidate_all_caches as invalidate_all_override_caches,
)
from .routes import (
    ROUTE_PERMISSIONS,
    PUBLIC_ROUTES,
    register_route,
    get_route_permission,
    is_public,
)
from .audit import log_decision
from .config_audit import log_config_change
from .dependency import requires, requires_resource, requires_step_up, check_access, SHADOW_MODE
from .plugin_visibility import (
    UNRESTRICTED_ROLES,
    is_per_user_filter_enabled,
    allowed_plugin_slugs_for_user,
    filter_plugins_for_user,
    users_with_restricted_access_excluding,
    get_user_plugin_access,
    set_user_plugin_access,
    apply_plugin_access_with_cursor,
    user_can_access_plugin,
    requires_plugin_access,
)

__all__ = [
    "PERMISSIONS",
    "ROLE_PERMISSIONS",
    "SENSITIVE_PERMISSIONS",
    "BUILTIN_ROLE_RANK",
    "role_rank",
    "role_has_permission",
    "all_permissions_for_role",
    "default_permissions_for_role",
    "resolve_role_permissions",
    "get_overrides_for_role",
    "invalidate_override_cache",
    "invalidate_all_override_caches",
    "ROUTE_PERMISSIONS",
    "PUBLIC_ROUTES",
    "register_route",
    "get_route_permission",
    "is_public",
    "log_decision",
    "log_config_change",
    "requires",
    "requires_resource",
    "requires_step_up",
    "check_access",
    "SHADOW_MODE",
    "UNRESTRICTED_ROLES",
    "is_per_user_filter_enabled",
    "allowed_plugin_slugs_for_user",
    "filter_plugins_for_user",
    "users_with_restricted_access_excluding",
    "get_user_plugin_access",
    "set_user_plugin_access",
    "apply_plugin_access_with_cursor",
    "user_can_access_plugin",
    "requires_plugin_access",
]
