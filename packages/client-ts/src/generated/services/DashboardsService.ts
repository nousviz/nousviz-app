/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardCreate } from '../models/DashboardCreate';
import type { DashboardDeleteResponse } from '../models/DashboardDeleteResponse';
import type { DashboardDetail } from '../models/DashboardDetail';
import type { DashboardsListResponse } from '../models/DashboardsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DashboardsService {
    /**
     * List user-created dashboards (no widgets blob)
     * @returns DashboardsListResponse Successful Response
     * @throws ApiError
     */
    public static dashboardsList(): CancelablePromise<DashboardsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/dashboards/',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.read permission.`,
            },
        });
    }
    /**
     * Create a user dashboard
     * @returns DashboardDetail Successful Response
     * @throws ApiError
     */
    public static dashboardsCreate({
        requestBody,
    }: {
        requestBody: DashboardCreate,
    }): CancelablePromise<DashboardDetail> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/dashboards/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a user dashboard with widgets + layout
     * @returns DashboardDetail Successful Response
     * @throws ApiError
     */
    public static dashboardsDetail({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<DashboardDetail> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/dashboards/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.read permission.`,
                404: `Dashboard not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Replace a user dashboard's name/description/widgets/layout/sources
     * @returns DashboardDetail Successful Response
     * @throws ApiError
     */
    public static dashboardsUpdate({
        slug,
        requestBody,
    }: {
        slug: string,
        requestBody: DashboardCreate,
    }): CancelablePromise<DashboardDetail> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/dashboards/{slug}',
            path: {
                'slug': slug,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.write permission.`,
                404: `Dashboard not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a user dashboard
     * @returns DashboardDeleteResponse Successful Response
     * @throws ApiError
     */
    public static dashboardsDelete({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<DashboardDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/dashboards/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the dashboards.write permission.`,
                404: `Dashboard not found.`,
                422: `Validation Error`,
            },
        });
    }
}
