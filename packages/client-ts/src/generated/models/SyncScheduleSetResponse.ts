/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/plugins/{id}/sync-schedule — write or clear an override.
 */
export type SyncScheduleSetResponse = {
    saved: boolean;
    /**
     * The newly-stored override, or null when clearing.
     */
    override_cron?: (string | null);
    /**
     * Up to 5 ISO-8601 firing times from now under the new cron.
     */
    preview_next_fires?: Array<string>;
    note?: (string | null);
};

