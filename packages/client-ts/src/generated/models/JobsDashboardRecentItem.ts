/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * B277: a completed job_runs row from the recent-history window.
 */
export type JobsDashboardRecentItem = {
    id: number;
    job_id: string;
    status: string;
    started_at: string;
    completed_at?: (string | null);
    duration_ms?: (number | null);
    /**
     * First 200 chars of the run's error column, or null.
     */
    error_short?: (string | null);
};

