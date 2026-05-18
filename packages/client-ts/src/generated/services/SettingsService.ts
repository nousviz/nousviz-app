/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiKeyEntry } from '../models/ApiKeyEntry';
import type { ApiKeySettingsCreateResponse } from '../models/ApiKeySettingsCreateResponse';
import type { ApiKeySettingsRevokeResponse } from '../models/ApiKeySettingsRevokeResponse';
import type { CreateKeyRequest } from '../models/CreateKeyRequest';
import type { DatabaseSaveResponse } from '../models/DatabaseSaveResponse';
import type { DatabaseSettings } from '../models/DatabaseSettings';
import type { DatabaseSettingsResponse } from '../models/DatabaseSettingsResponse';
import type { DeployKeyCheckResponse } from '../models/DeployKeyCheckResponse';
import type { DeployKeyCreate } from '../models/DeployKeyCreate';
import type { DeployKeyCreateResponse } from '../models/DeployKeyCreateResponse';
import type { DeployKeyDeleteResponse } from '../models/DeployKeyDeleteResponse';
import type { DeployKeysListResponse } from '../models/DeployKeysListResponse';
import type { DeployKeyTestResponse } from '../models/DeployKeyTestResponse';
import type { EmailSaveResponse } from '../models/EmailSaveResponse';
import type { EmailSettings } from '../models/EmailSettings';
import type { EmailSettingsResponse } from '../models/EmailSettingsResponse';
import type { EmailTestResponse } from '../models/EmailTestResponse';
import type { GitSettings } from '../models/GitSettings';
import type { GitSettingsGetResponse } from '../models/GitSettingsGetResponse';
import type { GitSettingsSaveResponse } from '../models/GitSettingsSaveResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SettingsService {
    /**
     * Read Postgres connection config (no password)
     * Return current Postgres config (no passwords).
     * @returns DatabaseSettingsResponse Successful Response
     * @throws ApiError
     */
    public static settingsDatabaseGet(): CancelablePromise<DatabaseSettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/database',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
            },
        });
    }
    /**
     * Save Postgres config + reconnect pool (no restart)
     * Update Postgres connection settings in .env and in the live process,
     * then reconnect the pool — no API restart needed.
     *
     * On connect failure, the .env was still patched. The response carries
     * `ok=false` + `error` so the operator can fix and retry. Reverting to
     * the prior config requires editing .env on disk.
     * @returns DatabaseSaveResponse Successful Response
     * @throws ApiError
     */
    public static settingsDatabaseSet({
        requestBody,
    }: {
        requestBody: DatabaseSettings,
    }): CancelablePromise<DatabaseSaveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/database',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read SMTP config (no password)
     * Return current SMTP config (no password — display only).
     * @returns EmailSettingsResponse Successful Response
     * @throws ApiError
     */
    public static settingsEmailGet(): CancelablePromise<EmailSettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/email',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
            },
        });
    }
    /**
     * Save SMTP config to .env
     * Save SMTP configuration to .env and update live process.
     * @returns EmailSaveResponse Successful Response
     * @throws ApiError
     */
    public static settingsEmailSet({
        requestBody,
    }: {
        requestBody: EmailSettings,
    }): CancelablePromise<EmailSaveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/email',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read GitHub-token status (masked)
     * @returns GitSettingsGetResponse Successful Response
     * @throws ApiError
     */
    public static settingsGitGet(): CancelablePromise<GitSettingsGetResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/git',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
            },
        });
    }
    /**
     * Set the GITHUB_TOKEN env var
     * @returns GitSettingsSaveResponse Successful Response
     * @throws ApiError
     */
    public static settingsGitSet({
        requestBody,
    }: {
        requestBody: GitSettings,
    }): CancelablePromise<GitSettingsSaveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/git',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Send a test email to the current user (or SMTP_FROM_ADDRESS fallback)
     * Send a test email to the current authenticated user.
     * @returns EmailTestResponse Successful Response
     * @throws ApiError
     */
    public static settingsEmailTest(): CancelablePromise<EmailTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/email/test',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
            },
        });
    }
    /**
     * List active API keys (no raw keys, ever)
     * List all active API keys (prefix + metadata only — never the raw key).
     * @returns ApiKeyEntry Successful Response
     * @throws ApiError
     */
    public static settingsApiKeysList(): CancelablePromise<Array<ApiKeyEntry>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/api-keys',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
            },
        });
    }
    /**
     * Generate a new API key (raw key returned exactly once)
     * Generate a new API key. The raw key is returned once and never stored.
     * @returns ApiKeySettingsCreateResponse Successful Response
     * @throws ApiError
     */
    public static settingsApiKeysCreate({
        requestBody,
    }: {
        requestBody: CreateKeyRequest,
    }): CancelablePromise<ApiKeySettingsCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/api-keys',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Name required.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revoke an API key
     * Revoke an API key by ID.
     * @returns ApiKeySettingsRevokeResponse Successful Response
     * @throws ApiError
     */
    public static settingsApiKeysRevoke({
        keyId,
    }: {
        keyId: string,
    }): CancelablePromise<ApiKeySettingsRevokeResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/settings/api-keys/{key_id}',
            path: {
                'key_id': keyId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                404: `Key not found or already revoked.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List registered SSH deploy keys
     * List registered deploy keys.
     *
     * B206 (v0.9.6): response includes ``created_by`` (joined to ``users``)
     * and ``repo_url``. Rows whose creator was deleted render with
     * ``created_by=None`` rather than vanishing — the key still exists and
     * must remain manageable.
     * @returns DeployKeysListResponse Successful Response
     * @throws ApiError
     */
    public static settingsDeployKeysList(): CancelablePromise<DeployKeysListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/deploy-keys',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
            },
        });
    }
    /**
     * Generate a new ed25519 SSH deploy key
     * @returns DeployKeyCreateResponse Successful Response
     * @throws ApiError
     */
    public static settingsDeployKeysCreate({
        requestBody,
    }: {
        requestBody: DeployKeyCreate,
    }): CancelablePromise<DeployKeyCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/deploy-keys',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Name is required.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                422: `Validation Error`,
                500: `ssh-keygen failed or NOUSVIZ_ENCRYPTION_KEY is not set.`,
            },
        });
    }
    /**
     * Check whether a deploy key exists for a given repo URL
     * Check if a deploy key exists for the given repo URL.
     *
     * B204: only exact repo_url matches return has_key=True. The previous
     * host fallback returned a green indicator even when the actual key
     * couldn't authenticate against this URL — the operator was misled
     * into thinking install would succeed.
     * @returns DeployKeyCheckResponse Successful Response
     * @throws ApiError
     */
    public static settingsDeployKeysCheck({
        repoUrl,
    }: {
        repoUrl: string,
    }): CancelablePromise<DeployKeyCheckResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/settings/deploy-keys/check',
            query: {
                'repo_url': repoUrl,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a deploy key (writes an audit row)
     * Delete a deploy key.
     *
     * B206 (v0.9.6): writes an ``app_logs`` entry at source ``deploy_keys``
     * so operators can see who deleted what in /system/logs.
     * @returns DeployKeyDeleteResponse Successful Response
     * @throws ApiError
     */
    public static settingsDeployKeysDelete({
        keyId,
    }: {
        keyId: string,
    }): CancelablePromise<DeployKeyDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/settings/deploy-keys/{key_id}',
            path: {
                'key_id': keyId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                404: `Key not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * SSH-auth probe a deploy key against its host
     * @returns DeployKeyTestResponse Successful Response
     * @throws ApiError
     */
    public static settingsDeployKeysTest({
        keyId,
    }: {
        keyId: string,
    }): CancelablePromise<DeployKeyTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/settings/deploy-keys/{key_id}/test',
            path: {
                'key_id': keyId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the settings.write permission.`,
                404: `Key not found.`,
                422: `Validation Error`,
            },
        });
    }
}
