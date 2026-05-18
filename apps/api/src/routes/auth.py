"""
Authentication & User Management.

Multi-user accounts with per-user sessions, bcrypt passwords, invite flow.

Auth methods:
1. Email + password → session token
2. API key → X-API-Key header, hashed lookup

Roles: superadmin | admin | analyst | viewer | custom
"""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn, dict_cursor
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail, StepUpRequiredDetail
from ..models.auth import (
    ApiKeyCreateResponse,
    AuthActivityResponse,
    AuthStatusResponse,
    AvatarResponse,
    DeactivateUserResponse,
    GenericMessageResponse,
    ImpersonateExitResponse,
    ImpersonateStartResponse,
    InviteCreateResponse,
    InviteRevokeResponse,
    InvitesListResponse,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    MyPermissionsResponse,
    PluginAccessResponse,
    RestrictedUsersListResponse,
    RolePermissionsResponse,
    SetupOkResponse,
    SetupResponse,
    StepUpResponse,
    UserSerialized,
    UsersListResponse,
    VerifyResponse,
)

logger = logging.getLogger("nousviz.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

# B227 + B228: register all auth.py routes.
# /me/* uses users.read_self (everyone+). User-management uses users.manage
# or users.manage_admins. Public flow (login/register/etc) is in
# PUBLIC_ROUTES, NOT registered here.
register_route("GET", "/api/auth/me", "users.read_self")
register_route("GET", "/api/auth/me/permissions", "users.read_self")
register_route("POST", "/api/auth/step-up", "users.read_self")  # B236
register_route("POST", "/api/auth/impersonate/{user_id}", "users.manage")  # B236 — rank check inside
register_route("POST", "/api/auth/impersonate/exit", "users.read_self")  # B236 — anyone in an impersonated session can exit
register_route("GET", "/api/auth/role-permissions/{role}", "system.audit")
register_route("PATCH", "/api/auth/me", "users.read_self")
register_route("POST", "/api/auth/me/avatar", "users.read_self")
register_route("DELETE", "/api/auth/me/avatar", "users.read_self")
register_route("GET", "/api/auth/users", "users.manage")
register_route("PATCH", "/api/auth/users/{user_id}", "users.manage")
register_route("DELETE", "/api/auth/users/{user_id}", "users.manage")
register_route("POST", "/api/auth/users/{user_id}/reactivate", "users.manage")
register_route("POST", "/api/auth/users/{user_id}/promote", "users.manage_admins")
register_route("POST", "/api/auth/users/{user_id}/demote", "users.manage_admins")
register_route("POST", "/api/auth/users/invite", "users.manage")
register_route("GET", "/api/auth/users/invites", "users.manage")
register_route("DELETE", "/api/auth/users/invite/{invite_id}", "users.manage")
register_route("POST", "/api/auth/users/{user_id}/api-key", "users.manage")
register_route("GET", "/api/auth/activity", "system.audit")
# B305 (v0.10.0.6) — per-user plugin allowlist.
register_route("GET", "/api/auth/users/with-restricted-plugin-access", "users.manage")
register_route("GET", "/api/auth/users/{user_id}/plugin-access", "users.manage")
register_route("PUT", "/api/auth/users/{user_id}/plugin-access", "users.manage")


def _serialize(row):
    if not row:
        return row
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    d.pop("password_hash", None)
    if d.get("api_key"):
        d["api_key"] = d["api_key"][:8] + "..."
    return d


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()


def _check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def _create_session(user_id: str, request: Request) -> tuple[str, datetime]:
    """Create a session token, store the SHA-256 hash, return (raw_token, expires_at)."""
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    ttl_days = int(os.environ.get("NOUSVIZ_SESSION_TTL_DAYS", "30"))
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else None)
    ua = (request.headers.get("user-agent") or "")[:256]

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)",
            (user_id, token_hash, expires_at, ip, ua),
        )
    return raw, expires_at


def _get_session_row(request: Request) -> Optional[dict]:
    """B236 (v0.9.10.0): look up the active session row for the request.

    Returns dict with user_id, acting_as_user_id, step_up_until — or None if
    no valid session token. Used by step-up, impersonation, and (when session
    introspection is needed beyond what get_me provides) other handlers.
    """
    token = request.headers.get("X-Session-Token")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute(
                """
                SELECT user_id, acting_as_user_id, step_up_until, expires_at
                FROM user_sessions
                WHERE token_hash = %s AND expires_at > now()
                """,
                (token_hash,),
            )
            return cur.fetchone()
    except Exception:
        import logging as _logging
        _logging.getLogger("nousviz.auth").exception("session row lookup failed")
        return None


def _users_exist() -> bool:
    """Returns True if any real (non-synthetic admin@local) user exists."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM users WHERE email != 'admin@local' AND is_active = true")
            return cur.fetchone()[0] > 0
    except Exception:
        return False


# ── Login rate limiting ───────────────────────────────────────────────────

from ..rate_limit import RateLimiter
_login_limiter = RateLimiter(max_attempts=5, window_sec=60, max_keys=1000)


def _check_login_rate(ip: str) -> bool:
    return _login_limiter.is_limited(ip)


# ── Auth status ──────────────────────────────────────────────────────────

@router.get(
    "/status",
    operation_id="auth.status",
    response_model=AuthStatusResponse,
    response_model_exclude_none=True,
    summary="Auth-mode and current-session status",
)
def auth_status(request: Request):
    """Return auth-mode flags and (if a session token is present and
    valid) the authenticated user.

    Public endpoint — no auth required. The frontend calls this on
    page load to decide whether to show the login screen, the setup
    wizard (no users exist), or the dashboard.
    """
    auth_required = os.environ.get("AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
    users_exist = _users_exist()

    user = None
    token = request.headers.get("X-Session-Token")
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            with get_pg_conn() as conn:
                cur = dict_cursor(conn)
                cur.execute("""
                    SELECT u.* FROM users u
                    JOIN user_sessions s ON s.user_id = u.id
                    WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active = true
                """, (token_hash,))
                row = cur.fetchone()
                if row:
                    user = _serialize(row)
        except Exception:
            pass

    return {
        "authenticated": user is not None,
        "auth_required": auth_required,
        "users_exist": users_exist,
        "user": user,
    }


# ── Register (first user = superadmin, or via invite) ────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    invite_token: Optional[str] = None


@router.post(
    "/register",
    operation_id="auth.register",
    response_model=LoginResponse,
    response_model_exclude_none=True,
    summary="Register a new account (first user = superadmin; later users via invite)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid password or email/invite mismatch."},
        403: {"model": ErrorDetail, "description": "Registration requires an invite."},
        409: {"model": ErrorDetail, "description": "Email already exists."},
        410: {"model": ErrorDetail, "description": "Invite invalid or expired."},
    },
)
def register(req: RegisterRequest, request: Request):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    users_exist = _users_exist()

    if users_exist and not req.invite_token:
        raise HTTPException(403, "Registration requires an invite. Ask an admin to invite you.")

    role = "superadmin"  # first user
    invite_id = None

    if users_exist and req.invite_token:
        # Validate invite
        token_hash = hashlib.sha256(req.invite_token.encode()).hexdigest()
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute("""
                SELECT * FROM user_invites
                WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
            """, (token_hash,))
            invite = cur.fetchone()
            if not invite:
                raise HTTPException(410, "This invitation is invalid or has expired. Ask an admin to re-send.")
            if invite["email"].lower() != req.email.lower():
                raise HTTPException(400, "Email doesn't match the invitation.")
            role = invite["role"]
            invite_id = invite["id"]

    # Check email not taken
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT id FROM users WHERE email = %s", (req.email.lower(),))
        if cur.fetchone():
            raise HTTPException(409, "A user with this email already exists.")

    pw_hash = _hash_password(req.password)

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            INSERT INTO users (email, name, role, auth_method, password_hash, last_login, login_count)
            VALUES (%s, %s, %s, 'password', %s, now(), 1)
            RETURNING *
        """, (req.email.lower(), req.name, role, pw_hash))
        user = _serialize(cur.fetchone())

        if invite_id:
            cur.execute("UPDATE user_invites SET used_at = now() WHERE id = %s", (invite_id,))
            # B305: if the invite carried a plugin_access_pending payload,
            # apply it in the same transaction as user creation. invite
            # was fetched above with all columns; re-read for the JSONB
            # field to keep the structure local.
            cur.execute(
                "SELECT plugin_access_pending FROM user_invites WHERE id = %s",
                (invite_id,),
            )
            pending_row = cur.fetchone()
            pending = pending_row["plugin_access_pending"] if pending_row else None
            if (
                pending
                and isinstance(pending, dict)
                and pending.get("mode") == "specific"
                and role not in ("admin", "superadmin")
            ):
                from ..rbac import apply_plugin_access_with_cursor

                apply_plugin_access_with_cursor(
                    cur,
                    str(user["id"]),
                    "specific",
                    pending.get("plugin_ids") or [],
                    actor_user_id=None,  # invite-acceptance is self-service; no actor
                    actor_role=None,
                    note="B305 invite-acceptance allowlist",
                )

    # Create session
    raw_token, expires_at = _create_session(user["id"], request)

    from .activity import record_activity
    record_activity(action="user_register", detail={"email": user["email"], "role": role})

    return {"token": raw_token, "expires_at": expires_at.isoformat(), "user": user}


