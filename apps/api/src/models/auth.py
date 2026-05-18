"""B215 (v0.9.10.2): typed responses for /api/auth/* routes.

Models match the actual return shape of `apps/api/src/routes/auth.py`.
The `MeResponse` shape is the headline contract of B236 (Option B
identity model): always returns the actor as primary identity, with an
optional `acting_as` side field when the session is impersonating.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserSerialized(BaseModel):
    """Serialized user row — output of `_serialize()` in routes/auth.py.

    `password_hash` is always stripped. `api_key` is truncated to first
    8 chars + ellipsis. Datetimes are ISO-8601 strings.

    Extra keys are allowed because user rows include columns added by
    later migrations (e.g. `last_seen_at`, `color`) that may or may not
    be present depending on schema state.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="UUID of the user.")
    email: str
    name: Optional[str] = None
    role: str = Field(..., description="'superadmin' | 'admin' | 'analyst' | 'viewer' | custom role name.")
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None
    auth_method: Optional[str] = Field(default=None, description="'password' | 'api_key'.")
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    login_count: Optional[int] = None


class AuthStatusResponse(BaseModel):
    """GET /api/auth/status — public endpoint, returns auth-mode info.

    Always returned, regardless of whether the caller is authenticated.
    `user` is null when no valid session token is presented.
    """
    authenticated: bool
    auth_required: bool = Field(..., description="True iff AUTH_REQUIRED=true in .env.")
    users_exist: bool = Field(..., description="True iff at least one user row exists.")
    user: Optional[UserSerialized] = None


class LoginResponse(BaseModel):
    """POST /api/auth/login response."""
    token: str = Field(..., description="Raw session token. Send as X-Session-Token on subsequent requests.")
    expires_at: str = Field(..., description="ISO-8601 expiry of the session.")
    user: UserSerialized


class LogoutResponse(BaseModel):
    """POST /api/auth/logout — always returns ok=True (idempotent)."""
    ok: bool = Field(default=True, description="Always True (logout is idempotent).")


class VerifyResponse(BaseModel):
    """GET /api/auth/verify — token introspection.

    Returns `{valid: false}` for any invalid/expired/missing token; the
    caller-friendly fields are only set when the token resolves to an
    active user.
    """
    valid: bool
    email: Optional[str] = None
    role: Optional[str] = None


