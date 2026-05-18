/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InsightEntry } from './InsightEntry';
/**
 * GET /api/insights — aggregated insights from all installed plugins.
 *
 * Sorted by severity (critical → warning → info → good → tip), then
 * truncated to `limit`. `total` is the un-truncated count.
 */
export type InsightsListResponse = {
    insights: Array<InsightEntry>;
    total: number;
};