# ── Login ────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post(
    "/login",
    operation_id="auth.login",
    response_model=LoginResponse,
    response_model_exclude_none=True,
    summary="Issue a session token for valid credentials",
    responses={
        400: {"model": ErrorDetail, "description": "Email is required."},
        401: {"model": ErrorDetail, "description": "Invalid email or password."},
        429: {"model": ErrorDetail, "description": "Rate-limited — too many login attempts."},
    },
)
def login(req: LoginRequest, request: Request):
    """Authenticate and return a session token. Rate-limited per source IP."""
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if _check_login_rate(client_ip):
        raise HTTPException(429, "Too many login attempts. Try again in 60 seconds.")

    if not req.email:
        raise HTTPException(400, "Email is required.")

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE email = %s AND is_active = true", (req.email.lower(),))
        user = cur.fetchone()

    if not user or not user.get("password_hash"):
        raise HTTPException(401, "Invalid email or password.")
    if not _check_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET last_login = now(), login_count = login_count + 1 WHERE id = %s", (user["id"],))

    raw_token, expires_at = _create_session(str(user["id"]), request)
    return {"token": raw_token, "expires_at": expires_at.isoformat(), "user": _serialize(user)}


# ── Accept invite (alternative to register — for link-click flow) ────────

class AcceptInviteRequest(BaseModel):
    invite_token: str
    password: str
    name: Optional[str] = None


@router.post(
    "/accept-invite",
    operation_id="auth.accept_invite",
    response_model=LoginResponse,
    response_model_exclude_none=True,
    summary="Accept an invite link and create the account",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid password or email mismatch."},
        409: {"model": ErrorDetail, "description": "Email already exists — try logging in."},
        410: {"model": ErrorDetail, "description": "Invite invalid or expired."},
    },
)
def accept_invite(req: AcceptInviteRequest, request: Request):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    token_hash = hashlib.sha256(req.invite_token.encode()).hexdigest()

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT * FROM user_invites
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
        """, (token_hash,))
        invite = cur.fetchone()

    if not invite:
        raise HTTPException(410, "This invitation is invalid or has expired. Ask an admin to re-send.")

    # Check email not already registered
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (invite["email"].lower(),))
        if cur.fetchone():
            raise HTTPException(409, "A user with this email already exists. Try logging in instead.")

    pw_hash = _hash_password(req.password)

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            INSERT INTO users (email, name, role, auth_method, password_hash, last_login, login_count)
            VALUES (%s, %s, %s, 'password', %s, now(), 1)
            RETURNING *
        """, (invite["email"].lower(), req.name or invite["email"].split("@")[0], invite["role"], pw_hash))
        user = _serialize(cur.fetchone())
        cur.execute("UPDATE user_invites SET used_at = now() WHERE id = %s", (invite["id"],))
        # B305: apply invite-time plugin allowlist if present.
        pending = invite.get("plugin_access_pending")
        if (
            pending
            and isinstance(pending, dict)
            and pending.get("mode") == "specific"
            and invite["role"] not in ("admin", "superadmin")
        ):
            from ..rbac import apply_plugin_access_with_cursor

            apply_plugin_access_with_cursor(
                cur,
                str(user["id"]),
                "specific",
                pending.get("plugin_ids") or [],
                actor_user_id=None,
                actor_role=None,
                note="B305 invite-acceptance allowlist",
            )

    raw_token, expires_at = _create_session(user["id"], request)

    from .activity import record_activity
    record_activity(action="user_register", detail={"email": user["email"], "role": invite["role"], "via": "invite"})

    return {"token": raw_token, "expires_at": expires_at.isoformat(), "user": user}


# ── Forgot / Reset password (B251, v0.9.10.0.3) ─────────────────────────
#
# Two public endpoints (auth-middleware-bypassed via PUBLIC_PREFIXES):
#
#   POST /api/auth/forgot-password { email }
#       Always returns 200 with the same generic message regardless of
#       whether the email exists. If found and active, generates a
#       SHA-256-hashed token (raw token in email link), stores in
#       password_reset_tokens with 1h TTL, sends email via SMTP.
#       Rate-limited per email at 3 requests / 60min.
#
#   POST /api/auth/reset-password { token, password }
#       Validates token (exists / not expired / not used). Hashes the
#       new password (bcrypt rounds=12), updates users.password_hash,
#       marks the token used, kills all active sessions for the user
#       (security: a hijacker can't keep using a stolen session after
#       the legitimate owner resets).
#
# Both write rbac_config_audit rows. The CLI recovery path
# (scripts/reset-password.sh, also B251) writes its own
# action='password_reset_cli' row.

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# Rate limiter: 3 attempts per email per 60 minutes. Separate bucket
# from login (per-IP) so flooding forgot-password doesn't lock out
# normal logins.
_forgot_password_limiter = RateLimiter(max_attempts=3, window_sec=3600, max_keys=10000)


def _send_password_reset_email_safely(to_email: str, reset_url: str) -> None:
    """Wrapper around services.email.send_password_reset_email. Logs
    on failure but never raises — the forgot-password endpoint must not
    leak whether the email succeeded (operator email infra issues
    shouldn't enable enumeration attacks)."""
    try:
        from ..services.email import send_password_reset_email
        ok, detail = send_password_reset_email(to_email, reset_url)
        if not ok:
            logger.warning(f"forgot-password: email send failed: {detail}")
    except Exception:
        logger.exception("forgot-password: email send raised")


