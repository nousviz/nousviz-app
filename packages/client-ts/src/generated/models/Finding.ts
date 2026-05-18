/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FindingAction } from './FindingAction';
import type { FindingAffected } from './FindingAffected';
/**
 * One actionable issue surfaced by the diagnostic engine.
 */
export type Finding = {
    /**
     * Stable rule identifier (used for dedup, history lookup).
     */
    id: string;
    severity: Finding.severity;
    /**
     * One-line summary shown collapsed.
     */
    title: string;
    /**
     * 2-4 lines explaining what was measured and why it triggered the rule.
     */
    evidence: string;
    /**
     * Plain-language guidance — what to do about it.
     */
    recommendation: string;
    affected?: Array<FindingAffected>;
    action?: (FindingAction | null);
    detected_at: string;
    /**
     * B274 (v0.9.11.20): ISO timestamp of the most recent webhook alert dispatched for this (finding_id, affected_key). Null when no alert has fired (severity below threshold, or the subscription set is empty). Drives the `alert sent N min ago` badge on the FindingCard.
     */
    last_alerted_at?: (string | null);
};
export namespace Finding {
    export enum severity {
        INFO = 'info',
        WARN = 'warn',
        CRITICAL = 'critical',
    }
}

