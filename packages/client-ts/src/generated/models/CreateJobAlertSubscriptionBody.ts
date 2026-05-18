/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/maintenance/job-alerts.
 */
export type CreateJobAlertSubscriptionBody = {
    /**
     * '*' for any plugin, or a specific plugin slug.
     */
    plugin_id: string;
    /**
     * Statuses to alert on. Allowed values: 'error', 'timeout', 'cancelled'.
     */
    on_status: Array<string>;
    /**
     * UUID of an outbound webhook_endpoints row.
     */
    webhook_id: string;
};

