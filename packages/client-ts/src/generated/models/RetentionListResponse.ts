/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RetentionPolicyState } from './RetentionPolicyState';
/**
 * GET /api/maintenance/retention — every policy + live state.
 */
export type RetentionListResponse = {
    policies: Array<RetentionPolicyState>;
    /**
     * ISO timestamp when this snapshot was assembled.
     */
    collected_at: string;
};

