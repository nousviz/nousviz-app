/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FindingHistoryPoint } from './FindingHistoryPoint';
/**
 * GET /api/system/diagnostics/history?id=...&days=N.
 */
export type DiagnosticsHistoryResponse = {
    finding_id: string;
    days: number;
    points: Array<FindingHistoryPoint>;
    /**
     * Earliest snapshot in the queried window where the finding was present. Null when the finding has never been present in the queried window.
     */
    first_detected_at?: (string | null);
};

