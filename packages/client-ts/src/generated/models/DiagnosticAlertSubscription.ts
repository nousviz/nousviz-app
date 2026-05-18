/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One outbound webhook + its diagnostic-alert subscription state.
 *
 * v0.9.11.24 (B283) renamed `webhook_slug` → `webhook_id` and added
 * `channel_type`. Existing slug-keyed subscriptions were backfilled
 * by migration 070; the API now exposes the UUID directly.
 */
export type DiagnosticAlertSubscription = {
    /**
     * webhook_endpoints.id (UUID).
     */
    webhook_id: string;
    name: string;
    url?: (string | null);
    is_active: boolean;
    /**
     * Channel type from webhook_endpoints: generic / slack / discord / teams.
     */
    channel_type?: string;
    /**
     * True iff the operator has explicitly subscribed this webhook to diagnostic alerts.
     */
    subscribed: boolean;
    updated_at?: (string | null);
};

