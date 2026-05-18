/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DataportPluginConfigResponse } from '../models/DataportPluginConfigResponse';
import type { DataportPluginsListResponse } from '../models/DataportPluginsListResponse';
import type { DataportTabRowsResponse } from '../models/DataportTabRowsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DataPortService {
    /**
     * Installed plugins that ship dataport.yaml
     * List all installed plugins that have a dataport.yaml.
     * @returns DataportPluginsListResponse Successful Response
     * @throws ApiError
     */
    public static dataPortPluginsList(): CancelablePromise<DataportPluginsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/data-port/plugins',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
            },
        });
    }
    /**
     * Full dataport.yaml config for a plugin (verbatim)
     * Return the full dataport.yaml config for a plugin.
     *
     * Schema is plugin-author-defined; we return it verbatim and let
     * the frontend render whatever the plugin declared.
     * @returns DataportPluginConfigResponse Successful Response
     * @throws ApiError
     */
    public static dataPortPluginConfig({
        pluginSlug,
    }: {
        pluginSlug: string,
    }): CancelablePromise<DataportPluginConfigResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/data-port/plugins/{plugin_slug}',
            path: {
                'plugin_slug': pluginSlug,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
                404: `Plugin has no dataport.yaml.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Paginated rows from a dataport tab's declared table
     * Query a plugin's dataport tab directly from its declared table.
     *
     * Sort/filter validation: column names and filter keys must appear in
     * the plugin's `dataport.yaml`; any other keys are silently dropped.
     * Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
     * on every column reference (S106).
     * @returns DataportTabRowsResponse Successful Response
     * @throws ApiError
     */
    public static dataPortTabRows({
        pluginSlug,
        tabId,
        page = 1,
        pageSize = 50,
        sort,
    }: {
        pluginSlug: string,
        tabId: string,
        page?: number,
        pageSize?: number,
        sort?: (string | null),
    }): CancelablePromise<DataportTabRowsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/data-port/plugins/{plugin_slug}/tab/{tab_id}',
            path: {
                'plugin_slug': pluginSlug,
                'tab_id': tabId,
            },
            query: {
                'page': page,
                'page_size': pageSize,
                'sort': sort,
            },
            errors: {
                400: `Invalid sort direction or column.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
                404: `Plugin has no dataport.yaml or tab not declared.`,
                422: `Validation Error`,
            },
        });
    }
}
