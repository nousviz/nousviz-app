/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActivityEvent } from '../models/ActivityEvent';
import type { ActivityListResponse } from '../models/ActivityListResponse';
import type { ActivityLogResponse } from '../models/ActivityLogResponse';
import type { DashboardUsageResponse } from '../models/DashboardUsageResponse';
import type { UserAnalyticsResponse } from '../models/UserAnalyticsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ActivityService {
    /**
     * Record a user activity event
     * Record a user activity event with device and IP metadata.
     *
     * Open to any authenticated user (POST-only — they can log their own
     * activity but can't read the firehose).
     * @returns ActivityLogResponse Successful Response
     * @throws ApiError
     */
    public static activityLog({
        requestBody,
    }: {
        requestBody: ActivityEvent,
    }): CancelablePromise<ActivityLogResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/activity',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List recent activity events (admin-only firehose)
     * List recent activity. Newest-first, optional filters on action /
     * plugin_id / page_path.
     * @returns ActivityListResponse Successful Response
     * @throws ApiError
     */
    public static activityList({
        action,
        pluginId,
        pagePath,
        limit = 50,
    }: {
        action?: (string | null),
        pluginId?: (string | null),
        pagePath?: (string | null),
        limit?: number,
    }): CancelablePromise<ActivityListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/activity',
            query: {
                'action': action,
                'plugin_id': pluginId,
                'page_path': pagePath,
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Per-page and per-plugin usage analytics
     * Analytics: which dashboards are being used?
     *
     * Aggregates page_view events into per-page + per-plugin counts plus
     * a daily-activity histogram. `unused_dashboards` enumerates manifest-
     * declared dashboard paths that received zero views in the period.
     * @returns DashboardUsageResponse Successful Response
     * @throws ApiError
     */
    public static activityDashboardUsage({
        days = 30,
    }: {
        days?: number,
    }): CancelablePromise<DashboardUsageResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/activity/dashboard-usage',
            query: {
                'days': days,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Admin analytics: time, devices, IPs, sessions
     * Admin analytics: time spent, devices, IPs, sessions, and usage patterns.
     *
     * Time-spent is a heuristic — sums gaps between consecutive page_view
     * events, capped at 30 minutes per gap so an idle tab doesn't inflate
     * the total. Sessions are runs of page_views separated by gaps >= 30 min.
     * @returns UserAnalyticsResponse Successful Response
     * @throws ApiError
     */
    public static activityAnalytics({
        days = 30,
    }: {
        days?: number,
    }): CancelablePromise<UserAnalyticsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/activity/analytics',
            query: {
                'days': days,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                422: `Validation Error`,
            },
        });
    }
}
