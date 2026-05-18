/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlertRow } from './AlertRow';
/**
 * GET /api/alerts — alert configs, newest-first.
 */
export type AlertsListResponse = {
    alerts: Array<AlertRow>;
    count: number;
};

