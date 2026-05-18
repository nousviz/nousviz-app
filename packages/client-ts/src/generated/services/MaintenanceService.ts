/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AvailableWebhooksResponse } from '../models/AvailableWebhooksResponse';
import type { CreateJobAlertSubscriptionBody } from '../models/CreateJobAlertSubscriptionBody';
import type { DiagnosticAlertSubscription } from '../models/DiagnosticAlertSubscription';
import type { DiagnosticAlertSubscriptionListResponse } from '../models/DiagnosticAlertSubscriptionListResponse';
import type { DiagnosticAlertTestResponse } from '../models/DiagnosticAlertTestResponse';
import type { JobAlertSubscription } from '../models/JobAlertSubscription';
import type { JobAlertSubscriptionListResponse } from '../models/JobAlertSubscriptionListResponse';
import type { JobAlertTestResponse } from '../models/JobAlertTestResponse';
import type { RetentionListResponse } from '../models/RetentionListResponse';
import type { RetentionPolicyState } from '../models/RetentionPolicyState';
import type { RetentionRunAllResponse } from '../models/RetentionRunAllResponse';
import type { RetentionRunResponse } from '../models/RetentionRunResponse';
import type { UpdateDiagnosticAlertSubscriptionBody } from '../models/UpdateDiagnosticAlertSubscriptionBody';
import type { UpdateJobAlertSubscriptionBody } from '../models/UpdateJobAlertSubscriptionBody';
import type { UpdateRetentionPolicyBody } from '../models/UpdateRetentionPolicyBody';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MaintenanceService {
    /**
     * List retention policies with live row counts and last-run state
     * Return every retention policy registered in the POLICIES code
     * constant, joined with the operator-tuned overrides + live counts.
     *
     * Each policy ships paused; first deploy is a no-op. Operator flips
     * each on from `/settings/maintenance` after reviewing the
     * `rows_would_prune` preview.
     * @returns RetentionListResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceRetentionList(): CancelablePromise<RetentionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/maintenance/retention',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * Update a retention policy (threshold or paused flag)
     * Update one or both editable fields on a retention policy. Audit-
     * logged with the operator's user_id.
     * @returns RetentionPolicyState Successful Response
     * @throws ApiError
     */
    public static maintenanceRetentionUpdate({
        policyKey,
        requestBody,
    }: {
        policyKey: string,
        requestBody: UpdateRetentionPolicyBody,
    }): CancelablePromise<RetentionPolicyState> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/maintenance/retention/{policy_key}',
            path: {
                'policy_key': policyKey,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Policy key not registered.`,
                422: `Invalid retention_days (must be 0-3650).`,
            },
        });
    }
    /**
     * Run a retention policy now (force; bypasses paused state)
     * Run one policy immediately. Bypasses the paused flag (the
     * operator just clicked "Run now" — that's their consent). Audit-
     * logged with the operator's user_id.
     * @returns RetentionRunResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceRetentionRun({
        policyKey,
    }: {
        policyKey: string,
    }): CancelablePromise<RetentionRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/maintenance/retention/{policy_key}/run',
            path: {
                'policy_key': policyKey,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Policy key not registered.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run every UNPAUSED retention policy now
     * Run every currently-unpaused policy. Paused policies are
     * skipped; failed policies are reported per-key. Audit-logged.
     * @returns RetentionRunAllResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceRetentionRunAll(): CancelablePromise<RetentionRunAllResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/maintenance/retention/run-all',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * List outbound webhooks + their diagnostic-alert subscription state (B274)
     * Return every outbound webhook from `webhook_endpoints` (the
     * webhooks plugin's table) along with whether it's subscribed to
     * receive diagnostic alerts.
     *
     * Empty list when the webhooks plugin isn't installed — operator
     * sees no rows and gets no toggle, no error.
     * @returns DiagnosticAlertSubscriptionListResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceDiagnosticAlertsListSubscriptions(): CancelablePromise<DiagnosticAlertSubscriptionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/maintenance/diagnostic-alerts/subscriptions',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * Subscribe or unsubscribe a webhook from diagnostic alerts (B274)
     * Toggle subscription for one outbound webhook. Audit-logged with
     * the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID.
     * @returns DiagnosticAlertSubscription Successful Response
     * @throws ApiError
     */
    public static maintenanceDiagnosticAlertsUpdateSubscription({
        webhookId,
        requestBody,
    }: {
        webhookId: string,
        requestBody: UpdateDiagnosticAlertSubscriptionBody,
    }): CancelablePromise<DiagnosticAlertSubscription> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/maintenance/diagnostic-alerts/subscriptions/{webhook_id}',
            path: {
                'webhook_id': webhookId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Webhook id not registered.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Fire a synthetic test alert to every subscribed webhook (B274)
     * Send a fake critical finding to every webhook with an active
     * subscription. Useful for one-click verification after configuring
     * a new webhook.
     * @returns DiagnosticAlertTestResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceDiagnosticAlertsTest(): CancelablePromise<DiagnosticAlertTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/maintenance/diagnostic-alerts/test',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * List per-job-run failure alert subscriptions (B284)
     * Every subscription joined with the referenced webhook's display
     * info (name, url, is_active). webhook_name/url null when the
     * webhooks plugin is uninstalled (orphan subscriptions render with
     * a "webhook missing" indicator in the UI).
     * @returns JobAlertSubscriptionListResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsList(): CancelablePromise<JobAlertSubscriptionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/maintenance/job-alerts',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * Create a per-job-run failure alert subscription (B284)
     * @returns JobAlertSubscription Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsCreate({
        requestBody,
    }: {
        requestBody: CreateJobAlertSubscriptionBody,
    }): CancelablePromise<JobAlertSubscription> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/maintenance/job-alerts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid plugin_id, on_status, or webhook_id.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Webhook id not registered.`,
                409: `Subscription already exists for (plugin_id, webhook_id).`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List outbound webhooks available for job-alert subscriptions (B284)
     * Picker source for the create-subscription form: every outbound
     * webhook in webhook_endpoints with its UUID. Empty list when the
     * webhooks plugin isn't installed.
     * @returns AvailableWebhooksResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsListAvailableWebhooks(): CancelablePromise<AvailableWebhooksResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/maintenance/job-alerts/webhooks',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
            },
        });
    }
    /**
     * Update a job-alert subscription (toggle enabled / change on_status) (B284)
     * @returns JobAlertSubscription Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsUpdate({
        subId,
        requestBody,
    }: {
        subId: string,
        requestBody: UpdateJobAlertSubscriptionBody,
    }): CancelablePromise<JobAlertSubscription> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/maintenance/job-alerts/{sub_id}',
            path: {
                'sub_id': subId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid on_status.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Subscription not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a job-alert subscription (B284)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsDelete({
        subId,
    }: {
        subId: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/maintenance/job-alerts/{sub_id}',
            path: {
                'sub_id': subId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Subscription not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Fire a synthetic test alert to a subscription's webhook (B284)
     * @returns JobAlertTestResponse Successful Response
     * @throws ApiError
     */
    public static maintenanceJobAlertsTest({
        subId,
    }: {
        subId: string,
    }): CancelablePromise<JobAlertTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/maintenance/job-alerts/{sub_id}/test',
            path: {
                'sub_id': subId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                404: `Subscription not found.`,
                422: `Validation Error`,
            },
        });
    }
}
