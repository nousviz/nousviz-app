/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * B277: a row in the dashboard's NOW section — a currently-running
 * or queued job with elapsed time + collision-prediction context.
 *
 * v0.9.11.16.4 adds heartbeat liveness so callers can distinguish
 * a live worker from an orphaned 'running' row.
 */
export type JobsDashboardNowItem = {
    id: number;
    job_id: string;
    /**
     * 'running' | 'queued' | 'cancelling'.
     */
    status: string;
    started_at: string;
    elapsed_ms: number;
    schedule_cron?: (string | null);
    next_fire_at?: (string | null);
    /**
     * True when elapsed already exceeds (next_fire_at - started_at).
     */
    will_overlap_next?: boolean;
    /**
     * ISO timestamp of the worker's most recent heartbeat write. Null until the row is claimed.
     */
    heartbeat_at?: (string | null);
    /**
     * Seconds since heartbeat_at (server-computed). Null when heartbeat_at is null.
     */
    heartbeat_age_sec?: (number | null);
    /**
     * True iff the worker heartbeated within the last 90s. Force-cancel is gated on this being false for running rows.
     */
    worker_alive?: boolean;
};

