/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/maintenance/retention/{policy_key}/run response.
 */
export type RetentionRunResponse = {
    policy_key: string;
    rows_deleted: number;
    duration_ms: number;
};