@router.post(
    "/forgot-password",
    operation_id="auth.forgot_password",
    response_model=GenericMessageResponse,
    summary="Initiate password reset (enumeration-resistant)",
    responses={
        429: {"model": ErrorDetail, "description": "Rate-limited — too many resets for this email."},
    },
)
def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Public endpoint — initiate a password reset.

    Always returns 200 with the same body regardless of whether the
    email exists, matches a real user, or the email send actually
    succeeded. This prevents user-enumeration via response timing or
    response shape.
    """
    email = (req.email or "").strip().lower()
    if not email or "@" not in email:
        # Don't even hit the rate limiter for obviously bogus input —
        # but still return the generic 200 to keep the response shape
        # stable for enumeration resistance.
        return {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}

    # Rate limit per email (lowercased so case variants share a bucket).
    if _forgot_password_limiter.is_limited(email):
        raise HTTPException(429, "Too many reset requests for this email. Try again later.")

    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )

    # Look up user. If not found or inactive, silently no-op.
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT id, email FROM users WHERE email = %s AND is_active = true",
            (email,),
        )
        user_row = cur.fetchone()

    if not user_row:
        # Silent no-op: same response, no token, no email.
        return {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}

    user_id = str(user_row["id"])

    # Generate raw token (sent in email) + hash (stored).
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO password_reset_tokens
                  (user_id, token_hash, expires_at, requested_ip)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, token_hash, expires_at, client_ip),
            )

            # Audit (best-effort).
            try:
                from ..rbac import log_config_change
                log_config_change(
                    cur,
                    action="password_reset_request",
                    target_role="self",
                    target_permission=None,
                    actor_user_id=user_id,
                    actor_role=None,  # actor identity is the user themselves
                    before_state=None,
                    after_state={"requested_ip": client_ip, "expires_at": expires_at.isoformat()},
                    note=f"Password reset requested by {email}",
                )
            except Exception:
                logger.exception("forgot-password: config_audit insert failed")
    except Exception:
        logger.exception("forgot-password: token insert failed")
        # Still return generic message — don't leak DB state.
        return {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}

    # Build the reset URL. Use NOUSVIZ_BASE_URL if set, else fall back to
    # the request's Origin / Host header (development convenience).
    base_url = os.environ.get("NOUSVIZ_BASE_URL", "").rstrip("/")
    if not base_url:
        origin = request.headers.get("origin") or request.headers.get("referer", "")
        if origin:
            # Strip trailing path
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""
        if not base_url:
            host = request.headers.get("host", "")
            scheme = "https" if request.url.scheme == "https" else "http"
            base_url = f"{scheme}://{host}" if host else ""

    reset_url = f"{base_url}/reset-password?token={raw_token}"

    # Send email (best-effort, doesn't affect response).
    _send_password_reset_email_safely(email, reset_url)

    return {"ok": True, "message": "If an account exists with that email, a reset link has been sent."}


@router.post(
    "/reset-password",
    operation_id="auth.reset_password",
    response_model=GenericMessageResponse,
    summary="Consume a reset token + set new password",
    responses={
        400: {
            "description": "Token invalid/used/expired (structured detail) or password too short.",
        },
    },
)
def reset_password(req: ResetPasswordRequest, request: Request):
    """Public endpoint — consume a password reset token.

    Validates the token, hashes the new password, updates the user row,
    marks the token used, kills all sessions for the user.

    Returns:
      200 {ok: true} on success
      400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
      400 if password too short
    """
    if not req.token:
        raise HTTPException(400, {"error": "token_invalid", "message": "Token is required."})
    if not req.password or len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    token_hash = hashlib.sha256(req.token.encode()).hexdigest()

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            """
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        token_row = cur.fetchone()

    if not token_row:
        raise HTTPException(400, {"error": "token_invalid", "message": "This reset link is not valid."})
    if token_row["used_at"] is not None:
        raise HTTPException(400, {"error": "token_used", "message": "This reset link has already been used."})
    if token_row["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(400, {"error": "token_expired", "message": "This reset link has expired. Request a new one."})

    user_id = str(token_row["user_id"])
    new_hash = _hash_password(req.password)

    # Update password, mark token used, kill sessions — all in one
    # transaction. If any step fails, none commit.
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s, updated_at = now() WHERE id = %s",
            (new_hash, user_id),
        )
        cur.execute(
            "UPDATE password_reset_tokens SET used_at = now() WHERE id = %s",
            (token_row["id"],),
        )
        # Kill all active sessions for this user — both legitimate and
        # any hijacker. Forces login with the new password.
        cur.execute(
            "UPDATE user_sessions SET expires_at = now() WHERE user_id = %s AND expires_at > now()",
            (user_id,),
        )

        # Look up user email/role for the audit row.
        cur.execute("SELECT email, role FROM users WHERE id = %s", (user_id,))
        user_row = cur.fetchone()

        # Audit (in-transaction so it commits with the password change).
        try:
            from ..rbac import log_config_change
            log_config_change(
                cur,
                action="password_reset_completed",
                target_role=(user_row[1] if user_row else "unknown"),
                target_permission=None,
                actor_user_id=user_id,
                actor_role=(user_row[1] if user_row else None),
                before_state=None,
                after_state={"sessions_killed": True},
                note=f"Password reset completed via email link by {(user_row[0] if user_row else '?')}",
            )
        except Exception:
            logger.exception("reset-password: config_audit insert failed (continuing)")

    return {"ok": True, "message": "Password updated. You can now log in with your new password."}


# ── Logout ───────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    operation_id="auth.logout",
    response_model=LogoutResponse,
    summary="Expire the current session",
)
def logout(request: Request):
    """Expire the session associated with the X-Session-Token header.

    Idempotent — returns `{ok: true}` whether or not a valid token was
    presented. Public endpoint.
    """
    token = request.headers.get("X-Session-Token")
    if not token:
        return {"ok": True}
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE user_sessions SET expires_at = now() WHERE token_hash = %s", (token_hash,))
    return {"ok": True}


# ── Step-up auth (B236, v0.9.10.0) ────────────────────────────────────────
#
# Sensitive operations (RBAC writes, impersonation) require the actor to
# have re-entered their password within the last 5 minutes. This sets a
# `step_up_until` timestamp on the session row; the requires_step_up
# dependency checks it before allowing sensitive endpoints to execute.
#
# Rate-limited via the same _login_limiter as POST /login.

class StepUpRequest(BaseModel):
    password: str


STEP_UP_TTL_MINUTES = int(os.environ.get("STEP_UP_TTL_MINUTES", "5"))


@router.post(
    "/step-up",
    operation_id="auth.step_up",
    response_model=StepUpResponse,
    summary="Re-authenticate for sensitive operations (B236)",
    responses={
        401: {"model": ErrorDetail, "description": "Not authenticated, or wrong password."},
        429: {"model": ErrorDetail, "description": "Rate-limited (5 attempts / 60s per IP)."},
    },
)
def step_up(req: StepUpRequest, request: Request):
    """Re-authenticate the current session for sensitive operations.

    Returns 200 with `step_up_until` on correct password, sets
    user_sessions.step_up_until to now() + 5 minutes for the active session.

    Wrong password returns 401 with the same error shape as /login. Subject
    to the same per-IP rate limit as /login (5 attempts / 60s).

    Requires an active session — returns 401 if no valid token.
    """
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if _check_login_rate(client_ip):
        raise HTTPException(429, "Too many attempts. Try again in 60 seconds.")

    session_row = _get_session_row(request)
    if not session_row:
        raise HTTPException(401, "Not authenticated")

    # Look up the actor's password hash. If impersonating, the actor (not the
    # target) must re-authenticate — operators stay accountable for their own
    # session activity.
    actor_user_id = session_row["user_id"]
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT password_hash FROM users WHERE id = %s AND is_active = true",
            (actor_user_id,),
        )
        user_row = cur.fetchone()
    if not user_row or not user_row.get("password_hash"):
        raise HTTPException(401, "Cannot re-authenticate: user not configured for password auth")
    if not _check_password(req.password, user_row["password_hash"]):
        raise HTTPException(401, "Invalid password")

    # Set step_up_until on the active session.
    step_up_until = datetime.now(timezone.utc) + timedelta(minutes=STEP_UP_TTL_MINUTES)
    token = request.headers.get("X-Session-Token")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE user_sessions SET step_up_until = %s WHERE token_hash = %s",
            (step_up_until, token_hash),
        )

    return {"step_up_until": step_up_until.isoformat()}


