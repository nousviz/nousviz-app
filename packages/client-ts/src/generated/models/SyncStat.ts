/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type SyncStat = {
    plugin_id: string;
    schedule_cron: string;
    schedule_interval_seconds: number;
    runs_24h: number;
    errors_24h: number;
    avg_duration_ms?: (number | null);
    max_duration_ms?: (number | null);
    /**
     * (avg_duration_ms × runs_24h) / 86_400_000 × 100, capped at 100. % of one CPU continuously consumed by this sync.
     */
    cpu_load_pct_estimate: number;
};

