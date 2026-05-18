/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET / PUT /api/auth/users/{user_id}/plugin-access — current
 * allowlist state for the user.
 *
 * `mode='all'` means zero ACL rows (unrestricted). `mode='specific'`
 * means one or more rows; `plugin_ids` lists the slugs the user is
 * allowed to see (utility plugins always pass through regardless).
 */
export type PluginAccessResponse = {
    /**
     * 'all' | 'specific'
     */
    mode: string;
    plugin_ids?: Array<string>;
    /**
     * The target user's current role, for UI display.
     */
    role?: (string | null);
    /**
     * True when the target user's role (admin/superadmin) makes them unrestricted regardless of ACL rows. UI greys out the editor.
     */
    unrestricted_by_role?: boolean;
};

