/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * B277 (v0.9.11.16.1): a job with ANY errors in the last 24h.
 *
 * Threshold widened from > 50% error rate to errors > 0 per operator
 * UX feedback: sporadic failures matter and should surface for
 * investigation. Ordered server-side by `last_error_at` DESC so the
 * frontend can lead with the most recent failure.
 */
export type JobsDashboardFailingItem = {
    job_id: string;
    runs_24h: number;
    errors_24h: number;
    error_rate_pct: number;
    last_error?: (string | null);
    /**
     * ISO timestamp of the most recent error — anchors the deep-link into /system/logs.
     */
    last_error_at?: (string | null);
};

