/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthLogRow } from './HealthLogRow';
/**
 * GET /api/health/log — recent health-check snapshots, newest-first.
 */
export type HealthLogResponse = {
    log: Array<HealthLogRow>;
    count: number;
};

