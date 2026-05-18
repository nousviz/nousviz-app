"""B305 (v0.10.0.6) — per-user plugin visibility filter.

Consumes existing `resource_acls` rows (B248, v0.9.10.7). A viewer or
analyst with one or more rows for
`(resource_type='plugin', principal_kind='user', principal_id=<user>)`
sees only those slugs in `/api/plugins`. Admin/superadmin always
unrestricted. Utility plugins always pass through (operators don't
manage infrastructure visibility per user).

Behind a feature flag `NOUSVIZ_PER_USER_PLUGIN_FILTER` (default 'true')
so a misbehaving filter can be reverted by one env var + PM2 reload
without removing the consuming code.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable, Optional

from fastapi import HTTPException, Request

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.rbac.plugin_visibility")


UNRESTRICTED_ROLES: frozenset[str] = frozenset({"admin", "superadmin"})


def is_per_user_filter_enabled() -> bool:
    """Read the runtime feature flag. Default ON.

    Rollback path: `NOUSVIZ_PER_USER_PLUGIN_FILTER=false` + PM2 reload
    reverts `/api/plugins` to its pre-B305 behaviour (full list to
    every authenticated user). ACL rows in the table remain harmless
    without the consuming code.
    """
    raw = os.environ.get("NOUSVIZ_PER_USER_PLUGIN_FILTER", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def allowed_plugin_slugs_for_user(user_id: str, role: str) -> Optional[set[str]]:
    """Return the set of plugin slugs the user is explicitly allowed to
    see, or None if the user is unrestricted (admin/superadmin, or no
    ACL rows for the plugin type).

    Semantics:
      - role ∈ UNRESTRICTED_ROLES → None (filter does not apply).
      - zero rows → None (unrestricted, matches pre-B305 behaviour).
      - one or more rows → set of slugs from `resource_id`.
    """
    if (role or "").lower() in UNRESTRICTED_ROLES:
        return None
    if not user_id:
        return None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT resource_id
                FROM resource_acls
                WHERE resource_type = 'plugin'
                  AND principal_kind = 'user'
                  AND principal_id = %s
                """,
                (str(user_id),),
            )
            rows = cur.fetchall()
    except Exception:
        logger.exception(
            "[plugin_visibility] ACL lookup failed for user=%s — failing open",
            user_id,
        )
        return None
    if not rows:
        return None
    return {row[0] for row in rows}


def user_can_access_plugin(
    user_id: Optional[str],
    role: Optional[str],
    plugin_slug: Optional[str],
) -> bool:
    """B305.1 (v0.10.0.6.1) — truth function for data-access surfaces.

    Returns True when the user is allowed to see / query the given
    plugin's resources. Composition:
      - feature flag OFF   → True (rollback parity with B305 filter)
      - admin / superadmin → True (always unrestricted)
      - no plugin_slug     → True (defensive — caller didn't name a plugin,
                              presumably a core-table operation governed
                              by other rules)
      - allowlist=None     → True (zero ACL rows = unrestricted)
      - allowlist=set      → plugin_slug in the set

    Used by:
      - the FastAPI dep `requires_plugin_access` for `/api/catalog/plugins/{slug}/*`
        and `/api/datasets/{slug}` routes.
      - the SQL table-ref check in `/api/query`.
    """
    if not is_per_user_filter_enabled():
        return True
    if (role or "").lower() in UNRESTRICTED_ROLES:
        return True
    if not plugin_slug:
        return True
    allowed = allowed_plugin_slugs_for_user(str(user_id or ""), role or "")
    if allowed is None:
        return True
    return plugin_slug in allowed


def requires_plugin_access(plugin_id_param: str = "plugin_id"):
    """FastAPI dep factory: 404s when the current user can't access the
    plugin named in the path. The 404 (not 403) mirrors B248 ACL
    semantics — don't leak presence of plugins the user shouldn't see.

    Usage:
        @router.get("/plugins/{plugin_id}/...")
        async def handler(
            plugin_id: str,
            _gate: None = Depends(requires_plugin_access()),
        ): ...

    The dep reads `plugin_id` from the request path (configurable via
    `plugin_id_param`) and the current user via `get_me(request)`. Runs
    AFTER the existing `requires(...)` permission dep (FastAPI runs
    deps in declaration order).
    """
    def _dep(request: Request) -> None:
        plugin_slug = request.path_params.get(plugin_id_param)
        if not plugin_slug:
            return  # Path didn't carry the param; nothing to gate on.
        # Late import to avoid a circular dep — routes.auth imports rbac.
        from ..routes.auth import get_me

        try:
            user = get_me(request)
        except HTTPException:
            # Auth layer will already have rejected this; defensive only.
            raise
        if not user_can_access_plugin(user.get("id"), user.get("role"), plugin_slug):
            raise HTTPException(404, "Not found")

    return _dep


def filter_plugins_for_user(plugins: list[dict], user: dict) -> list[dict]:
    """Apply the per-user plugin allowlist to a list of plugin entries.

    A plugin entry passes when ANY of:
      - the feature flag is OFF (rollback-safe)
      - the user is admin/superadmin
      - the user has no ACL rows for the plugin type
      - the plugin is a utility (entry["type"] == "utility")
      - the plugin's slug is in the user's allowlist
    """
    if not is_per_user_filter_enabled():
        return plugins
    user_id = user.get("id") if user else None
    user_role = user.get("role") if user else None
    allowed = allowed_plugin_slugs_for_user(str(user_id) if user_id else "", user_role or "")
    if allowed is None:
        return plugins
    out: list[dict] = []
    for entry in plugins:
        if entry.get("type") == "utility":
            out.append(entry)
            continue
        if entry.get("id") in allowed:
            out.append(entry)
    return out


