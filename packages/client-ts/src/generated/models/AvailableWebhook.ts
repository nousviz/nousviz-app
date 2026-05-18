/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One outbound webhook surfaced for the job-alert create-form picker.
 */
export type AvailableWebhook = {
    /**
     * webhook_endpoints.id (UUID) — pass as `webhook_id` when creating a subscription.
     */
    id: string;
    name: string;
    url?: (string | null);
    is_active: boolean;
};