# ── Impersonation (B236, v0.9.10.0) ──────────────────────────────────────
#
# Real impersonation: replaces v0.9.8.4's UI-only `setPreviewRole` preview.
# An admin who outranks a target user may issue an impersonation session
# that carries the target's effective permissions for a bounded window
# (default 10 minutes, configurable via IMPERSONATION_SESSION_MINUTES).
#
# Identity model: Option B (always returns the actor as primary identity;
# `acting_as` field on /me when impersonating). Permission resolution and
# audit emission both use the effective user; the actor stays accountable
# in user_sessions.user_id and auth_audit user_id columns.
#
# Rank rule: actor's role rank must be STRICTLY greater than target's. No
# self-impersonation (rank check fails). Custom roles use rbac_custom_roles.rank.
#
# Audit: rbac_config_audit rows written with action='impersonate_start' and
# 'impersonate_end'; auth_audit rows during impersonation populate
# acting_as_user_id with the target's id.

IMPERSONATION_SESSION_MINUTES = int(os.environ.get("IMPERSONATION_SESSION_MINUTES", "10"))


@router.post(
    "/impersonate/exit",
    operation_id="auth.impersonate.exit",
    response_model=ImpersonateExitResponse,
    summary="End impersonation by clearing session flags (B254 — no re-login)",
)
def impersonate_exit(request: Request):
    """End the current impersonation by clearing flags on the caller's session.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
    killed the impersonation session row. The session row is now the
    actor's existing session (with transient acting_as_* flags); exit
    just clears the flags. The session token, expires_at, and metadata
    all remain unchanged — actor stays logged in as themselves with no
    re-login needed.

    Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
    first-match-wins resolution picks this for `/impersonate/exit`
    rather than treating "exit" as a user_id parameter.

    Idempotent: returns 200 with `wasImpersonating: false` if the
    current session isn't impersonating.

    No step-up requirement — anyone holding the session may leave the
    impersonation. Step-up is required to ENTER impersonation, not exit.
    """
    session_row = _get_session_row(request)
    if not session_row or session_row.get("acting_as_user_id") is None:
        # Not impersonating — no-op.
        return {"ok": True, "wasImpersonating": False}

    actor_user_id = str(session_row["user_id"])
    target_user_id = str(session_row["acting_as_user_id"])

    token = request.headers.get("X-Session-Token")
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT email, role FROM users WHERE id = %s",
            (actor_user_id,),
        )
        actor = cur.fetchone()
        cur.execute(
            "SELECT email, role FROM users WHERE id = %s",
            (target_user_id,),
        )
        target = cur.fetchone()

        # B254: clear the impersonation flags on the actor's session,
        # leaving expires_at unchanged. Token continues to work for the
        # actor's identity.
        cur.execute(
            """
            UPDATE user_sessions
            SET acting_as_user_id = NULL,
                acting_as_until = NULL
            WHERE token_hash = %s
            """,
            (token_hash,),
        )

        # Audit.
        from ..rbac import log_config_change
        log_config_change(
            cur,
            action="impersonate_end",
            target_role=(target or {}).get("role") or "unknown",
            target_permission=None,
            actor_user_id=actor_user_id,
            actor_role=(actor or {}).get("role") or "unknown",
            before_state={
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
            },
            after_state=None,
            note=f"Impersonation ended — {(actor or {}).get('email','?')} stopped acting as {(target or {}).get('email','?')}",
        )

    return {"ok": True, "wasImpersonating": True}


@router.post(
    "/impersonate/{user_id}",
    operation_id="auth.impersonate.start",
    response_model=ImpersonateStartResponse,
    response_model_exclude_none=True,
    summary="Start impersonating a user (B254 — sets session flag, no token swap)",
    responses={
        401: {"model": StepUpRequiredDetail, "description": "Not authenticated or step-up required."},
        403: {"description": "Rank violation (actor's role rank not strictly greater than target's)."},
        404: {"model": ErrorDetail, "description": "Target user not found or not active."},
        409: {"description": "Caller is already impersonating — must exit first."},
    },
)
def impersonate(user_id: str, request: Request):
    """Start impersonating another user — by setting flags on the
    caller's existing session, NOT by issuing a new session token.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
    INSERTed a new short-lived session row and returned a new token.
    Now updates the caller's session with `acting_as_user_id` and
    `acting_as_until`. The caller's token is unchanged. On exit (or
    auto-expire), the flags clear and the caller is back as themselves
    without re-login.

    Requirements:
    - Caller has users.manage (gated by Depends-style routing — see register_route above)
    - Caller has stepped up within the last STEP_UP_TTL_MINUTES
    - Caller's role rank > target's role rank (strict)
    - Target user exists and is active
    - Caller cannot already be impersonating (must exit first)

    Returns:
    - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
      Note: NO `token` field in the response. Caller's existing token
      continues to work; the next /api/auth/me will show the new
      `acting_as` field.
    - 401 if not stepped up.
    - 403 with `{error: 'rank_violation'}` if rank check fails.
    - 404 if target not found.
    - 409 if already impersonating.
    """
    # Step-up gate (manual call — the dep-injection style stacks already
    # used by RBAC writes is harder to compose with the path-param shape
    # of this endpoint; calling directly is equivalent).
    from ..rbac import requires_step_up
    requires_step_up(request)

    actor_session = _get_session_row(request)
    if not actor_session:
        raise HTTPException(401, "Not authenticated")

    # Block re-impersonation (operator must exit current impersonation first).
    if actor_session.get("acting_as_user_id") is not None:
        raise HTTPException(
            409,
            {"error": "already_impersonating",
             "message": "Already impersonating another user. Exit current session first."},
        )

    actor_user_id = str(actor_session["user_id"])

    # Look up actor + target.
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            "SELECT id, email, name, role, is_active FROM users WHERE id = %s",
            (actor_user_id,),
        )
        actor = cur.fetchone()
        if not actor or not actor.get("is_active"):
            raise HTTPException(401, "Actor user inactive or missing")

        cur.execute(
            "SELECT id, email, name, role, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        target = cur.fetchone()
        if not target:
            raise HTTPException(404, f"Target user {user_id!r} not found")
        if not target.get("is_active"):
            raise HTTPException(404, f"Target user {user_id!r} is not active")

    # Rank check.
    from ..rbac import role_rank
    actor_rank = role_rank(actor["role"])
    target_rank = role_rank(target["role"])
    if actor_rank <= target_rank:
        raise HTTPException(
            403,
            {
                "error": "rank_violation",
                "actor_role": actor["role"], "actor_rank": actor_rank,
                "target_role": target["role"], "target_rank": target_rank,
                "message": (
                    f"Cannot impersonate {target['role']!r} — your rank "
                    f"({actor_rank}) does not exceed target's ({target_rank})."
                ),
            },
        )

    # B254: set the impersonation flags on the caller's existing session row.
    # Token stays unchanged. acting_as_until governs the impersonation TTL
    # (default 10 minutes) — independent of the session's overall expires_at.
    acting_as_until = datetime.now(timezone.utc) + timedelta(minutes=IMPERSONATION_SESSION_MINUTES)
    token = request.headers.get("X-Session-Token")
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE user_sessions
            SET acting_as_user_id = %s,
                acting_as_until = %s
            WHERE token_hash = %s
            """,
            (user_id, acting_as_until, token_hash),
        )

        # Audit: rbac_config_audit captures the impersonation event.
        # auth_audit rows during the session will carry acting_as_user_id
        # automatically (middleware reads it from the session row and
        # stashes on request.state for the rbac dep to surface).
        from ..rbac import log_config_change
        log_config_change(
            cur,
            action="impersonate_start",
            target_role=target["role"],
            target_permission=None,
            actor_user_id=actor_user_id,
            actor_role=actor["role"],
            before_state=None,
            after_state={
                "actor_user_id": actor_user_id,
                "actor_role": actor["role"],
                "target_user_id": user_id,
                "target_role": target["role"],
                "acting_as_until": acting_as_until.isoformat(),
            },
            note=f"Impersonation started — {actor['email']} acting as {target['email']}",
        )

    # NO token in the response — caller's token is unchanged.
    return {
        "acting_as": _serialize(target),
        "acting_as_until": acting_as_until.isoformat(),
    }


# ── Verify token ─────────────────────────────────────────────────────────

@router.get(
    "/verify",
    operation_id="auth.verify",
    response_model=VerifyResponse,
    response_model_exclude_none=True,
    summary="Introspect a session token (public)",
)
def verify_token(token: str):
    """Introspect a session token via the `?token=` query parameter.

    Public endpoint — does not require X-Session-Token. Returns
    `{valid: false}` for any invalid, expired, or missing token.
    Used by share-link landing pages and embed contexts to test
    whether a token is still good without consuming it.
    """
    if not token or not token.isprintable():
        return {"valid": False}
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT u.email, u.role FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active = true
        """, (token_hash,))
        row = cur.fetchone()
    if not row:
        return {"valid": False}
    return {"valid": True, "email": row["email"], "role": row["role"]}


