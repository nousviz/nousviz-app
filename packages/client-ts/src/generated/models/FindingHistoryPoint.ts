/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One sample in a finding presence time-series.
 */
export type FindingHistoryPoint = {
    snapshot_at: string;
    present: boolean;
    /**
     * Severity at this snapshot. Null when present=false.
     */
    severity?: (string | null);
};

