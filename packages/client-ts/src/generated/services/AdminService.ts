/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CliRequest } from '../models/CliRequest';
import type { CliResponse } from '../models/CliResponse';
import type { LogFiltersResponse } from '../models/LogFiltersResponse';
import type { LogsListResponse } from '../models/LogsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminService {
    /**
     * Run a curated admin CLI command
     * @returns CliResponse Successful Response
     * @throws ApiError
     */
    public static adminCli({
        requestBody,
    }: {
        requestBody: CliRequest,
    }): CancelablePromise<CliResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/cli',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the admin.cli permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Paginated app_logs feed with filters
     * Return application logs. Admin only.
     *
     * B208 (v0.9.6.1): supports filtering on the promoted columns
     * (plugin_id, actor_user_id, run_id) plus free-text search and date
     * range. Falls back to detail->>'key' for legacy rows where the
     * promoted column is NULL, so events written before the migration
     * are still discoverable.
     *
     * Pagination: keyset on `id` descending. Pass the response's
     * `next_cursor` back as `cursor` for the next page.
     *
     * B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
     * or full ISO timestamps. Date-only inputs are normalized to start /
     * end of UTC day server-side.
     * @returns LogsListResponse Successful Response
     * @throws ApiError
     */
    public static adminLogsList({
        source,
        level,
        since,
        until,
        pluginId,
        actorUserId,
        runId,
        q,
        cursor,
        limit = 100,
    }: {
        source?: (string | null),
        level?: (string | null),
        since?: (string | null),
        until?: (string | null),
        pluginId?: (string | null),
        actorUserId?: (string | null),
        runId?: (number | null),
        q?: (string | null),
        cursor?: (number | null),
        limit?: number,
    }): CancelablePromise<LogsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/logs',
            query: {
                'source': source,
                'level': level,
                'since': since,
                'until': until,
                'plugin_id': pluginId,
                'actor_user_id': actorUserId,
                'run_id': runId,
                'q': q,
                'cursor': cursor,
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.logs permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Distinct values for the /system/logs filter dropdowns
     * B208 (v0.9.6.1): distinct values for the dropdown filters on
     * /system/logs. Limited to events written in the last 30 days so the
     * dropdowns don't accumulate stale plugin slugs or deleted users.
     *
     * Returns:
     * plugins: list of distinct plugin_id values.
     * users: list of {id, email} tuples for distinct actors.
     * @returns LogFiltersResponse Successful Response
     * @throws ApiError
     */
    public static adminLogsFilters(): CancelablePromise<LogFiltersResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/logs/filters',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.logs permission.`,
            },
        });
    }
}
