/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlertCreate } from '../models/AlertCreate';
import type { AlertDeleteResponse } from '../models/AlertDeleteResponse';
import type { AlertRow } from '../models/AlertRow';
import type { AlertsListResponse } from '../models/AlertsListResponse';
import type { AlertSourcesResponse } from '../models/AlertSourcesResponse';
import type { AlertSparklineResponse } from '../models/AlertSparklineResponse';
import type { AlertTestResponse } from '../models/AlertTestResponse';
import type { AlertUpdate } from '../models/AlertUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AlertsService {
    /**
     * List alert configs (newest-first, optional plugin/enabled filter)
     * List all alerts, with human-readable frequency and period labels.
     * @returns AlertsListResponse Successful Response
     * @throws ApiError
     */
    public static alertsList({
        pluginId,
        enabledOnly = false,
    }: {
        pluginId?: (string | null),
        enabledOnly?: boolean,
    }): CancelablePromise<AlertsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alerts',
            query: {
                'plugin_id': pluginId,
                'enabled_only': enabledOnly,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create an alert rule
     * Create a new alert.
     * @returns AlertRow Successful Response
     * @throws ApiError
     */
    public static alertsCreate({
        requestBody,
    }: {
        requestBody: AlertCreate,
    }): CancelablePromise<AlertRow> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/alerts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Available data sources for alert configuration (grouped by origin)
     * Return available data sources for alert configuration, grouped by origin:
     * - postgres: Platform tables in the public schema (with columns + row counts)
     * - plugin: Datasets declared in installed plugin manifests
     * - connection: External data sources registered in the connections table
     * @returns AlertSourcesResponse Successful Response
     * @throws ApiError
     */
    public static alertsSources(): CancelablePromise<AlertSourcesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alerts/sources',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.read permission.`,
            },
        });
    }
    /**
     * Patch an alert (partial — null fields skipped)
     * Update an alert (toggle, change threshold, etc.).
     * @returns AlertRow Successful Response
     * @throws ApiError
     */
    public static alertsUpdate({
        alertId,
        requestBody,
    }: {
        alertId: string,
        requestBody: AlertUpdate,
    }): CancelablePromise<AlertRow> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/alerts/{alert_id}',
            path: {
                'alert_id': alertId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Empty body.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.write permission.`,
                404: `Alert not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete an alert
     * Delete a custom alert.
     * @returns AlertDeleteResponse Successful Response
     * @throws ApiError
     */
    public static alertsDelete({
        alertId,
    }: {
        alertId: string,
    }): CancelablePromise<AlertDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/alerts/{alert_id}',
            path: {
                'alert_id': alertId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.write permission.`,
                404: `Alert not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Dry-run an alert against current data
     * Test-run an alert against current data without triggering notifications.
     *
     * Imports the worker's evaluator at request time. If the worker module
     * isn't importable on this server, returns `{error: ...}` instead of
     * a fired/checked breakdown.
     * @returns AlertTestResponse Successful Response
     * @throws ApiError
     */
    public static alertsTest({
        alertId,
    }: {
        alertId: string,
    }): CancelablePromise<AlertTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/alerts/{alert_id}/test',
            path: {
                'alert_id': alertId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.write permission.`,
                404: `Alert not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Per-day trigger counts + semantic-score sparkline
     * Return per-day trigger counts + dominant semantic score for the last N days.
     * @returns AlertSparklineResponse Successful Response
     * @throws ApiError
     */
    public static alertsSparkline({
        alertId,
        days = 30,
    }: {
        alertId: string,
        days?: number,
    }): CancelablePromise<AlertSparklineResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alerts/{alert_id}/sparkline',
            path: {
                'alert_id': alertId,
            },
            query: {
                'days': days,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the alerts.read permission.`,
                404: `Alert not found.`,
                422: `Validation Error`,
            },
        });
    }
}
