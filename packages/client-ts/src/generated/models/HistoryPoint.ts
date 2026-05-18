/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One sample in a metric time-series.
 */
export type HistoryPoint = {
    snapshot_at: string;
    /**
     * Metric value at this snapshot. Null when the metric isn't applicable to the snapshot — e.g. a plugin that wasn't yet installed. The UI renders nulls as gaps, not zero.
     */
    value?: (number | null);
};