# ── Me ───────────────────────────────────────────────────────────────────
#
# B228: /me/* routes are registered with users.read_self (everyone+). The
# rbac dependency on these routes is harmlessly redundant — it calls
# get_me(request) internally to identify the user, then the handler runs
# get_me again. Wasteful but not broken; B229 can optimize. The reason
# we don't skip the dep entirely: every authenticated route in B228 has
# a dep, and consistency matters more than the extra DB hit on /me.

def get_me(request: Request, _: None = Depends(requires("users.read_self"))):
    """Return the EFFECTIVE user for the current session — target if
    impersonating, actor otherwise.

    Internal callers (rbac.dependency, plugin/sync/admin handlers) call
    this to identify "who is this request acting as for permission
    purposes." That's the right semantics — permission checks resolve
    against the effective user.

    NOT registered as a route directly any more (B236, v0.9.10.0). The
    public `GET /api/auth/me` endpoint is `get_me_endpoint` below, which
    composes the Option B response shape (actor + optional `acting_as`
    side field). Internal callers should keep using `get_me(request)`
    as before — its contract is unchanged.

    B236 JOIN resolves on COALESCE(acting_as_user_id, user_id) so
    impersonated sessions return the target. Behaviour unchanged for
    non-impersonated sessions.
    """
    token = request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(401, "Not authenticated")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT u.* FROM users u
            JOIN user_sessions s ON u.id = COALESCE(s.acting_as_user_id, s.user_id)
            WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active = true
        """, (token_hash,))
        user = cur.fetchone()
    if not user:
        raise HTTPException(401, "Not authenticated")
    return _serialize(user)


@router.get(
    "/me",
    operation_id="auth.me",
    response_model=MeResponse,
    response_model_exclude_none=True,
    summary="Current actor (with optional acting_as target)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
def get_me_endpoint(request: Request, _: None = Depends(requires("users.read_self"))):
    """Public `GET /api/auth/me` endpoint — Option B identity shape.

    B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
    to the session) as the primary identity. When the session is
    impersonating, the response also carries an `acting_as` field with
    the target's serialized identity.

    Frontend reads `me` for actor identity (audit, "Exit impersonation"
    banner, log-out button) and `me.acting_as` for effective identity
    (permission checks, role display). The `useEffectiveIdentity()` hook
    centralizes the choice for permission/UI display.
    """
    token = request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(401, "Not authenticated")
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        # Fetch the actor (always the session's user_id) and the optional
        # target (acting_as_user_id, may be NULL) in one round-trip.
        cur.execute(
            """
            SELECT
                actor.*,
                target.id AS target_id,
                target.email AS target_email,
                target.name AS target_name,
                target.role AS target_role,
                target.avatar_url AS target_avatar_url,
                target.is_active AS target_is_active,
                target.created_at AS target_created_at,
                target.last_login AS target_last_login
            FROM user_sessions s
            JOIN users actor ON actor.id = s.user_id
            LEFT JOIN users target ON target.id = s.acting_as_user_id
            WHERE s.token_hash = %s
              AND s.expires_at > now()
              AND actor.is_active = true
            """,
            (token_hash,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(401, "Not authenticated")

    # Build the actor payload from the row's actor.* columns.
    # The actor's columns are at the top level of the dict.
    actor_keys = {"id", "email", "name", "role", "avatar_url", "is_active",
                  "created_at", "last_login", "auth_method", "login_count",
                  "last_seen_at", "color"}  # `_serialize` will iso-format datetimes
    actor_dict = {k: row[k] for k in row.keys() if k in actor_keys}
    response = _serialize(actor_dict)

    # If impersonating, attach the target as `acting_as`. Otherwise omit.
    if row.get("target_id"):
        target_serialized = _serialize({
            "id": row["target_id"],
            "email": row["target_email"],
            "name": row["target_name"],
            "role": row["target_role"],
            "avatar_url": row["target_avatar_url"],
            "is_active": row["target_is_active"],
            "created_at": row["target_created_at"],
            "last_login": row["target_last_login"],
        })
        response["acting_as"] = target_serialized

    return response


@router.get(
    "/me/permissions",
    operation_id="auth.me.permissions",
    response_model=MyPermissionsResponse,
    summary="Resolved permissions for the current effective user",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
def get_my_permissions(
    request: Request,
    _: None = Depends(requires("users.read_self")),
):
    """B230 (v0.9.8.3): return the set of permissions the current user
    holds. The frontend uses this for role-aware UI (sidebar nav,
    conditional buttons) without needing to duplicate the role-permission
    catalog from rbac/permissions.py.

    Resolves the user, looks up their role's permission set, and returns
    a flat list. v0.9.9.x will layer DB overrides on top — this same
    endpoint will return the resolved post-override set, so the frontend
    contract doesn't change.
    """
    user = get_me(request)
    from ..rbac import all_permissions_for_role
    return {
        "role": user.get("role"),
        "permissions": sorted(all_permissions_for_role(user.get("role") or "")),
    }


@router.get(
    "/role-permissions/{role}",
    operation_id="auth.role_permissions",
    response_model=RolePermissionsResponse,
    summary="Permissions held by an arbitrary role (admin preview UI)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Unknown role."},
    },
)
def get_role_permissions(
    role: str,
    request: Request,
    _: None = Depends(requires("system.audit")),
):
    """B231 (v0.9.8.4): return the permissions held by an arbitrary role.

    Powers the admin-only "preview as <role>" UI — admins toggle the
    sidebar to render as if they had a different role, and the frontend
    needs the permission set for that role to compute hasPermission().

    Frontend-only feature: the backend still authorizes the request
    based on the admin's REAL session. This endpoint is gated by
    system.audit so a non-admin can't fish for role permissions.

    Returns 404 if the role is unknown (typo, future custom role).
    """
    from ..rbac import all_permissions_for_role, ROLE_PERMISSIONS

    if role not in ROLE_PERMISSIONS:
        raise HTTPException(404, f"Unknown role: {role!r}")

    return {
        "role": role,
        "permissions": sorted(all_permissions_for_role(role)),
    }


# ── Update own profile ───────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None


@router.patch(
    "/me",
    operation_id="auth.me.update",
    response_model=UserSerialized,
    response_model_exclude_none=True,
    summary="Update own profile (password change requires step-up — B251)",
    responses={
        400: {"model": ErrorDetail, "description": "Password too short or empty body."},
        401: {"model": StepUpRequiredDetail, "description": "Step-up auth required for password change."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.read_self permission."},
    },
)
def update_me(
    req: ProfileUpdate,
    request: Request,
    _: None = Depends(requires("users.read_self")),
):
    """Update the current user's profile.

    B251 (v0.9.10.0.3): when the request includes the password field,
    requires recent step-up auth (same gate as RBAC writes from B236).
    Without this, a stolen session token could change the password and
    lock the real owner out. Other fields (name, etc.) remain step-up-
    free — they're not security-sensitive.
    """
    # Step-up gate fires only when password is being changed.
    if req.password:
        from ..rbac import requires_step_up
        requires_step_up(request)

    user = get_me(request)
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.password:
        if len(req.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters.")
        updates["password_hash"] = _hash_password(req.password)
    if not updates:
        raise HTTPException(400, "Nothing to update.")

    set_parts = [f"{k} = %s" for k in updates] + ["updated_at = now()"]
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            f"UPDATE users SET {', '.join(set_parts)} WHERE id = %s RETURNING *",
            list(updates.values()) + [user["id"]],
        )
        updated = _serialize(cur.fetchone())

        # B251: audit password changes (in-transaction with the update).
        if req.password:
            try:
                from ..rbac import log_config_change
                log_config_change(
                    cur,
                    action="password_change_self",
                    target_role=updated.get("role") or "unknown",
                    target_permission=None,
                    actor_user_id=str(user["id"]),
                    actor_role=user.get("role"),
                    before_state=None,
                    after_state={"step_up_used": True},
                    note=f"Self password change by {user.get('email')}",
                )
            except Exception:
                logger.exception("update_me: config_audit insert failed (continuing)")

    return updated


# ── Avatar upload ────────────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "uploads", "avatars")
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB

@router.post(
    "/me/avatar",
    operation_id="auth.me.avatar.upload",
    response_model=AvatarResponse,
    summary="Upload avatar image (multipart; max 2 MB; jpg/png/webp/gif)",
    responses={
        400: {"model": ErrorDetail, "description": "Bad multipart, file too large, or unsupported MIME type."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
async def upload_avatar(
    request: Request,
    _: None = Depends(requires("users.read_self")),
):

    user = get_me(request)
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        raise HTTPException(400, "Expected multipart/form-data")

    form = await request.form()
    file = form.get("avatar")
    if not file or not hasattr(file, "read"):
        raise HTTPException(400, "No file uploaded")

    data = await file.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(400, "File too large (max 2MB)")

    ct = getattr(file, "content_type", "") or ""
    if ct not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(400, "Only JPEG, PNG, WebP, and GIF images are allowed")

    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}[ct]
    filename = f"{user['id']}{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Remove old avatar files for this user
    for old in os.listdir(UPLOAD_DIR):
        if old.startswith(user["id"]):
            os.remove(os.path.join(UPLOAD_DIR, old))

    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    avatar_url = f"/uploads/avatars/{filename}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar_url = %s, updated_at = now() WHERE id = %s", (avatar_url, user["id"]))

    return {"avatar_url": avatar_url}


@router.delete(
    "/me/avatar",
    operation_id="auth.me.avatar.delete",
    response_model=AvatarResponse,
    summary="Delete avatar image (returns avatar_url=null)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
def delete_avatar(
    request: Request,
    _: None = Depends(requires("users.read_self")),
):
    user = get_me(request)
    # Remove files
    if os.path.isdir(UPLOAD_DIR):
        for old in os.listdir(UPLOAD_DIR):
            if old.startswith(user["id"]):
                os.remove(os.path.join(UPLOAD_DIR, old))
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar_url = NULL, updated_at = now() WHERE id = %s", (user["id"],))
    return {"avatar_url": None}


# ── User management (admin+) ────────────────────────────────────────────


@router.get(
    "/users",
    operation_id="auth.users.list",
    response_model=UsersListResponse,
    response_model_exclude_none=True,
    summary="List all users (admin)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
    },
)
def list_users(
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = [_serialize(r) for r in cur.fetchall()]

    # B305: attach plugin_access_summary { mode, count } to every user
    # in one batched query so the UsersPanel can render
    # "Plugins: N of M" without N+1 fetches. Admin/superadmin rows are
    # always 'all' (they bypass the filter); non-admin rows reflect
    # actual ACL row count.
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT principal_id, COUNT(*) FROM resource_acls
                WHERE resource_type = 'plugin' AND principal_kind = 'user'
                GROUP BY principal_id
                """
            )
            counts = {row[0]: int(row[1]) for row in cur.fetchall()}
        from .plugins import _installed_slugs

        total_installed = max(len(_installed_slugs()), 1)
        for u in users:
            if u.get("role") in ("admin", "superadmin"):
                u["plugin_access_summary"] = {
                    "mode": "all",
                    "count": total_installed,
                    "total": total_installed,
                    "unrestricted_by_role": True,
                }
                continue
            n = counts.get(str(u["id"]), 0)
            u["plugin_access_summary"] = {
                "mode": "specific" if n > 0 else "all",
                "count": n if n > 0 else total_installed,
                "total": total_installed,
                "unrestricted_by_role": False,
            }
    except Exception:
        logger.exception(
            "list_users: B305 plugin_access_summary attach failed — returning rows without it",
        )

    return {"users": users}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch(
    "/users/{user_id}",
    operation_id="auth.users.update",
    response_model=UserSerialized,
    response_model_exclude_none=True,
    summary="Update a user's name/role/active flag (admin)",
    responses={
        400: {"model": ErrorDetail, "description": "Empty body or invalid role."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks rights to edit this user."},
        404: {"model": ErrorDetail, "description": "User not found."},
    },
)
def update_user(
    user_id: str,
    req: UserUpdate,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    admin = get_me(request)
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update.")
    if "role" in updates:
        valid_roles = ("admin", "analyst", "viewer") if admin["role"] == "admin" else ("superadmin", "admin", "analyst", "viewer")
        if updates["role"] not in valid_roles:
            raise HTTPException(400, f"Invalid role. Options: {', '.join(valid_roles)}")

    # Block admin from editing superadmin rows
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        target = cur.fetchone()
        if not target:
            raise HTTPException(404, "User not found.")
        if target["role"] == "superadmin" and admin["role"] != "superadmin":
            raise HTTPException(403, "Only a superadmin can edit another superadmin.")

    set_parts = [f"{k} = %s" for k in updates] + ["updated_at = now()"]
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute(
            f"UPDATE users SET {', '.join(set_parts)} WHERE id = %s RETURNING *",
            list(updates.values()) + [user_id],
        )
        updated = cur.fetchone()
    if not updated:
        raise HTTPException(404, "User not found.")
    return _serialize(updated)


@router.delete(
    "/users/{user_id}",
    operation_id="auth.users.deactivate",
    response_model=DeactivateUserResponse,
    summary="Deactivate a user (soft — sets is_active=false)",
    responses={
        400: {"model": ErrorDetail, "description": "Cannot deactivate own account."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Only superadmin can delete another superadmin."},
        404: {"model": ErrorDetail, "description": "User not found."},
    },
)
def delete_user(
    user_id: str,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    admin = get_me(request)
    if str(admin["id"]) == user_id:
        raise HTTPException(400, "You cannot deactivate your own account.")
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        target = cur.fetchone()
        if not target:
            raise HTTPException(404, "User not found.")
        if target["role"] == "superadmin" and admin["role"] != "superadmin":
            raise HTTPException(403, "Only a superadmin can delete another superadmin.")
        cur.execute("UPDATE users SET is_active = false, updated_at = now() WHERE id = %s", (user_id,))

    from .activity import record_activity
    record_activity(action="user_deactivate", detail={"email": target.get("email", user_id), "role": target["role"]})

    return {"deactivated": True}


@router.post(
    "/users/{user_id}/reactivate",
    operation_id="auth.users.reactivate",
    response_model=UserSerialized,
    response_model_exclude_none=True,
    summary="Reactivate a deactivated user",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
        404: {"model": ErrorDetail, "description": "User not found or already active."},
    },
)
def reactivate_user(
    user_id: str,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("UPDATE users SET is_active = true, updated_at = now() WHERE id = %s AND is_active = false RETURNING *", (user_id,))
        updated = cur.fetchone()
    if not updated:
        raise HTTPException(404, "User not found or already active.")

    from .activity import record_activity
    record_activity(action="user_reactivate", detail={"email": updated["email"]})

    return _serialize(updated)


# ── Superadmin promote/demote ────────────────────────────────────────────

@router.post(
    "/users/{user_id}/promote",
    operation_id="auth.users.promote",
    response_model=UserSerialized,
    response_model_exclude_none=True,
    summary="Promote an admin to superadmin (superadmin only)",
    responses={
        400: {"model": ErrorDetail, "description": "User not found or is not an admin."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage_admins permission."},
    },
)
def promote_to_superadmin(
    user_id: str,
    request: Request,
    # B227 dual-check: registry says users.manage_admins, inline says superadmin.
    _: None = Depends(requires("users.manage_admins")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("UPDATE users SET role = 'superadmin', updated_at = now() WHERE id = %s AND role = 'admin' RETURNING *", (user_id,))
        updated = cur.fetchone()
    if not updated:
        raise HTTPException(400, "User not found or is not an admin (only admins can be promoted).")
    return _serialize(updated)


@router.post(
    "/users/{user_id}/demote",
    operation_id="auth.users.demote",
    response_model=UserSerialized,
    response_model_exclude_none=True,
    summary="Demote a superadmin to admin (DB trigger blocks zero superadmins)",
    responses={
        400: {"model": ErrorDetail, "description": "User not found or not a superadmin, or only-superadmin guard fired."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage_admins permission."},
    },
)
def demote_superadmin(
    user_id: str,
    request: Request,
    _: None = Depends(requires("users.manage_admins")),
):
    # The DB trigger prevents reducing to zero superadmins
    try:
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute("UPDATE users SET role = 'admin', updated_at = now() WHERE id = %s AND role = 'superadmin' RETURNING *", (user_id,))
            updated = cur.fetchone()
        if not updated:
            raise HTTPException(400, "User not found or is not a superadmin.")
        return _serialize(updated)
    except Exception as e:
        if "superadmin must exist" in str(e).lower():
            raise HTTPException(409, "At least one superadmin must exist. Cannot demote the last superadmin.")
        raise


# ── B305 (v0.10.0.6) — per-user plugin allowlist ─────────────────────────
#
# Three endpoints (all users.manage):
#   GET  /api/auth/users/{user_id}/plugin-access
#   PUT  /api/auth/users/{user_id}/plugin-access
#   GET  /api/auth/users/with-restricted-plugin-access?exclude_slug=<slug>
#
# Consumes resource_acls (B248). Admin/superadmin targets reject (409) on
# PUT — they're unrestricted by design. Unknown slugs reject (400). The
# install-success grant banner on the frontend calls the third endpoint
# to find users who can't yet see a freshly-installed plugin.


class PluginAccessPayload(BaseModel):
    mode: str  # "all" | "specific"
    plugin_ids: list[str] = []


def _validate_plugin_access_payload(payload: dict) -> tuple[str, list[str]]:
    """Coerce + validate a plugin_access payload. Returns (mode, slugs).

    Raises HTTPException(400) on invalid shape or unknown slugs.
    Used by both the PUT endpoint and the invite payload extension.
    """
    if not isinstance(payload, dict):
        raise HTTPException(400, "plugin_access must be an object.")
    mode = str(payload.get("mode") or "").strip().lower()
    if mode not in {"all", "specific"}:
        raise HTTPException(400, "plugin_access.mode must be 'all' or 'specific'.")
    raw_ids = payload.get("plugin_ids") or []
    if not isinstance(raw_ids, list):
        raise HTTPException(400, "plugin_access.plugin_ids must be an array of strings.")
    slugs = [str(s).strip() for s in raw_ids if str(s).strip()]
    if mode == "all":
        # Invariant: mode='all' ⇔ zero rows. Slugs are irrelevant; clear
        # them so callers can't accidentally persist ghost values.
        slugs = []
    if mode == "specific" and not slugs:
        # Treat empty specific as "all" — no rows == unrestricted.
        # Caller may want to reject; we coerce here to keep the
        # invariant: zero rows ⇔ mode='all'.
        mode = "all"
        slugs = []
    if mode == "specific":
        # Validate against installed plugins. Late import — avoids a
        # circular dep with the plugins router.
        from .plugins import _installed_slugs

        installed = _installed_slugs()
        unknown = [s for s in slugs if s not in installed]
        if unknown:
            raise HTTPException(
                400,
                f"plugin_access.plugin_ids contains slugs that are not installed: {sorted(unknown)}",
            )
    return mode, slugs


@router.get(
    "/users/with-restricted-plugin-access",
    operation_id="auth.users.with_restricted_plugin_access",
    response_model=RestrictedUsersListResponse,
    response_model_exclude_none=True,
    summary="Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)",
    responses={
        400: {"model": ErrorDetail, "description": "Missing exclude_slug query parameter."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
    },
)
def list_users_with_restricted_plugin_access(
    request: Request,
    exclude_slug: str = "",
    _: None = Depends(requires("users.manage")),
):
    """Used by the install-success grant banner on the frontend. Returns
    users with `mode='specific'` whose allowlist does NOT include
    `exclude_slug` — i.e. the operator-visible "people who can't see
    this new plugin yet" set.
    """
    if not exclude_slug:
        raise HTTPException(400, "exclude_slug query parameter is required.")
    from ..rbac import users_with_restricted_access_excluding

    return {"users": users_with_restricted_access_excluding(exclude_slug)}


@router.get(
    "/users/{user_id}/plugin-access",
    operation_id="auth.users.plugin_access.get",
    response_model=PluginAccessResponse,
    response_model_exclude_none=True,
    summary="Get a user's plugin-visibility allowlist (admin)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
        404: {"model": ErrorDetail, "description": "User not found."},
    },
)
def get_user_plugin_access_endpoint(
    user_id: str,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT id, role FROM users WHERE id::text = %s", (user_id,))
        target = cur.fetchone()
    if not target:
        raise HTTPException(404, "User not found.")
    from ..rbac import get_user_plugin_access

    state = get_user_plugin_access(str(target["id"]))
    state["role"] = target["role"]
    state["unrestricted_by_role"] = target["role"] in ("admin", "superadmin")
    return state


@router.put(
    "/users/{user_id}/plugin-access",
    operation_id="auth.users.plugin_access.set",
    response_model=PluginAccessResponse,
    response_model_exclude_none=True,
    summary="Replace a user's plugin-visibility allowlist (admin)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid payload shape or unknown plugin slug."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
        404: {"model": ErrorDetail, "description": "User not found."},
        409: {"model": ErrorDetail, "description": "Target user has an admin/superadmin role — unrestricted by design."},
    },
)
def set_user_plugin_access_endpoint(
    user_id: str,
    req: PluginAccessPayload,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    admin = get_me(request)
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT id, role FROM users WHERE id::text = %s", (user_id,))
        target = cur.fetchone()
    if not target:
        raise HTTPException(404, "User not found.")
    if target["role"] in ("admin", "superadmin"):
        raise HTTPException(
            409,
            "This user has an admin role — admins are unrestricted by design. "
            "Demote first if you want to restrict their plugin access.",
        )
    mode, slugs = _validate_plugin_access_payload(req.model_dump())
    from ..rbac import set_user_plugin_access

    state = set_user_plugin_access(
        str(target["id"]),
        mode,
        slugs,
        actor_user_id=str(admin["id"]),
        actor_role=admin.get("role"),
    )
    state["role"] = target["role"]
    state["unrestricted_by_role"] = False
    return state


# ── Invite management ────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "analyst"
    # B305: optional invite-time plugin allowlist. None → "all plugins"
    # (current default; backward-compatible with older clients that
    # don't send this field).
    plugin_access: Optional[dict] = None


@router.post(
    "/users/invite",
    operation_id="auth.users.invite.create",
    response_model=InviteCreateResponse,
    response_model_exclude_none=True,
    summary="Invite a user via email (admin)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid role for invites."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
        409: {"model": ErrorDetail, "description": "Email already has a user account."},
    },
)
def invite_user(
    req: InviteRequest,
    request: Request,
    # B227 dual-check: registry says users.manage, inline says admin.
    _: None = Depends(requires("users.manage")),
):
    admin = get_me(request)
    if req.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "Invite role must be admin, analyst, or viewer (not superadmin — promote after they register).")

    # Check if user already exists
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (req.email.lower(),))
        if cur.fetchone():
            raise HTTPException(409, "A user with this email already exists.")

    # B305: validate the optional plugin_access payload up-front and
    # normalise it for storage. Admins/superadmins are unrestricted by
    # design, so we silently ignore plugin_access for those invites
    # rather than reject (operator's intent is already covered by role).
    plugin_access_for_jsonb: Optional[dict] = None
    if req.plugin_access is not None and req.role not in ("admin", "superadmin"):
        mode, slugs = _validate_plugin_access_payload(req.plugin_access)
        if mode == "specific":
            plugin_access_for_jsonb = {"mode": "specific", "plugin_ids": sorted(set(slugs))}
        # mode == "all" → store NULL (matches "no restriction").

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    import json as _json
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        # Revoke any existing pending invite for this email
        cur.execute("DELETE FROM user_invites WHERE email = %s AND used_at IS NULL", (req.email.lower(),))
        cur.execute("""
            INSERT INTO user_invites (email, role, token_hash, invited_by, plugin_access_pending)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            RETURNING *
        """, (
            req.email.lower(),
            req.role,
            token_hash,
            admin["id"],
            _json.dumps(plugin_access_for_jsonb) if plugin_access_for_jsonb is not None else None,
        ))
        invite = _serialize(cur.fetchone())

    # Build invite URL
    base = os.environ.get("NOUSVIZ_BASE_URL", "").strip()
    if not base:
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("host", "localhost")
        base = f"{forwarded_proto}://{host}"
    invite_url = f"{base}/accept-invite?token={raw_token}"

    # Try to send email — always attempt, _send() returns a clear error if SMTP_HOST is unset
    email_sent = False
    email_error = ""
    try:
        from ..services.email import send_invite_email
        ok, err = send_invite_email(req.email, invite_url, admin.get("name") or admin.get("email", "Admin"))
        email_sent = ok
        email_error = err
    except Exception as e:
        email_error = str(e)

    from .activity import record_activity
    record_activity(action="user_invite", detail={"email": req.email, "role": req.role, "email_sent": email_sent})

    return {
        "invite": invite,
        "invite_url": invite_url if not email_sent else None,  # expose URL only if email failed (manual copy fallback)
        "email_sent": email_sent,
        "email_error": email_error if not email_sent else None,
    }


@router.get(
    "/users/invites",
    operation_id="auth.users.invites.list",
    response_model=InvitesListResponse,
    response_model_exclude_none=True,
    summary="List recent invites (admin)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
    },
)
def list_invites(
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT i.*, u.email AS inviter_email, u.name AS inviter_name
            FROM user_invites i
            JOIN users u ON u.id = i.invited_by
            ORDER BY i.created_at DESC
            LIMIT 50
        """)
        invites = [_serialize(r) for r in cur.fetchall()]
    return {"invites": invites}


@router.delete(
    "/users/invite/{invite_id}",
    operation_id="auth.users.invite.revoke",
    response_model=InviteRevokeResponse,
    summary="Revoke an unused invite",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
        404: {"model": ErrorDetail, "description": "Invite not found or already used."},
    },
)
def revoke_invite(
    invite_id: str,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_invites WHERE id = %s AND used_at IS NULL RETURNING id", (invite_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Invite not found or already used.")
    return {"revoked": True}


# ── API key management ───────────────────────────────────────────────────

@router.post(
    "/users/{user_id}/api-key",
    operation_id="auth.users.api_key.create",
    response_model=ApiKeyCreateResponse,
    summary="Generate an API key for a user (raw key shown once)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the users.manage permission."},
    },
)
def generate_api_key(
    user_id: str,
    request: Request,
    _: None = Depends(requires("users.manage")),
):
    admin = get_me(request)

    raw_key = f"nv_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    key_name = f"user:{user_id}"

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE api_keys SET revoked_at = now() WHERE name = %s AND revoked_at IS NULL", (key_name,))
        cur.execute("INSERT INTO api_keys (name, key_prefix, key_hash) VALUES (%s, %s, %s)", (key_name, key_prefix, key_hash))
        cur.execute("UPDATE users SET api_key = %s, updated_at = now() WHERE id = %s", (key_prefix + "...", user_id))

    from .activity import record_activity
    record_activity(action="api_key_create", detail={"user_id": user_id, "prefix": key_prefix})

    return {"api_key": raw_key, "message": "Store this key securely — it won't be shown again."}


# ── Activity log ─────────────────────────────────────────────────────────

@router.get(
    "/activity",
    operation_id="auth.activity",
    response_model=AuthActivityResponse,
    response_model_exclude_none=True,
    summary="Auth activity log (admin audit)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def get_activity(
    request: Request,
    limit: int = 50,
    _: None = Depends(requires("system.audit")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT a.*, u.name AS user_name
            FROM user_activity a
            LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.created_at DESC LIMIT %s
        """, (limit,))
        rows = [_serialize(r) for r in cur.fetchall()]
    return {"activity": rows}


# ── First-run security config (setup wizard) ────────────────────────────

class SetupConfigRequest(BaseModel):
    auth_required: bool = True
    postgres_password: Optional[str] = None
    generate_encryption_key: bool = False


@router.post(
    "/setup/config",
    operation_id="auth.setup.config",
    response_model=SetupOkResponse,
    summary="First-run wizard: write security-config to .env",
    responses={
        400: {"model": ErrorDetail, "description": "Postgres-password ALTER failed."},
        403: {"model": ErrorDetail, "description": "Already configured."},
    },
)
def setup_config(req: SetupConfigRequest):
    from .._env import write_and_reload

    # B252 (v0.9.11.2): the wizard runs once, before the first superadmin
    # exists. Once any user exists, the wizard is "done" — settings page
    # owns subsequent changes. The encryption-key path is the one
    # exception: it's safe to top-up an existing install with a generated
    # key if one was missed at install.
    already_configured = _users_exist()
    if already_configured and not req.generate_encryption_key:
        raise HTTPException(403, "Already configured. Use Settings to change credentials.")

    # If a new Postgres password is provided, apply it before writing .env
    if req.postgres_password:
        pg_user = os.environ.get("POSTGRES_USER", "nousviz")
        try:
            with get_pg_conn() as conn:
                conn.autocommit = True
                cur = conn.cursor()
                from psycopg2 import sql as pg_sql
                cur.execute(
                    pg_sql.SQL("ALTER USER {} WITH PASSWORD %s").format(pg_sql.Identifier(pg_user)),
                    (req.postgres_password,),
                )
                cur.close()
        except Exception as e:
            raise HTTPException(400, f"Failed to change Postgres password: {e}")

    updates: dict[str, str] = {
        "AUTH_REQUIRED": "true" if req.auth_required else "false",
    }
    if req.postgres_password:
        updates["POSTGRES_PASSWORD"] = req.postgres_password
    if req.generate_encryption_key and not os.environ.get("NOUSVIZ_ENCRYPTION_KEY", "").strip():
        updates["NOUSVIZ_ENCRYPTION_KEY"] = secrets.token_hex(32)

    write_and_reload(updates)
    return {"ok": True}


# ── Setup: create first admin (legacy — pre-P58) ────────────────────────

class SetupRequest(BaseModel):
    email: str
    name: Optional[str] = None


@router.post(
    "/setup",
    operation_id="auth.setup",
    response_model=SetupResponse,
    summary="Legacy first-admin creation (pre-P58, kept for backward compat)",
)
def initial_setup(req: SetupRequest):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT COUNT(*) AS count FROM users")
        if cur.fetchone()["count"] > 0:
            raise HTTPException(400, "Setup already completed — users exist")
        cur.execute(
            "INSERT INTO users (email, name, role, auth_method) VALUES (%s, %s, 'admin', 'cloudflare') RETURNING *",
            (req.email.lower().strip(), req.name),
        )
        admin = _serialize(cur.fetchone())
    return {"user": admin, "message": "Admin user created."}
