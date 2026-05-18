"""
B232 (v0.9.9.0) — RBAC override resolution.

Layers operator-controlled deltas (rbac_role_overrides table) on top of
the static catalog (ROLE_PERMISSIONS in permissions.py).

resolve_role_permissions(role) returns the post-override permission set.
Cached per-role with a 30s TTL; invalidate_cache(role) clears the cache
for one role (called from B233's write endpoints).

Fail-open path: if the DB query errors, we return the static-default
set. RBAC reads must never crash the request — better to fall back to
code defaults than 500.
"""
import logging
import time
from typing import FrozenSet

from ..db import get_pg_conn
from . import permissions as _perms

logger = logging.getLogger("nousviz.rbac.overrides")

# role -> (resolved_set, expires_at_unix_seconds)
_CACHE: dict[str, tuple[FrozenSet[str], float]] = {}
_CACHE_TTL_SEC = 30


def resolve_role_permissions(role: str) -> FrozenSet[str]:
    """Return the post-override permission set for `role`.

    Algorithm:
      1. Start with the static catalog default for the role.
      2. Add any 'grant' overrides.
      3. Subtract any 'revoke' overrides.

    Empty result for unknown roles. Cached for _CACHE_TTL_SEC seconds.
    Fails open: DB errors return the static default.
    """
    if not role:
        return frozenset()

    now = time.time()
    cached = _CACHE.get(role)
    if cached is not None and cached[1] > now:
        return cached[0]

    default = set(_perms.ROLE_PERMISSIONS.get(role, frozenset()))

    grants: set[str] = set()
    revokes: set[str] = set()

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT permission, kind FROM rbac_role_overrides WHERE role = %s",
                (role,),
            )
            for permission, kind in cur.fetchall():
                if kind == "grant":
                    grants.add(permission)
                elif kind == "revoke":
                    revokes.add(permission)
    except Exception:
        # Fail-open: code defaults still apply if the DB is unreachable
        # or if the table doesn't exist yet (pre-migration).
        logger.exception(
            "[rbac] override query failed for role=%r; falling back to defaults",
            role,
        )
        # Cache the default briefly so we don't hammer the DB during an
        # outage. Shorter TTL (5s) so recovery is quick.
        resolved = frozenset(default)
        _CACHE[role] = (resolved, now + 5)
        return resolved

    resolved = frozenset((default | grants) - revokes)
    _CACHE[role] = (resolved, now + _CACHE_TTL_SEC)
    return resolved


def get_overrides_for_role(role: str) -> dict[str, list[str]]:
    """Return the raw override rows for one role, for the matrix UI to
    render 'modified from default' badges. Not cached — called once per
    matrix load.

    Shape: {grants: [permission, ...], revokes: [permission, ...]}
    Sorted by permission for stable rendering.
    Empty lists when no overrides exist or on DB error.
    """
    grants: list[str] = []
    revokes: list[str] = []
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT permission, kind FROM rbac_role_overrides "
                "WHERE role = %s ORDER BY permission",
                (role,),
            )
            for permission, kind in cur.fetchall():
                if kind == "grant":
                    grants.append(permission)
                elif kind == "revoke":
                    revokes.append(permission)
    except Exception:
        logger.exception("[rbac] get_overrides_for_role failed for role=%r", role)
    return {"grants": grants, "revokes": revokes}


def invalidate_cache(role: str) -> None:
    """Clear cached resolution for one role. Called by B233's write
    endpoints after committing an override change so operators see
    their edits reflected immediately rather than at next TTL expiry."""
    _CACHE.pop(role, None)


def invalidate_all_caches() -> None:
    """Clear all cached resolutions. Useful in tests, after bulk
    operations like custom-role create/delete (B233), and when an
    operator imports a saved RBAC config snapshot."""
    _CACHE.clear()
