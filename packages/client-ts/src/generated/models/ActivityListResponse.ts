/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActivityEventRow } from './ActivityEventRow';
/**
 * GET /api/activity — recent events, newest first.
 */
export type ActivityListResponse = {
    events: Array<ActivityEventRow>;
    count: number;
};

