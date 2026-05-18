/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/maintenance/diagnostic-alerts/test.
 */
export type DiagnosticAlertTestResponse = {
    /**
     * Webhooks the synthetic payload reached successfully.
     */
    delivered: number;
    /**
     * Total currently-subscribed webhooks.
     */
    subscribed_webhooks: number;
};

