"""
B234 (v0.9.9.2) — RBAC config audit logger.

Distinct from `audit.py` (which logs permission DECISIONS at request
time). This module logs RBAC POLICY MUTATIONS — every grant, revoke,
clear, custom-role create, custom-role delete that flows through the
/api/system/role-overrides and /api/system/custom-roles endpoints.

Fail-closed: caller passes the cursor from their existing transaction.
If the audit insert fails, the caller's transaction rolls back and the
underlying data write doesn't commit either. RBAC config compliance
scenarios require guaranteed audit trail — losing audit means losing
the operation.

Schema lives in storage/postgres/migrations/055_rbac_config_audit.sql.
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger("nousviz.rbac.config_audit")


VALID_ACTIONS = (
    "grant", "revoke", "clear", "create_role", "delete_role",
    "impersonate_start", "impersonate_end",  # B236 (v0.9.10.0)
    "password_reset_cli",                    # B251 (v0.9.10.0.3): scripts/reset-password.sh
    "password_reset_request",                # B251: POST /api/auth/forgot-password
    "password_reset_completed",              # B251: POST /api/auth/reset-password
    "password_change_self",                  # B251: PATCH /api/auth/me with password
    "acl_grant",                             # B248 (v0.9.10.7): per-resource ACL grant
    "acl_revoke",                            # B248: per-resource ACL revoke
    "set_default_policy",                    # B248: per-type default policy update
)


def log_config_change(
    cur,
    *,
    action: str,
    target_role: Optional[str] = None,
    actor_user_id: Optional[str],
    actor_role: Optional[str] = None,
    target_permission: Optional[str] = None,
    target_resource_type: Optional[str] = None,
    target_resource_id: Optional[str] = None,
    before_state: Optional[dict[str, Any]] = None,
    after_state: Optional[dict[str, Any]] = None,
    note: Optional[str] = None,
) -> None:
    """Insert one rbac_config_audit row using `cur` (caller's cursor).

    Caller is responsible for transaction management — this function
    does NOT commit. If the insert raises, caller's transaction
    aborts and the calling endpoint should propagate the error.

    Action shape contract:
      grant  / revoke / clear  → target_permission required;
                                 before_state = prior override row (or null);
                                 after_state  = new override row (or null on clear)
      create_role              → target_permission null;
                                 before_state null;
                                 after_state = {display_name, description, based_on, seed_permissions}
      delete_role              → target_permission null;
                                 before_state = {display_name, description, based_on, permissions:[...]};
                                 after_state null
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Invalid RBAC config audit action: {action!r}")

    cur.execute(
        """
        INSERT INTO rbac_config_audit
        (actor_user_id, actor_role, action, target_role, target_permission,
         target_resource_type, target_resource_id,
         before_state, after_state, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
        """,
        (
            actor_user_id,
            actor_role,
            action,
            target_role,
            target_permission,
            target_resource_type,
            target_resource_id,
            json.dumps(before_state) if before_state is not None else None,
            json.dumps(after_state) if after_state is not None else None,
            note,
        ),
    )
