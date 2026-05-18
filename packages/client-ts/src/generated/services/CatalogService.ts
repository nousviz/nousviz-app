/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogPluginTablesResponse } from '../models/CatalogPluginTablesResponse';
import type { CatalogTable } from '../models/CatalogTable';
import type { CatalogTableRowsResponse } from '../models/CatalogTableRowsResponse';
import type { CatalogTablesGroupedResponse } from '../models/CatalogTablesGroupedResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CatalogService {
    /**
     * All discovered plugin tables, grouped by plugin
     * @returns CatalogTablesGroupedResponse Successful Response
     * @throws ApiError
     */
    public static catalogTablesGrouped(): CancelablePromise<CatalogTablesGroupedResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/catalog/tables',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
            },
        });
    }
    /**
     * Discovered tables for one plugin (with manifest drift)
     * All discovered tables for a single plugin.
     *
     * Returns empty `tables` list (not 404) if the plugin has no
     * discovered tables, so the frontend can render an empty state
     * cleanly without distinguishing "plugin not installed" from
     * "plugin owns nothing."
     * @returns CatalogPluginTablesResponse Successful Response
     * @throws ApiError
     */
    public static catalogPluginTablesList({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<CatalogPluginTablesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/catalog/plugins/{plugin_id}/tables',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Schema + metadata for one (plugin, table) pair
     * Schema and metadata for one specific (plugin, table).
     * @returns CatalogTable Successful Response
     * @throws ApiError
     */
    public static catalogPluginTableDetail({
        pluginId,
        tableName,
    }: {
        pluginId: string,
        tableName: string,
    }): CancelablePromise<CatalogTable> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/catalog/plugins/{plugin_id}/tables/{table_name}',
            path: {
                'plugin_id': pluginId,
                'table_name': tableName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
                404: `Plugin not installed, manifest doesn't declare table, or table missing.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Paginated rows from a discovered plugin table (B262: server-side filters + search)
     * Paginated rows from a discovered plugin table.
     *
     * The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
     * Works for every plugin's every granted table — no `dataport.yaml`
     * opt-in required.
     *
     * `sort` accepts "column" or "column desc" / "column asc". Invalid
     * sort (column not in table) is silently dropped (no-sort fallback)
     * rather than 400-erroring; pagination still works.
     *
     * `q` is a server-side substring search. Casts text-coercible columns
     * to text and matches via ILIKE. Empty q is treated as no q.
     *
     * `filter` is repeatable. Each value is `col:op:value` (or
     * `col:is_null` / `col:not_null` for null checks). Filters AND together;
     * the response's `total` reflects the filtered count.
     *
     * Response:
     * {
         * "rows": [{...}, {...}, ...],
         * "total": 7068,    # filtered count when q/filter present
         * "page": 1,
         * "limit": 50
         * }
         * @returns CatalogTableRowsResponse Successful Response
         * @throws ApiError
         */
        public static catalogPluginTableRows({
            pluginId,
            tableName,
            page = 1,
            limit = 50,
            sort,
            q,
            filter,
        }: {
            pluginId: string,
            tableName: string,
            page?: number,
            limit?: number,
            sort?: (string | null),
            /**
             * Full-dataset substring search (B262). Matches via ILIKE %q% across text-coercible columns (text, varchar, json, jsonb, uuid). Capped at 100 characters.
             */
            q?: (string | null),
            /**
             * Per-column predicate filter (B262). Repeatable. Each filter is `col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, startswith, is_null, not_null. Up to 8 per request. Filters compose with AND.
             */
            filter?: Array<string>,
        }): CancelablePromise<CatalogTableRowsResponse> {
            return __request(OpenAPI, {
                method: 'GET',
                url: '/api/catalog/plugins/{plugin_id}/tables/{table_name}/rows',
                path: {
                    'plugin_id': pluginId,
                    'table_name': tableName,
                },
                query: {
                    'page': page,
                    'limit': limit,
                    'sort': sort,
                    'q': q,
                    'filter': filter,
                },
                errors: {
                    400: `Malformed filter, unknown column/operator, q too long, or too many filters.`,
                    401: `Missing or invalid session token.`,
                    403: `Caller lacks the datasets.read permission.`,
                    404: `Table not owned by plugin or doesn't exist.`,
                    422: `Validation Error`,
                    500: `Internal — fetch_rows raised. Check API logs.`,
                },
            });
        }
    }
