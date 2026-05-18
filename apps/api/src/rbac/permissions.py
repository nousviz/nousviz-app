"""
B227 (v0.9.8.0) — Permission catalog and role-to-permission map.

This is the canonical source of truth for what each built-in role can do in
v0.9.8.x. v0.9.9.0 layers a DB override table on top of these defaults; for
v0.9.8.x this file IS the role definition.

Naming convention: lowercase, dot-separated, "<resource>.<verb>".
Adding a permission: add to PERMISSIONS, then assign to the appropriate
roles in ROLE_PERMISSIONS, then mark sensitive if applicable.
"""
from typing import FrozenSet, Mapping


# Permission catalog. Every permission referenced in ROLE_PERMISSIONS must be
# listed here — the assertion at module bottom enforces it.
PERMISSIONS: Mapping[str, str] = {
    # System / admin (B227)
    "system.audit": "View the RBAC matrix and audit logs",
    "system.admin": "System-level config, restart, environment changes",
    "system.logs": "View application and system log streams",
    "users.read_self": "View own profile (always granted to authenticated users)",
    "users.manage": "Create, edit, delete, change roles for non-admin users",
    "users.manage_admins": "Modify users whose current role is admin or superadmin",
    "admin.cli": "Run admin CLI commands via the web shell",
    # Plugins (B227)
    "plugins.install": "Install or uninstall plugins",
    "plugins.configure": "Edit plugin settings",
    "plugins.read": "View installed plugins and their manifests",
    # Settings (B228)
    "settings.read": "View platform settings (database, email, git, deploy keys, API keys)",
    "settings.write": "Edit platform settings",
    # Dashboards / data (B227)
    "dashboards.read": "View dashboards",
    "dashboards.write": "Create or edit dashboards",
    "data.query": "Run queries against plugin tables",
    "data.sync": "Trigger plugin syncs",
    "datasets.read": "Browse plugin datasets and their rows",
    "datasets.write": "Upload datasets, modify dataset metadata",
    "query.run": "Execute /api/query SQL against plugin schemas",
    # Alerts / shares (B227)
    "alerts.read": "View alerts",
    "alerts.write": "Create, edit, mute alerts",
    "shares.read": "View shared links",
    "shares.write": "Create or revoke shared links",
    # B228 additions — connections, fusions, notes, annotations, jobs
    "connections.read": "View configured connections (DBs, APIs)",
    "connections.write": "Create, edit, delete connections",
    "fusions.read": "View fusions (cross-plugin data composition)",
    "fusions.write": "Create or edit fusions",
    "notes.read": "View notes",
    "notes.write": "Create, edit, delete notes",
    "annotations.read": "View dashboard annotations",
    "annotations.write": "Create, edit, delete annotations",
    "jobs.read": "View async job runs and their status",
    "jobs.write": "Cancel async jobs",
    # Reserved — not yet enforced; declared so the catalog is stable across
    # the v0.9.8 → v0.9.9 transition.
    "rbac.edit": "Modify role-permission assignments (v0.9.9+)",
}


# Sensitive permissions cannot be granted to non-admin/superadmin custom roles
# in v0.9.9+. The matrix editor's role-create UI will refuse. v0.9.8.x doesn't
# enforce this directly (no editing yet), but the registry is published now so
# downstream consumers (matrix UI, future custom-role editor) can rely on it.
SENSITIVE_PERMISSIONS: FrozenSet[str] = frozenset({
    "system.audit",
    "system.admin",
    "users.manage",
    "users.manage_admins",
    "plugins.install",
    "admin.cli",
    "rbac.edit",
})


# Built-in roles. Role hierarchy is implicit in the permission sets:
# superadmin ⊇ admin ⊇ analyst ⊇ viewer.
#
# When v0.9.9.0 adds DB overrides, an admin can edit these per-deployment.
# The defaults here are the fallback if no override row exists.
_VIEWER_PERMS = frozenset({
    "users.read_self",
    "plugins.read",
    "dashboards.read",
    "data.query",
    "datasets.read",
    "query.run",
    "alerts.read",
    "shares.read",
    "connections.read",
    "fusions.read",
    "notes.read",
    "annotations.read",
    "settings.read",
})

_ANALYST_PERMS = _VIEWER_PERMS | frozenset({
    "dashboards.write",
    "data.sync",
    "datasets.write",
    "alerts.write",
    "shares.write",
    "connections.write",
    "fusions.write",
    "notes.write",
    "annotations.write",
    "jobs.read",
    "jobs.write",
})

_ADMIN_PERMS = _ANALYST_PERMS | frozenset({
    "system.audit",
    "system.admin",
    "system.logs",
    "users.manage",
    "plugins.install",
    "plugins.configure",
    "settings.write",
})

