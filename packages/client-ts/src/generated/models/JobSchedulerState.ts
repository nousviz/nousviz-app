/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * sync_schedule_registry row attached to plugin sync jobs (B150).
 *
 * Surfaced under JobEntry.scheduler — tells the operator UI whether
 * the v0.9.3 scheduler is actively tracking this plugin and when it
 * last enqueued a run.
 */
export type JobSchedulerState = {
    cron_expression?: (string | null);
    /**
     * 'manifest' | 'override'.
     */
    cron_source?: (string | null);
    next_fire_at?: (string | null);
    last_enqueued_at?: (string | null);
    last_run_id?: (number | null);
    last_error?: (string | null);
    /**
     * Seconds since the registry row was last touched. <300 means scheduler is alive.
     */
    age_sec?: (number | null);
};

