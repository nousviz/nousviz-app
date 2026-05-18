/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PluginScriptRunResponse } from '../models/PluginScriptRunResponse';
import type { SyncRequest } from '../models/SyncRequest';
import type { SyncResponse } from '../models/SyncResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SyncService {
    /**
     * Trigger Sync
     * Trigger a plugin sync manually.
     *
     * B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
     * scheduled runs (the scheduler dispatches them) but ignored here —
     * manual triggers always enqueue and return immediately so the HTTP
     * request never blocks on subprocess execution. The unified Sync card
     * on the plugin Settings tab polls /sync/status for live progress.
     *
     * Returns 409 Conflict when an active run already exists (status in
     * queued/running/cancelling). Body shape on 409:
     * {"detail": {"run_id": <existing>, "status": <status>,
     * "already_running": true}}
     * Frontend swaps to the live progress view in this case rather than
     * enqueueing a duplicate.
     * @returns SyncResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSync({
        pluginId,
        requestBody,
    }: {
        pluginId: string,
        requestBody?: SyncRequest,
    }): CancelablePromise<SyncResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/sync',
            path: {
                'plugin_id': pluginId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run a plugin's setup_schema.py script (60s timeout)
     * Run the plugin's schema setup script.
     *
     * Synchronous (not part of the async sync pipeline) — the response
     * blocks until the subprocess exits or the 60s timeout fires. The
     * plugin's environment is sanitised by `plugin_subprocess.plugin_sync_env`.
     * @returns PluginScriptRunResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSetup({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginScriptRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/setup',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin has no setup_schema.py.`,
                422: `Validation Error`,
                500: `Subprocess raised before producing output.`,
            },
        });
    }
    /**
     * Run a plugin's health_check.py script (30s timeout)
     * Run the plugin's health check script.
     *
     * Synchronous — the response blocks until the subprocess exits or
     * the 30s timeout fires. The plugin's environment is sanitised by
     * `plugin_subprocess.plugin_sync_env`.
     * @returns PluginScriptRunResponse Successful Response
     * @throws ApiError
     */
    public static pluginsHealthCheck({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginScriptRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/health-check',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin has no health_check.py.`,
                422: `Validation Error`,
                500: `Subprocess raised before producing output.`,
            },
        });
    }
}
