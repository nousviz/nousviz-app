/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HistoryPoint } from './HistoryPoint';
/**
 * GET /api/system/resources/history?metric=...&days=N.
 */
export type ResourcesHistoryResponse = {
    metric: string;
    plugin?: (string | null);
    days: number;
    points: Array<HistoryPoint>;
};