# admin.cli is currently superadmin-only via the inline check in admin.py.
# Putting it in superadmin-only matches today's behaviour; a v0.9.9 operator
# can grant it to admin via the matrix UI if they want.
_SUPERADMIN_PERMS = _ADMIN_PERMS | frozenset({
    "users.manage_admins",
    "admin.cli",
    "rbac.edit",
})

# ROLE_PERMISSIONS = the static catalog *default*. v0.9.8.x: this is the
# only source of truth. v0.9.9.0 (B232): operators layer DB-backed
# overrides on top via apps/api/src/rbac/overrides.py. This dict still
# represents the code defaults; callers that want the resolved
# (post-override) set should use role_has_permission() or
# all_permissions_for_role(), which consult the override layer.
ROLE_PERMISSIONS: Mapping[str, FrozenSet[str]] = {
    "viewer": _VIEWER_PERMS,
    "analyst": _ANALYST_PERMS,
    "admin": _ADMIN_PERMS,
    "superadmin": _SUPERADMIN_PERMS,
}


# B236 (v0.9.10.0): role rank for impersonation.
#
# Higher number = higher rank. The rule for impersonation is
# `actor_rank > target_rank` (strict greater) — you may only impersonate
# users below you in the hierarchy.
#
# Built-in roles have fixed ranks 1-4. Custom roles get a numeric rank
# stored in rbac_custom_roles.rank (0-3, never 4 — superadmin is reserved
# for the built-in role). Custom roles default to rank 0 (cannot
# impersonate anyone) unless the operator sets otherwise.
#
# `role_rank(role)` looks up built-in ranks here first, then falls back
# to the rbac_custom_roles table for custom roles. Unknown roles → 0.
BUILTIN_ROLE_RANK: Mapping[str, int] = {
    "viewer": 1,
    "analyst": 2,
    "admin": 3,
    "superadmin": 4,
}


def role_rank(role: str) -> int:
    """Return numeric rank for `role`. Built-in roles use BUILTIN_ROLE_RANK;
    custom roles look up rbac_custom_roles.rank. Unknown / missing → 0.

    The look-up is cheap (single indexed query) and uncached for now —
    impersonation flows are operator-driven and infrequent. If this ends
    up on a hot path, cache via the same TTL pattern as resolve_role_permissions.
    """
    if not role:
        return 0
    if role in BUILTIN_ROLE_RANK:
        return BUILTIN_ROLE_RANK[role]
    # Custom role — look up its assigned rank from the DB.
    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT rank FROM rbac_custom_roles WHERE role = %s",
                (role,),
            )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        # Fail closed: any DB error → rank 0 (cannot impersonate).
        import logging as _lg
        _lg.getLogger("nousviz.rbac").warning(
            f"role_rank: lookup failed for custom role {role!r}; treating as 0",
            exc_info=True,
        )
        return 0


def role_has_permission(role: str, permission: str) -> bool:
    """Predicate — does `role` hold `permission` after applying
    operator-controlled DB overrides on top of the static catalog?

    Returns False for unknown roles (including None) and unknown permissions.
    Cached per-role with a 30-second TTL; the cache is invalidated by
    the override-write endpoints in B233.

    v0.9.9.0+: consults rbac_role_overrides via overrides.resolve_role_permissions.
    Falls back to the static catalog if the override query fails.
    """
    if not role:
        return False
    # Late import to avoid a circular dep — overrides.py imports this module.
    from .overrides import resolve_role_permissions
    return permission in resolve_role_permissions(role)


def all_permissions_for_role(role: str) -> FrozenSet[str]:
    """Return the full set of permissions a role holds, resolved through
    the override layer (B232+)."""
    if not role:
        return frozenset()
    from .overrides import resolve_role_permissions
    return resolve_role_permissions(role)


def default_permissions_for_role(role: str) -> FrozenSet[str]:
    """Return the static-catalog default permission set for a role,
    BEFORE applying operator overrides. Used by the matrix UI to render
    'modified from default' indicators (the matrix needs to know what
    'default' is independently of what's currently effective)."""
    return ROLE_PERMISSIONS.get(role, frozenset())


# Self-test on import: every permission referenced in any role must exist
# in PERMISSIONS, and every sensitive permission must exist in PERMISSIONS.
# Catches typos at import time rather than at first auth check.
def _validate_catalog() -> None:
    declared = set(PERMISSIONS.keys())
    for role, perms in ROLE_PERMISSIONS.items():
        unknown = perms - declared
        if unknown:
            raise RuntimeError(
                f"RBAC catalog: role {role!r} references unknown permissions: "
                f"{sorted(unknown)}. Add them to PERMISSIONS or fix the typo."
            )
    sensitive_unknown = SENSITIVE_PERMISSIONS - declared
    if sensitive_unknown:
        raise RuntimeError(
            f"RBAC catalog: SENSITIVE_PERMISSIONS contains unknown permissions: "
            f"{sorted(sensitive_unknown)}. Add them to PERMISSIONS or fix the typo."
        )


_validate_catalog()
