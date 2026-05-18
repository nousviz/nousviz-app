"""B248 (v0.9.10.7): per-resource ACL DB layer.

Migration 061 created two tables:
  resource_acls          — per-(type, id) grants to roles or users
  rbac_resource_defaults — per-type allow/deny default policy

This module is the single read/write layer over both. The
`requires_resource(resource_type)` FastAPI dep in dependency.py
calls `check_resource_access` to resolve a request.

Resolution order:
  1. Owner implicit grant — resource.created_by gets read + write.
  2. Explicit user grant — resource_acls row, principal_kind='user'.
  3. Explicit role grant — resource_acls row, principal_kind='role'.
  4. Role permission — the existing rbac_role_overrides + static
     catalog (consulted via role_has_permission).
  5. Default policy — rbac_resource_defaults; seeded 'allow' on every
     known type at install (B248 doesn't change behaviour by default).

Resource-type registry: each known type registers a lookup config
(table name, id column, owner column). The resolver uses it to find
the owner for the implicit-grant rule. Unknown types fall back to no
owner check.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.rbac.resource_acls")


# ── Resource-type registry ────────────────────────────────────────────


@dataclass(frozen=True)
class ResourceTypeConfig:
    """How to find the owner of a resource of a given type.

    `table` is the SQL table to look up.
    `id_column` is the column matched against the request's resource_id.
    `owner_column` is the column carrying the user_id of the resource's
    creator. None means no owner concept (skip the implicit-grant rule).
    """
    table: str
    id_column: str
    owner_column: Optional[str]


_REGISTRY: dict[str, ResourceTypeConfig] = {
    "dashboard":  ResourceTypeConfig(table="user_dashboards", id_column="slug",  owner_column="created_by"),
    "fusion":     ResourceTypeConfig(table="fusions",         id_column="slug",  owner_column=None),
    "connection": ResourceTypeConfig(table="connections",     id_column="id",    owner_column="created_by"),
    "share":      ResourceTypeConfig(table="shared_links",    id_column="share_id", owner_column="created_by"),
    "plugin":     ResourceTypeConfig(table=None,              id_column=None,    owner_column=None),
    # ^^ plugin resources don't have a single SQL owner column —
    # the plugin's identity is the slug; per-plugin ownership is the
    # operator who installed it. Implicit-grant rule doesn't apply.
}


def known_resource_types() -> tuple[str, ...]:
    return tuple(_REGISTRY.keys())


# ── Owner lookup ──────────────────────────────────────────────────────


def _get_resource_owner(resource_type: str, resource_id: str) -> Optional[str]:
    """Return the resource's owner user_id (text) or None."""
    cfg = _REGISTRY.get(resource_type)
    if not cfg or not cfg.table or not cfg.owner_column:
        return None
    sql = f"SELECT {cfg.owner_column}::text FROM {cfg.table} WHERE {cfg.id_column} = %s"
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (resource_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        logger.exception(
            "[acls] owner lookup failed for %s/%s — falling back to no implicit grant",
            resource_type, resource_id,
        )
        return None


# ── Default-policy lookup ─────────────────────────────────────────────


def _get_default_policy(resource_type: str) -> str:
    """Return 'allow' or 'deny' for the type. Default 'allow' if the
    table is unreachable or the row is missing — fail-open keeps current
    behaviour during partial DB outages."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT policy FROM rbac_resource_defaults WHERE resource_type = %s",
                (resource_type,),
            )
            row = cur.fetchone()
            if row:
                return row[0]
    except Exception:
        logger.exception(
            "[acls] default-policy lookup failed for %s — defaulting to 'allow'",
            resource_type,
        )
    return "allow"


# ── ACL grants ────────────────────────────────────────────────────────


@dataclass
class AclGrant:
    """A single resource_acls row."""
    id: int
    resource_type: str
    resource_id: str
    principal_kind: str
    principal_id: str
    permission: str
    granted_by: Optional[str]
    note: Optional[str]
    created_at: Optional[str]


def list_grants(resource_type: str, resource_id: str) -> list[AclGrant]:
    """Return all grants on a resource (newest first)."""
    sql = """
        SELECT id, resource_type, resource_id, principal_kind::text,
               principal_id, permission, granted_by, note, created_at::text
        FROM resource_acls
        WHERE resource_type = %s AND resource_id = %s
        ORDER BY created_at DESC, id DESC
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (resource_type, resource_id))
            return [
                AclGrant(
                    id=r[0], resource_type=r[1], resource_id=r[2],
                    principal_kind=r[3], principal_id=r[4],
                    permission=r[5], granted_by=r[6], note=r[7],
                    created_at=r[8],
                )
                for r in cur.fetchall()
            ]
    except Exception:
        logger.exception("[acls] list_grants failed for %s/%s", resource_type, resource_id)
        return []


