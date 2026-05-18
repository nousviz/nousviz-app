/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RestrictedUserRow } from './RestrictedUserRow';
/**
 * GET /api/auth/users/with-restricted-plugin-access — users whose
 * allowlist is non-empty AND does not include `exclude_slug`.
 */
export type RestrictedUsersListResponse = {
    users: Array<RestrictedUserRow>;
};