def users_with_restricted_access_excluding(slug: str) -> list[dict]:
    """Return users whose plugin allowlist is non-empty AND does not
    already contain `slug`. Used by the install-success grant banner.

    Each row: {user_id, email, role}. Admins/superadmins are never
    returned (they bypass the filter by role anyway).
    """
    if not slug:
        return []
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT u.id::text, u.email, u.role
                FROM users u
                WHERE u.is_active = true
                  AND u.role NOT IN ('admin', 'superadmin')
                  AND EXISTS (
                      SELECT 1 FROM resource_acls a
                      WHERE a.resource_type = 'plugin'
                        AND a.principal_kind = 'user'
                        AND a.principal_id = u.id::text
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM resource_acls a
                      WHERE a.resource_type = 'plugin'
                        AND a.principal_kind = 'user'
                        AND a.principal_id = u.id::text
                        AND a.resource_id = %s
                  )
                ORDER BY u.email
                """,
                (slug,),
            )
            return [
                {"user_id": row[0], "email": row[1], "role": row[2]}
                for row in cur.fetchall()
            ]
    except Exception:
        logger.exception(
            "[plugin_visibility] users_with_restricted_access_excluding(%s) failed",
            slug,
        )
        return []


# ── Read / write the per-user allowlist ────────────────────────────────


def get_user_plugin_access(user_id: str) -> dict:
    """Return `{ "mode": "all" | "specific", "plugin_ids": [...] }` for
    the user. `mode='all'` ⇔ zero rows; `mode='specific'` ⇔ ≥1 row.
    """
    if not user_id:
        return {"mode": "all", "plugin_ids": []}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT resource_id
                FROM resource_acls
                WHERE resource_type = 'plugin'
                  AND principal_kind = 'user'
                  AND principal_id = %s
                ORDER BY resource_id
                """,
                (str(user_id),),
            )
            slugs = [row[0] for row in cur.fetchall()]
    except Exception:
        logger.exception(
            "[plugin_visibility] get_user_plugin_access(%s) failed", user_id
        )
        return {"mode": "all", "plugin_ids": []}
    if not slugs:
        return {"mode": "all", "plugin_ids": []}
    return {"mode": "specific", "plugin_ids": slugs}


def apply_plugin_access_with_cursor(
    cur,
    user_id: str,
    mode: str,
    plugin_ids: Iterable[str],
    *,
    actor_user_id: Optional[str],
    actor_role: Optional[str] = None,
    note: Optional[str] = None,
) -> tuple[set[str], set[str]]:
    """Apply the allowlist using the caller's cursor (single transaction).

    Returns (added_slugs, removed_slugs). Writes one rbac_config_audit
    row per change via `log_config_change` so the audit and the data
    move together.

    Used by:
      - PUT /api/auth/users/{id}/plugin-access (this module's
        set_user_plugin_access wrapper opens the conn).
      - The invite-acceptance path in routes/auth.py, where the user
        insert + ACL writes share the same transaction.
    """
    if mode not in {"all", "specific"}:
        raise ValueError(f"invalid mode: {mode!r}")
    target_set: set[str] = set()
    if mode == "specific":
        target_set = {str(s).strip() for s in plugin_ids if str(s).strip()}

    cur.execute(
        """
        SELECT resource_id
        FROM resource_acls
        WHERE resource_type = 'plugin'
          AND principal_kind = 'user'
          AND principal_id = %s
        """,
        (str(user_id),),
    )
    current = {row[0] for row in cur.fetchall()}
    to_remove = current - target_set
    to_add = target_set - current
    from .config_audit import log_config_change

    for slug in sorted(to_remove):
        cur.execute(
            """
            DELETE FROM resource_acls
            WHERE resource_type = 'plugin'
              AND principal_kind = 'user'
              AND principal_id = %s
              AND resource_id = %s
            """,
            (str(user_id), slug),
        )
        log_config_change(
            cur,
            action="acl_revoke",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            target_resource_type="plugin",
            target_resource_id=slug,
            before_state={
                "principal_kind": "user",
                "principal_id": str(user_id),
                "permission": "plugins.read",
            },
            after_state=None,
            note=note or "B305 per-user plugin allowlist",
        )
    for slug in sorted(to_add):
        cur.execute(
            """
            INSERT INTO resource_acls
                (resource_type, resource_id, principal_kind, principal_id,
                 permission, granted_by, note)
            VALUES ('plugin', %s, 'user', %s, 'plugins.read', %s, %s)
            ON CONFLICT (resource_type, resource_id, principal_kind,
                         principal_id, permission)
            DO NOTHING
            """,
            (slug, str(user_id), actor_user_id, note or "B305 per-user plugin allowlist"),
        )
        log_config_change(
            cur,
            action="acl_grant",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            target_resource_type="plugin",
            target_resource_id=slug,
            before_state=None,
            after_state={
                "principal_kind": "user",
                "principal_id": str(user_id),
                "permission": "plugins.read",
            },
            note=note or "B305 per-user plugin allowlist",
        )
    return to_add, to_remove


def set_user_plugin_access(
    user_id: str,
    mode: str,
    plugin_ids: Iterable[str],
    actor_user_id: Optional[str],
    actor_role: Optional[str] = None,
) -> dict:
    """Open-conn convenience wrapper around apply_plugin_access_with_cursor.

    Opens one transaction, applies the diff, commits. Returns the
    post-write state in the same shape as get_user_plugin_access.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()
        apply_plugin_access_with_cursor(
            cur,
            user_id,
            mode,
            plugin_ids,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
        conn.commit()
    return get_user_plugin_access(user_id)
