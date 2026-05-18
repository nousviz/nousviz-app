/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InsightsListResponse } from '../models/InsightsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InsightsService {
    /**
     * Aggregate insights across all installed plugins
     * Aggregate insights from all installed plugins (Tier 1 YAML + Tier 2 plugin endpoints).
     *
     * Sorted by severity (critical → warning → info → good → tip) before
     * truncation. `total` is the un-truncated count so the UI can show
     * "20 of 47" pagination hints.
     * @returns InsightsListResponse Successful Response
     * @throws ApiError
     */
    public static insightsList({
        limit = 20,
    }: {
        limit?: number,
    }): CancelablePromise<InsightsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/insights/',
            query: {
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.read permission.`,
                422: `Validation Error`,
            },
        });
    }
}
