/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/connections/{conn_id}/health-check — probe + persist.
 */
export type ConnectionHealthCheckResponse = {
    /**
     * 'connected' | 'error'.
     */
    status: string;
    detail: string;
    /**
     * ISO-8601 timestamp of the check.
     */
    checked_at: string;
};

