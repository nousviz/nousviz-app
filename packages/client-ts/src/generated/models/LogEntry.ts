/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single app_logs row as returned by /api/admin/logs.
 *
 * `actor_email` and `run_status` are joined in from users / job_runs.
 * `actor_user_id` is the actor's UUID as a string (or null when the
 * log entry has no associated actor — e.g. system-emitted events).
 */
export type LogEntry = {
    id: number;
    /**
     * 'info' | 'warning' | 'error' | etc.
     */
    level: string;
    /**
     * Log source label, e.g. 'plugin', 'plugin_route', 'rbac', 'sync'.
     */
    source: string;
    message: string;
    /**
     * Structured JSONB detail payload — shape depends on the source.
     */
    detail?: (Record<string, any> | null);
    created_at?: (string | null);
    plugin_id?: (string | null);
    actor_user_id?: (string | null);
    run_id?: (number | null);
    actor_email?: (string | null);
    run_status?: (string | null);
};

