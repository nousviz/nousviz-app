/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LaunchpadResponse } from '../models/LaunchpadResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LaunchpadService {
    /**
     * Single-call aggregate data feed for the Overview page
     * Single-call data feed for the Overview page.
     *
     * Each block is fetched in its own savepoint — failures roll back
     * that block only and leave the rest of the response intact. The
     * frontend receives partial data rather than a 500 when one of the
     * underlying queries hits a missing table or stale schema.
     *
     * Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
     * so the cache absorbs back-to-back requests without staleness anyone
     * notices.
     * @returns LaunchpadResponse Successful Response
     * @throws ApiError
     */
    public static launchpadFeed(): CancelablePromise<LaunchpadResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/launchpad',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.read permission.`,
            },
        });
    }
}
