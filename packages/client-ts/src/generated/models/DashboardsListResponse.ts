/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardSummary } from './DashboardSummary';
/**
 * GET /api/dashboards — every user-created dashboard, newest-first.
 */
export type DashboardsListResponse = {
    dashboards: Array<DashboardSummary>;
};

