/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/auth/me/permissions — flat list of permissions for the
 * EFFECTIVE user (target if impersonating, actor otherwise).
 *
 * The permission set is the resolved post-override set as of v0.9.9.x.
 */
export type MyPermissionsResponse = {
    role: string;
    /**
     * Sorted list of permission strings, e.g. ['plugins.install', 'system.logs'].
     */
    permissions: Array<string>;
};

