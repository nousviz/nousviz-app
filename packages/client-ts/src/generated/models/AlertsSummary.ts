/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Aggregate alert counts surfaced in the launchpad block.
 */
export type AlertsSummary = {
    total?: number;
    enabled?: number;
    triggered_24h?: number;
    /**
     * Recent alert_events rows; row shape varies by alert type.
     */
    recent_triggers?: Array<Record<string, any>>;
};

