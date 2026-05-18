/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Most recent failed run (status IN ('error','timeout','cancelled')).
 */
export type SyncRunFailure = {
    run_id: number;
    completed_at?: (string | null);
    /**
     * 'error' | 'timeout' | 'cancelled'.
     */
    status: string;
    /**
     * Truncated to 500 chars if longer.
     */
    error?: (string | null);
    source?: (string | null);
};