class MeResponse(BaseModel):
    """GET /api/auth/me — Option B identity shape (B236).

    The top-level fields describe the ACTOR (the human authenticated to
    this session). `acting_as`, when present, carries the target the
    actor is currently impersonating.

    Frontend reads `me` for actor identity (for the impersonation
    banner, audit display, log-out button) and `me.acting_as` for
    effective identity (permission resolution, role display). The
    `useEffectiveIdentity()` hook centralizes this choice.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    email: str
    name: Optional[str] = None
    role: str
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None
    auth_method: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    login_count: Optional[int] = None
    acting_as: Optional[UserSerialized] = Field(
        default=None,
        description="Target user when the session is impersonating; absent otherwise.",
    )


class MyPermissionsResponse(BaseModel):
    """GET /api/auth/me/permissions — flat list of permissions for the
    EFFECTIVE user (target if impersonating, actor otherwise).

    The permission set is the resolved post-override set as of v0.9.9.x.
    """
    role: str
    permissions: list[str] = Field(
        ...,
        description="Sorted list of permission strings, e.g. ['plugins.install', 'system.logs'].",
    )


# ── Password reset ────────────────────────────────────────────────────


class GenericMessageResponse(BaseModel):
    """Generic `{ok, message}` response — used by forgot-password and
    reset-password to keep the response shape constant across success
    and silent-no-op paths (enumeration resistance)."""
    ok: bool = True
    message: str


# ── Step-up + impersonation ───────────────────────────────────────────


class StepUpResponse(BaseModel):
    """POST /api/auth/step-up — re-auth confirmed."""
    step_up_until: str = Field(
        ...,
        description="ISO-8601 timestamp until which sensitive ops are unlocked (default 5 min).",
    )


class ImpersonateExitResponse(BaseModel):
    """POST /api/auth/impersonate/exit — idempotent, always returns 200."""
    ok: bool = True
    wasImpersonating: bool


class ImpersonateStartResponse(BaseModel):
    """POST /api/auth/impersonate/{user_id}.

    NOTE: no `token` field. The caller's existing session token is
    reused with `acting_as_user_id` set on the session row (B254).
    """
    acting_as: UserSerialized
    acting_as_until: str


# ── Role permissions ──────────────────────────────────────────────────


class RolePermissionsResponse(BaseModel):
    """GET /api/auth/role-permissions/{role} — admin-only role preview."""
    role: str
    permissions: list[str]


# ── Avatar ────────────────────────────────────────────────────────────


class AvatarResponse(BaseModel):
    """POST/DELETE /api/auth/me/avatar — current avatar URL.

    DELETE returns avatar_url=null; POST returns the new URL.
    """
    avatar_url: Optional[str] = None


# ── User CRUD (admin) ─────────────────────────────────────────────────


class UsersListResponse(BaseModel):
    """GET /api/auth/users — every user, newest-first."""
    users: list[UserSerialized]


class DeactivateUserResponse(BaseModel):
    """DELETE /api/auth/users/{user_id} — soft delete (sets is_active=false)."""
    deactivated: bool = True


# ── Invites ───────────────────────────────────────────────────────────


class InviteRow(BaseModel):
    """A single user_invites row."""
    model_config = ConfigDict(extra="allow")

    id: str
    email: str
    role: str
    invited_by: Optional[str] = None
    inviter_email: Optional[str] = None
    inviter_name: Optional[str] = None
    used_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class InviteCreateResponse(BaseModel):
    """POST /api/auth/users/invite — invite issued.

    `invite_url` is exposed only when email send failed (operator can
    copy/paste the link). On successful send, it stays null and only
    `email_sent=true` is reported.
    """
    invite: InviteRow
    invite_url: Optional[str] = None
    email_sent: bool
    email_error: Optional[str] = None


class InvitesListResponse(BaseModel):
    """GET /api/auth/users/invites — recent invites with inviter info."""
    invites: list[InviteRow]


class InviteRevokeResponse(BaseModel):
    """DELETE /api/auth/users/invite/{invite_id}."""
    revoked: bool = True


# ── API keys ──────────────────────────────────────────────────────────


class ApiKeyCreateResponse(BaseModel):
    """POST /api/auth/users/{user_id}/api-key.

    The raw key is returned exactly once — store it immediately.
    """
    api_key: str = Field(..., description="Raw API key (nv_<random>); shown only on creation.")
    message: str


# ── Activity ──────────────────────────────────────────────────────────


class AuthActivityRow(BaseModel):
    """A single user_activity row joined to the user's name."""
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: Optional[str] = None
    detail: Optional[Any] = None
    created_at: Optional[str] = None


class AuthActivityResponse(BaseModel):
    """GET /api/auth/activity — admin-only audit view."""
    activity: list[AuthActivityRow]


# ── Setup (first-run wizard) ──────────────────────────────────────────


class SetupOkResponse(BaseModel):
    """POST /api/auth/setup/config — first-run wizard confirms write."""
    ok: bool = True


class SetupResponse(BaseModel):
    """POST /api/auth/setup — legacy first-admin creation.

    extra='allow' covers whatever the legacy handler returns; this
    surface is kept for backward compat and not actively maintained.
    """
    model_config = ConfigDict(extra="allow")


# ── B305 (v0.10.0.6) — per-user plugin allowlist responses ───────────


class PluginAccessResponse(BaseModel):
    """GET / PUT /api/auth/users/{user_id}/plugin-access — current
    allowlist state for the user.

    `mode='all'` means zero ACL rows (unrestricted). `mode='specific'`
    means one or more rows; `plugin_ids` lists the slugs the user is
    allowed to see (utility plugins always pass through regardless).
    """
    mode: str = Field(..., description="'all' | 'specific'")
    plugin_ids: list[str] = Field(default_factory=list)
    role: Optional[str] = Field(
        None, description="The target user's current role, for UI display."
    )
    unrestricted_by_role: bool = Field(
        False,
        description=(
            "True when the target user's role (admin/superadmin) makes them "
            "unrestricted regardless of ACL rows. UI greys out the editor."
        ),
    )


class RestrictedUserRow(BaseModel):
    """One row of GET /api/auth/users/with-restricted-plugin-access."""
    user_id: str
    email: str
    role: str


class RestrictedUsersListResponse(BaseModel):
    """GET /api/auth/users/with-restricted-plugin-access — users whose
    allowlist is non-empty AND does not include `exclude_slug`.
    """
    users: list[RestrictedUserRow]
