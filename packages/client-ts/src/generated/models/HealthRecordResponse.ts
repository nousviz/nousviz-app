/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/health/record — new snapshot persisted.
 */
export type HealthRecordResponse = {
    /**
     * Always 'recorded' on success.
     */
    status?: string;
    /**
     * 'healthy' | 'warning' | 'error'.
     */
    level: string;
    /**
     * Count of checks in this snapshot.
     */
    checks: number;
};

