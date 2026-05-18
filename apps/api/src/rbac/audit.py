"""
B227 (v0.9.8.0) — RBAC audit logger.

Writes one auth_audit row per permission decision. Fails open: a logging
error must never break a request, since we run during request handling.

Schema lives in storage/postgres/migrations/052_auth_audit.sql.
"""
import logging
import uuid
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.rbac.audit")


VALID_DECISIONS = ("allow", "deny", "shadow_mismatch")
VALID_MODES = ("shadow", "enforced")


def log_decision(
    *,
    user_id: Optional[str],
    user_role: Optional[str],
    permission: str,
    route_method: str,
    route_path: str,
    decision: str,
    mode: str,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
    acting_as_user_id: Optional[str] = None,
) -> None:
    """Insert one auth_audit row.

    Fails open — any DB error is swallowed and logged to stderr. RBAC
    decisions still happen even if the audit table is unavailable.

    `request_id` defaults to a fresh UUID if not supplied. Pass an existing
    request id from middleware (when available) to correlate multiple checks
    in the same request.

    `acting_as_user_id` (B236, v0.9.10.0): when the request was made by an
    actor impersonating another user, `user_id` is the *effective* user (the
    target whose permissions were used for the decision), and
    `acting_as_user_id` is the same target id — but `user_id` of the underlying
    session row is the actor. Most callers should set both to the effective
    user id when the session has an active impersonation; the actor is
    discoverable via the session row.
    """
    if decision not in VALID_DECISIONS:
        logger.warning("auth_audit: invalid decision %r (will be inserted anyway)", decision)
    if mode not in VALID_MODES:
        logger.warning("auth_audit: invalid mode %r (will be inserted anyway)", mode)

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO auth_audit
                (user_id, user_role, permission, route_method, route_path,
                 decision, mode, reason, request_id, acting_as_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    user_role,
                    permission,
                    route_method,
                    route_path,
                    decision,
                    mode,
                    reason,
                    request_id or str(uuid.uuid4()),
                    acting_as_user_id,
                ),
            )
    except Exception:
        # Logging shouldn't break requests. Swallow & log to stderr only.
        logger.exception("auth_audit insert failed (request continues)")
