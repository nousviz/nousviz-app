/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One row in the job_alert_subscriptions table joined with the
 * referenced webhook's display info. webhook_name / webhook_url are
 * null when the webhooks plugin is uninstalled (orphan subscription).
 */
export type JobAlertSubscription = {
    id: string;
    /**
     * '*' for any plugin, or a specific plugin slug.
     */
    plugin_id: string;
    /**
     * Terminal statuses this subscription fires on (subset of error/timeout/cancelled).
     */
    on_status: Array<string>;
    webhook_id: string;
    webhook_name?: (string | null);
    webhook_url?: (string | null);
    webhook_active?: boolean;
    /**
     * Channel type of the referenced webhook (generic/slack/discord/teams). Null when the webhooks plugin is uninstalled (orphan subscription).
     */
    webhook_channel_type?: (string | null);
    enabled: boolean;
    updated_at?: (string | null);
};

