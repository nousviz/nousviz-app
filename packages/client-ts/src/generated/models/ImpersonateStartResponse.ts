/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserSerialized } from './UserSerialized';
/**
 * POST /api/auth/impersonate/{user_id}.
 *
 * NOTE: no `token` field. The caller's existing session token is
 * reused with `acting_as_user_id` set on the session row (B254).
 */
export type ImpersonateStartResponse = {
    acting_as: UserSerialized;
    acting_as_until: string;
};

