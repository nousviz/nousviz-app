/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Cached plugin update status for one plugin (B144).
 */
export type PluginUpdateInfo = {
    plugin_id: string;
    /**
     * 'first_party' | 'github' | 'pending' — origin of the update check.
     */
    source_class: string;
    source_url?: (string | null);
    installed_version?: (string | null);
    latest_version?: (string | null);
    update_available?: boolean;
    last_error?: (string | null);
};

