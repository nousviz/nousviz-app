/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Per-user audit row in the matrix UI's Users tab.
 */
export type UserWithPermissions = {
    id: string;
    email: string;
    name?: (string | null);
    role?: (string | null);
    is_active: boolean;
    /**
     * Resolved permission set for this user's role.
     */
    permissions?: Array<string>;
    last_activity_at?: (string | null);
    last_activity_route?: (string | null);
};

