/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectionHealthHistoryEntry } from './ConnectionHealthHistoryEntry';
/**
 * GET /api/connections/{conn_id}/health-history — last 20 health checks.
 */
export type ConnectionHealthHistoryResponse = {
    /**
     * Most recent health_status value.
     */
    status?: (string | null);
    last_check?: (string | null);
    /**
     * Newest-first; capped at 20 entries.
     */
    history?: Array<ConnectionHealthHistoryEntry>;
};

