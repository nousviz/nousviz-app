/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * plugin_update_status block attached to plugin entries (B144).
 */
export type UpdateStatus = {
    /**
     * 'pending' | 'github' | 'community' | 'official' — where the update check looked.
     */
    source_class: string;
    installed_version?: (string | null);
    latest_version?: (string | null);
    update_available?: boolean;
    last_error?: (string | null);
};

