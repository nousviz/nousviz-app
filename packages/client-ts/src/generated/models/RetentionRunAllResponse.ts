/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/maintenance/retention/run-all response.
 */
export type RetentionRunAllResponse = {
    /**
     * Per-policy outcome. int = rows_deleted; 'paused' = skipped; 'error: <type>' = failed.
     */
    summary: Record<string, (number | string)>;
    duration_ms: number;
};

