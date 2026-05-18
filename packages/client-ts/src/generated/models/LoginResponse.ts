/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserSerialized } from './UserSerialized';
/**
 * POST /api/auth/login response.
 */
export type LoginResponse = {
    /**
     * Raw session token. Send as X-Session-Token on subsequent requests.
     */
    token: string;
    /**
     * ISO-8601 expiry of the session.
     */
    expires_at: string;
    user: UserSerialized;
};

