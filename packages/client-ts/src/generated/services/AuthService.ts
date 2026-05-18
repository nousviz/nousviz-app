/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AcceptInviteRequest } from '../models/AcceptInviteRequest';
import type { ApiKeyCreateResponse } from '../models/ApiKeyCreateResponse';
import type { AuthActivityResponse } from '../models/AuthActivityResponse';
import type { AuthStatusResponse } from '../models/AuthStatusResponse';
import type { AvatarResponse } from '../models/AvatarResponse';
import type { DeactivateUserResponse } from '../models/DeactivateUserResponse';
import type { ForgotPasswordRequest } from '../models/ForgotPasswordRequest';
import type { GenericMessageResponse } from '../models/GenericMessageResponse';
import type { ImpersonateExitResponse } from '../models/ImpersonateExitResponse';
import type { ImpersonateStartResponse } from '../models/ImpersonateStartResponse';
import type { InviteCreateResponse } from '../models/InviteCreateResponse';
import type { InviteRequest } from '../models/InviteRequest';
import type { InviteRevokeResponse } from '../models/InviteRevokeResponse';
import type { InvitesListResponse } from '../models/InvitesListResponse';
import type { LoginRequest } from '../models/LoginRequest';
import type { LoginResponse } from '../models/LoginResponse';
import type { LogoutResponse } from '../models/LogoutResponse';
import type { MeResponse } from '../models/MeResponse';
import type { MyPermissionsResponse } from '../models/MyPermissionsResponse';
import type { PluginAccessPayload } from '../models/PluginAccessPayload';
import type { PluginAccessResponse } from '../models/PluginAccessResponse';
import type { ProfileUpdate } from '../models/ProfileUpdate';
import type { RegisterRequest } from '../models/RegisterRequest';
import type { ResetPasswordRequest } from '../models/ResetPasswordRequest';
import type { RestrictedUsersListResponse } from '../models/RestrictedUsersListResponse';
import type { RolePermissionsResponse } from '../models/RolePermissionsResponse';
import type { SetupConfigRequest } from '../models/SetupConfigRequest';
import type { SetupOkResponse } from '../models/SetupOkResponse';
import type { SetupRequest } from '../models/SetupRequest';
import type { SetupResponse } from '../models/SetupResponse';
import type { StepUpRequest } from '../models/StepUpRequest';
import type { StepUpResponse } from '../models/StepUpResponse';
import type { UserSerialized } from '../models/UserSerialized';
import type { UsersListResponse } from '../models/UsersListResponse';
import type { UserUpdate } from '../models/UserUpdate';
import type { VerifyResponse } from '../models/VerifyResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Auth-mode and current-session status
     * Return auth-mode flags and (if a session token is present and
     * valid) the authenticated user.
     *
     * Public endpoint — no auth required. The frontend calls this on
     * page load to decide whether to show the login screen, the setup
     * wizard (no users exist), or the dashboard.
     * @returns AuthStatusResponse Successful Response
     * @throws ApiError
     */
    public static authStatus(): CancelablePromise<AuthStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/status',
        });
    }
    /**
     * Register a new account (first user = superadmin; later users via invite)
     * @returns LoginResponse Successful Response
     * @throws ApiError
     */
    public static authRegister({
        requestBody,
    }: {
        requestBody: RegisterRequest,
    }): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid password or email/invite mismatch.`,
                403: `Registration requires an invite.`,
                409: `Email already exists.`,
                410: `Invite invalid or expired.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Issue a session token for valid credentials
     * Authenticate and return a session token. Rate-limited per source IP.
     * @returns LoginResponse Successful Response
     * @throws ApiError
     */
    public static authLogin({
        requestBody,
    }: {
        requestBody: LoginRequest,
    }): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/login',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Email is required.`,
                401: `Invalid email or password.`,
                422: `Validation Error`,
                429: `Rate-limited — too many login attempts.`,
            },
        });
    }
    /**
     * Accept an invite link and create the account
     * @returns LoginResponse Successful Response
     * @throws ApiError
     */
    public static authAcceptInvite({
        requestBody,
    }: {
        requestBody: AcceptInviteRequest,
    }): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/accept-invite',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid password or email mismatch.`,
                409: `Email already exists — try logging in.`,
                410: `Invite invalid or expired.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Initiate password reset (enumeration-resistant)
     * Public endpoint — initiate a password reset.
     *
     * Always returns 200 with the same body regardless of whether the
     * email exists, matches a real user, or the email send actually
     * succeeded. This prevents user-enumeration via response timing or
     * response shape.
     * @returns GenericMessageResponse Successful Response
     * @throws ApiError
     */
    public static authForgotPassword({
        requestBody,
    }: {
        requestBody: ForgotPasswordRequest,
    }): CancelablePromise<GenericMessageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/forgot-password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
                429: `Rate-limited — too many resets for this email.`,
            },
        });
    }
    /**
     * Consume a reset token + set new password
     * Public endpoint — consume a password reset token.
     *
     * Validates the token, hashes the new password, updates the user row,
     * marks the token used, kills all sessions for the user.
     *
     * Returns:
     * 200 {ok: true} on success
     * 400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
     * 400 if password too short
     * @returns GenericMessageResponse Successful Response
     * @throws ApiError
     */
    public static authResetPassword({
        requestBody,
    }: {
        requestBody: ResetPasswordRequest,
    }): CancelablePromise<GenericMessageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/reset-password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Token invalid/used/expired (structured detail) or password too short.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Expire the current session
     * Expire the session associated with the X-Session-Token header.
     *
     * Idempotent — returns `{ok: true}` whether or not a valid token was
     * presented. Public endpoint.
     * @returns LogoutResponse Successful Response
     * @throws ApiError
     */
    public static authLogout(): CancelablePromise<LogoutResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/logout',
        });
    }
    /**
     * Re-authenticate for sensitive operations (B236)
     * Re-authenticate the current session for sensitive operations.
     *
     * Returns 200 with `step_up_until` on correct password, sets
     * user_sessions.step_up_until to now() + 5 minutes for the active session.
     *
     * Wrong password returns 401 with the same error shape as /login. Subject
     * to the same per-IP rate limit as /login (5 attempts / 60s).
     *
     * Requires an active session — returns 401 if no valid token.
     * @returns StepUpResponse Successful Response
     * @throws ApiError
     */
    public static authStepUp({
        requestBody,
    }: {
        requestBody: StepUpRequest,
    }): CancelablePromise<StepUpResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/step-up',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Not authenticated, or wrong password.`,
                422: `Validation Error`,
                429: `Rate-limited (5 attempts / 60s per IP).`,
            },
        });
    }
    /**
     * End impersonation by clearing session flags (B254 — no re-login)
     * End the current impersonation by clearing flags on the caller's session.
     *
     * B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
     * killed the impersonation session row. The session row is now the
     * actor's existing session (with transient acting_as_* flags); exit
     * just clears the flags. The session token, expires_at, and metadata
     * all remain unchanged — actor stays logged in as themselves with no
     * re-login needed.
     *
     * Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
     * first-match-wins resolution picks this for `/impersonate/exit`
     * rather than treating "exit" as a user_id parameter.
     *
     * Idempotent: returns 200 with `wasImpersonating: false` if the
     * current session isn't impersonating.
     *
     * No step-up requirement — anyone holding the session may leave the
     * impersonation. Step-up is required to ENTER impersonation, not exit.
     * @returns ImpersonateExitResponse Successful Response
     * @throws ApiError
     */
    public static authImpersonateExit(): CancelablePromise<ImpersonateExitResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/impersonate/exit',
        });
    }
    /**
     * Start impersonating a user (B254 — sets session flag, no token swap)
     * Start impersonating another user — by setting flags on the
     * caller's existing session, NOT by issuing a new session token.
     *
     * B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
     * INSERTed a new short-lived session row and returned a new token.
     * Now updates the caller's session with `acting_as_user_id` and
     * `acting_as_until`. The caller's token is unchanged. On exit (or
     * auto-expire), the flags clear and the caller is back as themselves
     * without re-login.
     *
     * Requirements:
     * - Caller has users.manage (gated by Depends-style routing — see register_route above)
     * - Caller has stepped up within the last STEP_UP_TTL_MINUTES
     * - Caller's role rank > target's role rank (strict)
     * - Target user exists and is active
     * - Caller cannot already be impersonating (must exit first)
     *
     * Returns:
     * - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
     * Note: NO `token` field in the response. Caller's existing token
     * continues to work; the next /api/auth/me will show the new
     * `acting_as` field.
     * - 401 if not stepped up.
     * - 403 with `{error: 'rank_violation'}` if rank check fails.
     * - 404 if target not found.
     * - 409 if already impersonating.
     * @returns ImpersonateStartResponse Successful Response
     * @throws ApiError
     */
    public static authImpersonateStart({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<ImpersonateStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/impersonate/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Not authenticated or step-up required.`,
                403: `Rank violation (actor's role rank not strictly greater than target's).`,
                404: `Target user not found or not active.`,
                409: `Caller is already impersonating — must exit first.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Introspect a session token (public)
     * Introspect a session token via the `?token=` query parameter.
     *
     * Public endpoint — does not require X-Session-Token. Returns
     * `{valid: false}` for any invalid, expired, or missing token.
     * Used by share-link landing pages and embed contexts to test
     * whether a token is still good without consuming it.
     * @returns VerifyResponse Successful Response
     * @throws ApiError
     */
    public static authVerify({
        token,
    }: {
        token: string,
    }): CancelablePromise<VerifyResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/verify',
            query: {
                'token': token,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Current actor (with optional acting_as target)
     * Public `GET /api/auth/me` endpoint — Option B identity shape.
     *
     * B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
     * to the session) as the primary identity. When the session is
     * impersonating, the response also carries an `acting_as` field with
     * the target's serialized identity.
     *
     * Frontend reads `me` for actor identity (audit, "Exit impersonation"
     * banner, log-out button) and `me.acting_as` for effective identity
     * (permission checks, role display). The `useEffectiveIdentity()` hook
     * centralizes the choice for permission/UI display.
     * @returns MeResponse Successful Response
     * @throws ApiError
     */
    public static authMe(): CancelablePromise<MeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/me',
            errors: {
                401: `Missing or invalid session token.`,
            },
        });
    }
    /**
     * Update own profile (password change requires step-up — B251)
     * Update the current user's profile.
     *
     * B251 (v0.9.10.0.3): when the request includes the password field,
     * requires recent step-up auth (same gate as RBAC writes from B236).
     * Without this, a stolen session token could change the password and
     * lock the real owner out. Other fields (name, etc.) remain step-up-
     * free — they're not security-sensitive.
     * @returns UserSerialized Successful Response
     * @throws ApiError
     */
    public static authMeUpdate({
        requestBody,
    }: {
        requestBody: ProfileUpdate,
    }): CancelablePromise<UserSerialized> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/auth/me',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Password too short or empty body.`,
                401: `Step-up auth required for password change.`,
                403: `Caller lacks the users.read_self permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Resolved permissions for the current effective user
     * B230 (v0.9.8.3): return the set of permissions the current user
     * holds. The frontend uses this for role-aware UI (sidebar nav,
     * conditional buttons) without needing to duplicate the role-permission
     * catalog from rbac/permissions.py.
     *
     * Resolves the user, looks up their role's permission set, and returns
     * a flat list. v0.9.9.x will layer DB overrides on top — this same
     * endpoint will return the resolved post-override set, so the frontend
     * contract doesn't change.
     * @returns MyPermissionsResponse Successful Response
     * @throws ApiError
     */
    public static authMePermissions(): CancelablePromise<MyPermissionsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/me/permissions',
            errors: {
                401: `Missing or invalid session token.`,
            },
        });
    }
    /**
     * Permissions held by an arbitrary role (admin preview UI)
     * B231 (v0.9.8.4): return the permissions held by an arbitrary role.
     *
     * Powers the admin-only "preview as <role>" UI — admins toggle the
     * sidebar to render as if they had a different role, and the frontend
     * needs the permission set for that role to compute hasPermission().
     *
     * Frontend-only feature: the backend still authorizes the request
     * based on the admin's REAL session. This endpoint is gated by
     * system.audit so a non-admin can't fish for role permissions.
     *
     * Returns 404 if the role is unknown (typo, future custom role).
     * @returns RolePermissionsResponse Successful Response
     * @throws ApiError
     */
    public static authRolePermissions({
        role,
    }: {
        role: string,
    }): CancelablePromise<RolePermissionsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/role-permissions/{role}',
            path: {
                'role': role,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Unknown role.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload avatar image (multipart; max 2 MB; jpg/png/webp/gif)
     * @returns AvatarResponse Successful Response
     * @throws ApiError
     */
    public static authMeAvatarUpload(): CancelablePromise<AvatarResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/me/avatar',
            errors: {
                400: `Bad multipart, file too large, or unsupported MIME type.`,
                401: `Missing or invalid session token.`,
            },
        });
    }
    /**
     * Delete avatar image (returns avatar_url=null)
     * @returns AvatarResponse Successful Response
     * @throws ApiError
     */
    public static authMeAvatarDelete(): CancelablePromise<AvatarResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/auth/me/avatar',
            errors: {
                401: `Missing or invalid session token.`,
            },
        });
    }
    /**
     * List all users (admin)
     * @returns UsersListResponse Successful Response
     * @throws ApiError
     */
    public static authUsersList(): CancelablePromise<UsersListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
            },
        });
    }
    /**
     * Update a user's name/role/active flag (admin)
     * @returns UserSerialized Successful Response
     * @throws ApiError
     */
    public static authUsersUpdate({
        userId,
        requestBody,
    }: {
        userId: string,
        requestBody: UserUpdate,
    }): CancelablePromise<UserSerialized> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/auth/users/{user_id}',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Empty body or invalid role.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks rights to edit this user.`,
                404: `User not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Deactivate a user (soft — sets is_active=false)
     * @returns DeactivateUserResponse Successful Response
     * @throws ApiError
     */
    public static authUsersDeactivate({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<DeactivateUserResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/auth/users/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                400: `Cannot deactivate own account.`,
                401: `Missing or invalid session token.`,
                403: `Only superadmin can delete another superadmin.`,
                404: `User not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reactivate a deactivated user
     * @returns UserSerialized Successful Response
     * @throws ApiError
     */
    public static authUsersReactivate({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<UserSerialized> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/users/{user_id}/reactivate',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                404: `User not found or already active.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Promote an admin to superadmin (superadmin only)
     * @returns UserSerialized Successful Response
     * @throws ApiError
     */
    public static authUsersPromote({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<UserSerialized> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/users/{user_id}/promote',
            path: {
                'user_id': userId,
            },
            errors: {
                400: `User not found or is not an admin.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage_admins permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Demote a superadmin to admin (DB trigger blocks zero superadmins)
     * @returns UserSerialized Successful Response
     * @throws ApiError
     */
    public static authUsersDemote({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<UserSerialized> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/users/{user_id}/demote',
            path: {
                'user_id': userId,
            },
            errors: {
                400: `User not found or not a superadmin, or only-superadmin guard fired.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage_admins permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)
     * Used by the install-success grant banner on the frontend. Returns
     * users with `mode='specific'` whose allowlist does NOT include
     * `exclude_slug` — i.e. the operator-visible "people who can't see
     * this new plugin yet" set.
     * @returns RestrictedUsersListResponse Successful Response
     * @throws ApiError
     */
    public static authUsersWithRestrictedPluginAccess({
        excludeSlug = '',
    }: {
        excludeSlug?: string,
    }): CancelablePromise<RestrictedUsersListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users/with-restricted-plugin-access',
            query: {
                'exclude_slug': excludeSlug,
            },
            errors: {
                400: `Missing exclude_slug query parameter.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a user's plugin-visibility allowlist (admin)
     * @returns PluginAccessResponse Successful Response
     * @throws ApiError
     */
    public static authUsersPluginAccessGet({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<PluginAccessResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users/{user_id}/plugin-access',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                404: `User not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Replace a user's plugin-visibility allowlist (admin)
     * @returns PluginAccessResponse Successful Response
     * @throws ApiError
     */
    public static authUsersPluginAccessSet({
        userId,
        requestBody,
    }: {
        userId: string,
        requestBody: PluginAccessPayload,
    }): CancelablePromise<PluginAccessResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/auth/users/{user_id}/plugin-access',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid payload shape or unknown plugin slug.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                404: `User not found.`,
                409: `Target user has an admin/superadmin role — unrestricted by design.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Invite a user via email (admin)
     * @returns InviteCreateResponse Successful Response
     * @throws ApiError
     */
    public static authUsersInviteCreate({
        requestBody,
    }: {
        requestBody: InviteRequest,
    }): CancelablePromise<InviteCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/users/invite',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid role for invites.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                409: `Email already has a user account.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List recent invites (admin)
     * @returns InvitesListResponse Successful Response
     * @throws ApiError
     */
    public static authUsersInvitesList(): CancelablePromise<InvitesListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users/invites',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
            },
        });
    }
    /**
     * Revoke an unused invite
     * @returns InviteRevokeResponse Successful Response
     * @throws ApiError
     */
    public static authUsersInviteRevoke({
        inviteId,
    }: {
        inviteId: string,
    }): CancelablePromise<InviteRevokeResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/auth/users/invite/{invite_id}',
            path: {
                'invite_id': inviteId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                404: `Invite not found or already used.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate an API key for a user (raw key shown once)
     * @returns ApiKeyCreateResponse Successful Response
     * @throws ApiError
     */
    public static authUsersApiKeyCreate({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<ApiKeyCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/users/{user_id}/api-key',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the users.manage permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Auth activity log (admin audit)
     * @returns AuthActivityResponse Successful Response
     * @throws ApiError
     */
    public static authActivity({
        limit = 50,
    }: {
        limit?: number,
    }): CancelablePromise<AuthActivityResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/activity',
            query: {
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * First-run wizard: write security-config to .env
     * @returns SetupOkResponse Successful Response
     * @throws ApiError
     */
    public static authSetupConfig({
        requestBody,
    }: {
        requestBody: SetupConfigRequest,
    }): CancelablePromise<SetupOkResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/setup/config',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Postgres-password ALTER failed.`,
                403: `Already configured.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Legacy first-admin creation (pre-P58, kept for backward compat)
     * @returns SetupResponse Successful Response
     * @throws ApiError
     */
    public static authSetup({
        requestBody,
    }: {
        requestBody: SetupRequest,
    }): CancelablePromise<SetupResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/setup',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Oauth Callback
     * Public OAuth-provider redirect target. See module docstring.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static oauthCallbackApiOauthCallbackPluginSlugGet({
        pluginSlug,
    }: {
        pluginSlug: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/oauth/callback/{plugin_slug}',
            path: {
                'plugin_slug': pluginSlug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
