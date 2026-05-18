/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectionDeleteResponse } from '../models/ConnectionDeleteResponse';
import type { ConnectionHealthCheckResponse } from '../models/ConnectionHealthCheckResponse';
import type { ConnectionHealthHistoryResponse } from '../models/ConnectionHealthHistoryResponse';
import type { ConnectionRow } from '../models/ConnectionRow';
import type { ConnectionsListResponse } from '../models/ConnectionsListResponse';
import type { ConnectionTestResponse } from '../models/ConnectionTestResponse';
import type { CreateConnection } from '../models/CreateConnection';
import type { MysqlInitDefaultResponse } from '../models/MysqlInitDefaultResponse';
import type { UpdateConnection } from '../models/UpdateConnection';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConnectionsService {
    /**
     * List all named connections (passwords masked)
     * List every operator-managed connection. Plugin-managed connections
     * (`name='plugin:<slug>'`) appear here too; their config password
     * field is replaced with the constant '••••••••'.
     * @returns ConnectionsListResponse Successful Response
     * @throws ApiError
     */
    public static connectionsList(): CancelablePromise<ConnectionsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
            },
        });
    }
    /**
     * Create a named connection
     * @returns ConnectionRow Successful Response
     * @throws ApiError
     */
    public static connectionsCreate({
        requestBody,
    }: {
        requestBody: CreateConnection,
    }): CancelablePromise<ConnectionRow> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/connections',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid type, or name is empty.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List connections of a specific type (postgres/mysql/clickhouse)
     * @returns ConnectionsListResponse Successful Response
     * @throws ApiError
     */
    public static connectionsListByType({
        connType,
    }: {
        connType: string,
    }): CancelablePromise<ConnectionsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/by-type/{conn_type}',
            path: {
                'conn_type': connType,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get the default connection of a type (404 if none)
     * @returns ConnectionRow Successful Response
     * @throws ApiError
     */
    public static connectionsDefault({
        connType,
    }: {
        connType: string,
    }): CancelablePromise<ConnectionRow> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/default/{conn_type}',
            path: {
                'conn_type': connType,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `No default connection of that type.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Patch a connection (password preserved when masked)
     * @returns ConnectionRow Successful Response
     * @throws ApiError
     */
    public static connectionsUpdate({
        connId,
        requestBody,
    }: {
        connId: string,
        requestBody: UpdateConnection,
    }): CancelablePromise<ConnectionRow> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/connections/{conn_id}',
            path: {
                'conn_id': connId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Empty body.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a connection
     * @returns ConnectionDeleteResponse Successful Response
     * @throws ApiError
     */
    public static connectionsDelete({
        connId,
    }: {
        connId: string,
    }): CancelablePromise<ConnectionDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/connections/{conn_id}',
            path: {
                'conn_id': connId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Probe connectivity using stored credentials (no persist)
     * @returns ConnectionTestResponse Successful Response
     * @throws ApiError
     */
    public static connectionsTest({
        connId,
    }: {
        connId: string,
    }): CancelablePromise<ConnectionTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/connections/{conn_id}/test',
            path: {
                'conn_id': connId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Probe + persist (last 20 entries kept in health_history)
     * Run a health check and store the result in health_history.
     * @returns ConnectionHealthCheckResponse Successful Response
     * @throws ApiError
     */
    public static connectionsHealthCheck({
        connId,
    }: {
        connId: string,
    }): CancelablePromise<ConnectionHealthCheckResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/connections/{conn_id}/health-check',
            path: {
                'conn_id': connId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Last-stored health status + history JSONB
     * @returns ConnectionHealthHistoryResponse Successful Response
     * @throws ApiError
     */
    public static connectionsHealthHistory({
        connId,
    }: {
        connId: string,
    }): CancelablePromise<ConnectionHealthHistoryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/{conn_id}/health-history',
            path: {
                'conn_id': connId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create the default MySQL 'nousviz' database
     * Create a default MySQL 'nousviz' database using existing default MySQL connection.
     * @returns MysqlInitDefaultResponse Successful Response
     * @throws ApiError
     */
    public static connectionsMysqlInitDefault(): CancelablePromise<MysqlInitDefaultResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/connections/mysql/init-default',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `No default MySQL connection.`,
                500: `pymysql missing or CREATE DATABASE failed.`,
            },
        });
    }
    /**
     * List tables for this connection's database (grouped by schema)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static connectionsTablesList({
        connId,
    }: {
        connId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/{conn_id}/tables',
            path: {
                'conn_id': connId,
            },
            errors: {
                400: `Synthetic plugin connection; browse via /datasets instead.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection not found.`,
                422: `Validation Error`,
                501: `Connection type not supported for browsing yet.`,
                502: `Could not connect to the external database.`,
            },
        });
    }
    /**
     * Schema + metadata for one (connection, schema, table)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static connectionsTableDetail({
        connId,
        schema,
        table,
    }: {
        connId: string,
        schema: string,
        table: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/{conn_id}/tables/{schema}/{table}',
            path: {
                'conn_id': connId,
                'schema': schema,
                'table': table,
            },
            errors: {
                400: `Invalid schema/table name or synthetic plugin connection.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission, or schema is hidden.`,
                404: `Connection or table not found.`,
                422: `Validation Error`,
                501: `Connection type not supported for browsing yet.`,
                502: `Could not connect to the external database.`,
            },
        });
    }
    /**
     * Paginated rows for a (connection, schema, table)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static connectionsTableRows({
        connId,
        schema,
        table,
        page = 1,
        limit = 50,
        sort,
        q,
        requestBody,
    }: {
        connId: string,
        schema: string,
        table: string,
        page?: number,
        limit?: number,
        sort?: (string | null),
        q?: (string | null),
        requestBody?: Array<string>,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/connections/{conn_id}/tables/{schema}/{table}/rows',
            path: {
                'conn_id': connId,
                'schema': schema,
                'table': table,
            },
            query: {
                'page': page,
                'limit': limit,
                'sort': sort,
                'q': q,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Malformed filter, unknown column/operator, q too long, or too many filters.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Connection or table not found.`,
                422: `Validation Error`,
                501: `Connection type not supported for browsing yet.`,
                502: `Could not connect to the external database.`,
            },
        });
    }
}