def grant(
    *,
    resource_type: str,
    resource_id: str,
    principal_kind: str,
    principal_id: str,
    permission: str,
    granted_by: Optional[str] = None,
    note: Optional[str] = None,
) -> Optional[int]:
    """Insert a grant row. Returns the new row's id, or the existing
    row's id if a duplicate was attempted (UNIQUE conflict)."""
    if principal_kind not in ("role", "user"):
        raise ValueError(f"principal_kind must be 'role' or 'user', got {principal_kind!r}")
    sql = """
        INSERT INTO resource_acls
          (resource_type, resource_id, principal_kind, principal_id,
           permission, granted_by, note)
        VALUES (%s, %s, %s::resource_principal_kind, %s, %s, %s, %s)
        ON CONFLICT (resource_type, resource_id, principal_kind, principal_id, permission)
        DO UPDATE SET note = EXCLUDED.note, granted_by = EXCLUDED.granted_by
        RETURNING id
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (
                resource_type, resource_id, principal_kind, principal_id,
                permission, granted_by, note,
            ))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        logger.exception("[acls] grant failed")
        return None


def revoke(grant_id: int) -> bool:
    """Delete a grant by id. Returns True iff a row was removed."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM resource_acls WHERE id = %s", (grant_id,))
            return cur.rowcount > 0
    except Exception:
        logger.exception("[acls] revoke %s failed", grant_id)
        return False


# ── Access check ──────────────────────────────────────────────────────


def check_resource_access(
    user: dict,
    permission: str,
    resource_type: str,
    resource_id: str,
) -> bool:
    """Resolve whether `user` may exercise `permission` on (type, id).

    See module docstring for the resolution order.
    """
    if not user:
        return False

    user_id = user.get("id")
    role = user.get("role") or ""

    # 1. Owner implicit grant — read + write only.
    if user_id and permission in ("dashboards.read", "dashboards.write",
                                  "fusions.read", "fusions.write",
                                  "connections.read", "connections.write",
                                  "shares.read", "shares.write",
                                  "notes.read", "notes.write",
                                  "annotations.read", "annotations.write"):
        owner = _get_resource_owner(resource_type, resource_id)
        if owner and str(owner) == str(user_id):
            return True

    # 2. Explicit user grant.
    if user_id and _has_acl_row(resource_type, resource_id, "user", str(user_id), permission):
        return True

    # 3. Explicit role grant.
    if role and _has_acl_row(resource_type, resource_id, "role", role, permission):
        return True

    # 4. Role permission (existing rbac_role_overrides + static catalog).
    #    Late import to avoid the circular dep with permissions.py.
    from .permissions import role_has_permission
    if role and role_has_permission(role, permission):
        # Role permission grants access when the type's default policy is
        # 'allow'. Under 'deny', the role permission alone is not enough —
        # the user/role needs an explicit grant.
        if _get_default_policy(resource_type) == "allow":
            return True

    # 5. Default-deny — already handled above by short-circuiting; if
    #    we got here, no rule granted access.
    return False


def _has_acl_row(
    resource_type: str,
    resource_id: str,
    principal_kind: str,
    principal_id: str,
    permission: str,
) -> bool:
    """True iff a matching resource_acls row exists."""
    sql = """
        SELECT 1 FROM resource_acls
        WHERE resource_type = %s
          AND resource_id   = %s
          AND principal_kind = %s::resource_principal_kind
          AND principal_id  = %s
          AND permission    = %s
        LIMIT 1
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (resource_type, resource_id, principal_kind, principal_id, permission))
            return cur.fetchone() is not None
    except Exception:
        logger.exception("[acls] _has_acl_row failed")
        return False


# ── Default-policy admin ──────────────────────────────────────────────


def get_default_policy(resource_type: str) -> str:
    """Public read of the per-type default. Returns 'allow' on missing
    config (matches the safe-default in _get_default_policy)."""
    return _get_default_policy(resource_type)


def set_default_policy(resource_type: str, policy: str, updated_by: Optional[str] = None) -> bool:
    """Set the per-type default. Returns True on success."""
    if policy not in ("allow", "deny"):
        raise ValueError(f"policy must be 'allow' or 'deny', got {policy!r}")
    if resource_type not in _REGISTRY:
        raise ValueError(
            f"unknown resource_type {resource_type!r}; expected one of {list(_REGISTRY.keys())}"
        )
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO rbac_resource_defaults (resource_type, policy, updated_by, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (resource_type)
                DO UPDATE SET policy = EXCLUDED.policy, updated_by = EXCLUDED.updated_by, updated_at = now()
                """,
                (resource_type, policy, updated_by),
            )
            return True
    except Exception:
        logger.exception("[acls] set_default_policy failed")
        return False
