/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * In-flight sync run — populated when status IN ('queued','running','cancelling').
 */
export type SyncRunCurrent = {
    run_id: number;
    status: string;
    /**
     * Who triggered this run (manual/scheduler/api).
     */
    source?: (string | null);
    started_at?: (string | null);
    heartbeat_at?: (string | null);
    /**
     * Live progress payload from the worker — shape is plugin-defined.
     */
    progress?: Record<string, any>;
    elapsed_sec: number;
};

