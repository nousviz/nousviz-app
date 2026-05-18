/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Per-day cell in the sparkline.
 */
export type AlertSparklineDay = {
    date: string;
    count: number;
    /**
     * Dominant semantic score for the day: 'useful' | 'neutral' | 'useless'.
     */
    score?: (string | null);
};

