/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * sync_schedule_registry row — what the scheduler is actively tracking.
 */
export type SyncScheduleRegistry = {
    cron_expression?: (string | null);
    /**
     * 'manifest' | 'override'.
     */
    cron_source?: (string | null);
    next_fire_at?: (string | null);
    last_enqueued_at?: (string | null);
    last_run_id?: (number | null);
    last_error?: (string | null);
    updated_at?: (string | null);
};

