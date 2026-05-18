/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One row in the /settings/maintenance retention table.
 *
 * `rows_total` and `rows_would_prune` are computed live (cached at
 * request time, no caching layer above) so the operator sees an
 * accurate "click 'Run now' and N rows will be deleted" preview.
 */
export type RetentionPolicyState = {
    /**
     * Canonical policy identifier (e.g. 'app_logs', 'job_runs:success').
     */
    key: string;
    /**
     * SQL table the policy prunes.
     */
    table: string;
    /**
     * Timestamp field used for the retention cutoff.
     */
    field: string;
    /**
     * Human-readable summary of what the policy keeps.
     */
    description: string;
    /**
     * Current retention threshold in days. 0 means immediate purge of rows matching `additional_where`.
     */
    retention_days: number;
    /**
     * When true, the cron worker skips this policy. Default for every policy at install.
     */
    paused: boolean;
    /**
     * Current total rows in the policy's scope (bounded by additional_where if any).
     */
    rows_total: number;
    /**
     * Rows that exceed the retention threshold and would be deleted on the next run.
     */
    rows_would_prune: number;
    last_run_at?: (string | null);
    last_run_rows_deleted?: (number | null);
    last_run_error?: (string | null);
    updated_at?: (string | null);
};

