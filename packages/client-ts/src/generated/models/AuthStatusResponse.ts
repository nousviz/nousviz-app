/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserSerialized } from './UserSerialized';
/**
 * GET /api/auth/status — public endpoint, returns auth-mode info.
 *
 * Always returned, regardless of whether the caller is authenticated.
 * `user` is null when no valid session token is presented.
 */
export type AuthStatusResponse = {
    authenticated: boolean;
    /**
     * True iff AUTH_REQUIRED=true in .env.
     */
    auth_required: boolean;
    /**
     * True iff at least one user row exists.
     */
    users_exist: boolean;
    user?: (UserSerialized | null);
};

