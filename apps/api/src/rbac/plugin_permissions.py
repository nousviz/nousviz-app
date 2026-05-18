"""B247 (v0.9.10.6): dynamic plugin permission entries in the RBAC catalog.

Built-in permissions like `system.audit` are declared statically in
`permissions.py`. Plugin permissions like `plugin.<slug>.<level>` are
**dynamic** — they only exist for currently-installed plugins and need
to appear in the catalog after the plugin loader runs.

The plugin loader calls `register_plugin_permissions(slug, levels)`
once per plugin during startup. The function:

1. Adds `plugin.<slug>.<level>` entries to the live PERMISSIONS dict.
2. Adds default role-mappings (`viewer` → read, `analyst` → write,
   etc.) so every role has a sensible starting point.

Operators can override the role-mappings via the matrix UI's
`rbac_role_overrides` table — same plumbing core permissions use.

This module is import-safe: importing it doesn't trigger plugin
discovery. The loader calls `register_plugin_permissions()` explicitly.
"""
from __future__ import annotations

import logging
from typing import Iterable

from ..plugin_manifest import LEVELS, permission_string
from .permissions import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
)

logger = logging.getLogger("nousviz.rbac.plugin_permissions")


# Mapping from level → built-in roles that hold it by default.
# Operators override per-plugin via the matrix UI.
_DEFAULT_ROLE_GRANTS: dict[str, frozenset[str]] = {
    "read":      frozenset({"viewer", "analyst", "admin", "superadmin"}),
    "write":     frozenset({"analyst", "admin", "superadmin"}),
    "configure": frozenset({"admin", "superadmin"}),
    "admin":     frozenset({"superadmin"}),
}


# Track which plugin permissions we've registered so we can
# (a) avoid double-registering on hot-reload and
# (b) report the active set to the matrix UI.
_REGISTERED_PLUGIN_PERMISSIONS: set[str] = set()


def register_plugin_permissions(slug: str, levels: Iterable[str] = LEVELS) -> list[str]:
    """Register `plugin.<slug>.<level>` for each level in the catalog.

    Default role grants:
        read       → viewer+
        write      → analyst+
        configure  → admin+
        admin      → superadmin

    Returns the list of permission strings registered (or already
    present, on a subsequent call).
    """
    out: list[str] = []
    for level in levels:
        if level not in LEVELS:
            logger.error(
                "[rbac] plugin %s: ignoring invalid level %r (must be one of %s)",
                slug, level, list(LEVELS),
            )
            continue

        perm = permission_string(slug, level)
        out.append(perm)
        if perm in _REGISTERED_PLUGIN_PERMISSIONS:
            continue

        # 1. Add to the live PERMISSIONS dict.
        # `PERMISSIONS` is typed as Mapping but is a plain dict at runtime.
        PERMISSIONS[perm] = (  # type: ignore[index]
            f"Per-plugin {level} access for the {slug!r} plugin (B247)."
        )

        # 2. Append to each role's frozenset that should hold this perm
        #    by default. ROLE_PERMISSIONS values are frozensets — replace
        #    them with new frozensets to keep the immutability contract.
        granted_roles = _DEFAULT_ROLE_GRANTS.get(level, frozenset())
        for role in granted_roles:
            base = ROLE_PERMISSIONS.get(role, frozenset())
            ROLE_PERMISSIONS[role] = base | {perm}  # type: ignore[index]

        # 3. Invalidate the resolve_role_permissions cache for affected
        #    roles so the new perm shows up on the next check (otherwise
        #    a request that arrives within the 30s cache TTL would see
        #    the stale frozenset). Cache invalidation is best-effort —
        #    the TTL still guarantees eventual consistency.
        try:
            from .overrides import invalidate_cache
            for role in granted_roles:
                invalidate_cache(role)
        except Exception:
            pass

        _REGISTERED_PLUGIN_PERMISSIONS.add(perm)
        logger.info(
            "[rbac] B247 registered %s (default grants: %s)",
            perm, sorted(granted_roles),
        )
    return out


def register_all_plugin_levels(slug: str) -> list[str]:
    """Convenience: register every level (read/write/configure/admin)
    for a plugin so the matrix UI shows the full set even before any
    route uses a given level.
    """
    return register_plugin_permissions(slug, LEVELS)


def registered_plugin_permissions() -> frozenset[str]:
    """Snapshot of permissions registered so far. Used by the matrix
    UI to flag rows as plugin-owned vs core."""
    return frozenset(_REGISTERED_PLUGIN_PERMISSIONS)
