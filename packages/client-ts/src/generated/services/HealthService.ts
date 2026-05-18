/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectionHealthResponse } from '../models/ConnectionHealthResponse';
import type { HealthConfigResponse } from '../models/HealthConfigResponse';
import type { HealthLogResponse } from '../models/HealthLogResponse';
import type { HealthRecordResponse } from '../models/HealthRecordResponse';
import type { HealthResponse } from '../models/HealthResponse';
import type { SslSetupRequest } from '../models/SslSetupRequest';
import type { SslSetupResponse } from '../models/SslSetupResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * Overall instance health
     * Overall health check for the NousViz instance.
     *
     * Public endpoint (no auth required) — this is the same shape used by
     * load balancers and the operator dashboard. The response is intentionally
     * nested: `services.postgres` reports DB connectivity and critical-table
     * presence, `runtime.sdk` reports whether `nousviz_sdk` imported, and
     * `stats` carries operator-dashboard counts.
     *
     * Top-level `status` flips to `degraded` when Postgres reports degraded,
     * the SDK is unavailable, or critical tables are missing. Frontend
     * `evaluateChecks` drives banner display from this shape — additive
     * changes here are safe; renaming or removing fields will break the UI.
     * @returns HealthResponse Successful Response
     * @throws ApiError
     */
    public static healthCheck(): CancelablePromise<HealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health',
        });
    }
    /**
     * Boolean status of security-sensitive config
     * Return boolean status of security-sensitive config values.
     *
     * Public endpoint (no auth required) — this is what the dashboard
     * config-banner reads to decide whether to nudge the operator about
     * missing encryption keys, missing superadmin user, SMTP config, etc.
     *
     * **Never exposes actual values** — only whether they are set and
     * non-default. The `update_*` fields surface a once-per-hour-cached
     * GitHub release check so operators can see the "update available"
     * banner without polling the GitHub API on every request.
     * @returns HealthConfigResponse Successful Response
     * @throws ApiError
     */
    public static healthConfig(): CancelablePromise<HealthConfigResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health/config',
        });
    }
    /**
     * Plugin connection health issues
     * Banner-shaped list of plugin connection-health issues.
     *
     * Each entry carries a plugin id, severity, message, and optional
     * structured detail — the UI renders each as a banner on the home
     * dashboard. An empty list means all installed plugins report healthy
     * connections.
     *
     * Plugins will register their own health checks via `plugin_registry`
     * in a future release; the current implementation always returns no
     * issues.
     * @returns ConnectionHealthResponse Successful Response
     * @throws ApiError
     */
    public static healthConnections(): CancelablePromise<ConnectionHealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health/connections',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.logs permission.`,
            },
        });
    }
    /**
     * Recent health-check snapshots from health_log
     * Return health check history from the health_log table.
     * @returns HealthLogResponse Successful Response
     * @throws ApiError
     */
    public static healthLog({
        days = 7,
        limit = 200,
    }: {
        days?: number,
        limit?: number,
    }): CancelablePromise<HealthLogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health/log',
            query: {
                'days': days,
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
     * Run a health check + persist to health_log (PM2 cron + manual refresh)
     * Run a health check and store the result in health_log.
     *
     * Accepted from:
     * - localhost (PM2 cron on the same box) — unlimited rate
     * - authenticated requests (session token, API key, or Cloudflare) — lets
     * an operator force a fresh check from the browser via the Refresh button
     * on /health-overview. Rate-limited per-IP.
     * @returns HealthRecordResponse Successful Response
     * @throws ApiError
     */
    public static healthRecord(): CancelablePromise<HealthRecordResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/health/record',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Health record requires localhost or authenticated access.`,
                429: `Rate-limited (10/min per IP, localhost exempt).`,
                500: `Health record failed.`,
            },
        });
    }
    /**
     * Provision Let's Encrypt SSL via the ssl-setup.sh script
     * Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
     * Only Let's Encrypt is supported (requires a domain).
     * @returns SslSetupResponse Successful Response
     * @throws ApiError
     */
    public static adminSslSetup({
        requestBody,
    }: {
        requestBody: SslSetupRequest,
    }): CancelablePromise<SslSetupResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/ssl/setup',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid mode/domain.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.admin permission.`,
                422: `Validation Error`,
                500: `ssl-setup.sh missing or invocation failed.`,
            },
        });
    }
}
