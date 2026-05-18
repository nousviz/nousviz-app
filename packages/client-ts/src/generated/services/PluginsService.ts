/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstallTestResponse } from '../models/InstallTestResponse';
import type { PluginAuditLogResponse } from '../models/PluginAuditLogResponse';
import type { PluginCapabilitiesResponse } from '../models/PluginCapabilitiesResponse';
import type { PluginCatalogResponse } from '../models/PluginCatalogResponse';
import type { PluginConnectionsResponse } from '../models/PluginConnectionsResponse';
import type { PluginConnectionsSaveResponse } from '../models/PluginConnectionsSaveResponse';
import type { PluginEntry } from '../models/PluginEntry';
import type { PluginFrontendComponentsResponse } from '../models/PluginFrontendComponentsResponse';
import type { PluginInstallRequest } from '../models/PluginInstallRequest';
import type { PluginInstallResponse } from '../models/PluginInstallResponse';
import type { PluginListResponse } from '../models/PluginListResponse';
import type { PluginModulesListResponse } from '../models/PluginModulesListResponse';
import type { PluginModuleToggleResponse } from '../models/PluginModuleToggleResponse';
import type { PluginSettingsBody } from '../models/PluginSettingsBody';
import type { PluginSettingsResponse } from '../models/PluginSettingsResponse';
import type { PluginSettingsSaveResponse } from '../models/PluginSettingsSaveResponse';
import type { PluginUninstallResponse } from '../models/PluginUninstallResponse';
import type { PluginUpdateInfo } from '../models/PluginUpdateInfo';
import type { PluginUpdateResponse } from '../models/PluginUpdateResponse';
import type { PluginUpdatesListResponse } from '../models/PluginUpdatesListResponse';
import type { PluginYamlResource } from '../models/PluginYamlResource';
import type { RevokeFrontendTrustResponse } from '../models/RevokeFrontendTrustResponse';
import type { SyncScheduleBody } from '../models/SyncScheduleBody';
import type { SyncScheduleGetResponse } from '../models/SyncScheduleGetResponse';
import type { SyncScheduleSetResponse } from '../models/SyncScheduleSetResponse';
import type { SyncStatusResponse } from '../models/SyncStatusResponse';
import type { TrustFrontendResponse } from '../models/TrustFrontendResponse';
import type { UninstallCheckResponse } from '../models/UninstallCheckResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PluginsService {
    /**
     * List installed plugins
     * List only active (installed) plugins — used by the Installed Plugins page and sidebar.
     *
     * B144 (v0.9.2.4): each entry carries an `update_status` block from the
     * plugin_update_status cache. Stale entries (older than ~1h) trigger a
     * fire-and-forget refresh in the background so the next call sees fresh
     * data. The current call doesn't block on the network check.
     *
     * Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
     * lookups that `_enrich_datasets` used to fire per-plugin are now
     * pre-fetched in two batched calls before the loop. Drops `/api/plugins`
     * DB round trips from ~6N to ~3 for the enrichment block alone.
     *
     * B305 (v0.10.0.6): the result list is filtered through
     * `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
     * allowlist (resource_acls rows for resource_type='plugin') sees only
     * their permitted set + utilities. Admins/superadmins bypass.
     * @returns PluginListResponse Successful Response
     * @throws ApiError
     */
    public static pluginsList(): CancelablePromise<PluginListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
            },
        });
    }
    /**
     * Recent plugin lifecycle events (install/uninstall/update/etc.)
     * View plugin audit log entries.
     * @returns PluginAuditLogResponse Successful Response
     * @throws ApiError
     */
    public static pluginsAuditLog({
        pluginId,
        limit = 50,
    }: {
        pluginId?: (string | null),
        limit?: number,
    }): CancelablePromise<PluginAuditLogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/audit-log',
            query: {
                'plugin_id': pluginId,
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.audit permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Capabilities registered by installed utility plugins
     * Return registered capabilities from installed utility plugins.
     * @returns PluginCapabilitiesResponse Successful Response
     * @throws ApiError
     */
    public static pluginsCapabilities(): CancelablePromise<PluginCapabilitiesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/capabilities',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
            },
        });
    }
    /**
     * Full plugin catalog for the Marketplace page
     * Full plugin catalog — official + installed + community, with installed flag.
     * Used by the Marketplace page.
     *
     * Priority: installed/ and community/ win over official/ stubs for the same
     * plugin slug — the installed copy has richer metadata and is the live version.
     * Official stubs only appear in the catalog when the plugin is not installed.
     *
     * P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
     * Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.
     * @returns PluginCatalogResponse Successful Response
     * @throws ApiError
     */
    public static pluginsCatalog(): CancelablePromise<PluginCatalogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/catalog',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
            },
        });
    }
    /**
     * Get a plugin's full manifest with module merges + predicate resolution
     * Get full plugin manifest, with enabled module manifests merged in.
     *
     * v0.8.6: also resolves P119 action predicates and P121 checklist
     * predicates server-side so the frontend can render without further
     * round trips.
     *
     * v0.9.0 (P204): includes `load_status` reflecting whether the
     * plugin's api/routes.py loaded successfully at API startup. If false,
     * `failure_reason` explains why (ModuleNotFoundError, SyntaxError, etc).
     * @returns PluginEntry Successful Response
     * @throws ApiError
     */
    public static pluginsDetail({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginEntry> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a plugin dashboard spec (YAML, returned verbatim)
     * Get a dashboard spec for rendering. Searches parent dashboards/ first, then enabled modules.
     * @returns PluginYamlResource Successful Response
     * @throws ApiError
     */
    public static pluginsDashboard({
        pluginId,
        dashboardName,
    }: {
        pluginId: string,
        dashboardName: string,
    }): CancelablePromise<PluginYamlResource> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/dashboards/{dashboard_name}',
            path: {
                'plugin_id': pluginId,
                'dashboard_name': dashboardName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Dashboard not found in plugin or its enabled modules.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a plugin dataset schema (YAML, returned verbatim)
     * Get a dataset schema.
     * @returns PluginYamlResource Successful Response
     * @throws ApiError
     */
    public static pluginsDataset({
        pluginId,
        datasetName,
    }: {
        pluginId: string,
        datasetName: string,
    }): CancelablePromise<PluginYamlResource> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/datasets/{dataset_name}',
            path: {
                'plugin_id': pluginId,
                'dataset_name': datasetName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Dataset not found in plugin.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Pre-install repo connectivity probe (clone + read manifest)
     * Test connectivity to a private repo before installing. Probe-clones and reads manifest.
     * @returns InstallTestResponse Successful Response
     * @throws ApiError
     */
    public static pluginsInstallTest({
        pluginId,
        requestBody,
    }: {
        pluginId: string,
        requestBody?: (PluginInstallRequest | null),
    }): CancelablePromise<InstallTestResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/install/test',
            path: {
                'plugin_id': pluginId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `repository_url required.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission, or SSH auth failed.`,
                404: `Repository not found.`,
                422: `Validation Error`,
                502: `Clone failed (network/repo error).`,
            },
        });
    }
    /**
     * Install a plugin
     * Install a plugin. Three-tier source resolution (P19):
     *
     * - Tier 1 (official): no repository_url — clones github.com/nousviz/plugin-{slug}
     * - Tier 2 (community): no repository_url — reads URL from plugins/community/{slug}/plugin.yaml
     * - Tier 3 (private): explicit repository_url in request body
     *
     * Idempotent if already installed. Restart the API after installing to activate routes.
     *
     * Security (P22):
     * - Rate limited: 5 installs per 5 minutes per IP (G3)
     * - Git clone pins to declared version tag (G2) — refuses HEAD installs
     * - pip runs with a sanitised environment — no NOUSVIZ_* vars exposed (G5)
     * - repository_url validated against SSRF blocklist (P19)
     * @returns PluginInstallResponse Successful Response
     * @throws ApiError
     */
    public static pluginsInstall({
        pluginId,
        requestBody,
    }: {
        pluginId: string,
        requestBody?: (PluginInstallRequest | null),
    }): CancelablePromise<PluginInstallResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/install',
            path: {
                'plugin_id': pluginId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                422: `Validation Error`,
                429: `Rate-limited (5 installs / 5 min per IP).`,
                503: `nousviz_sdk not importable in the API runtime.`,
            },
        });
    }
    /**
     * Uninstall a plugin (with optional dependent cascade)
     * Uninstall a plugin.
     *
     * - remove_data=true: run down migrations to drop plugin tables before removal
     * - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
     * references — delete annotations pinned to the plugin, delete
     * shares pointing at /plugin/<id>*, strip the plugin slug from
     * fusion `requires` arrays. Alert rules are left alone (Phase 2).
     * - cascade=true: also uninstall all plugins that depend on this one
     *
     * Returns has_dependents status if dependents exist and cascade=false —
     * the frontend should prompt the user to confirm cascade or cancel.
     * @returns PluginUninstallResponse Successful Response
     * @throws ApiError
     */
    public static pluginsUninstall({
        pluginId,
        removeData = false,
        removeReferences = false,
        cascade = false,
    }: {
        pluginId: string,
        removeData?: boolean,
        removeReferences?: boolean,
        cascade?: boolean,
    }): CancelablePromise<PluginUninstallResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/plugins/{plugin_id}/install',
            path: {
                'plugin_id': pluginId,
            },
            query: {
                'remove_data': removeData,
                'remove_references': removeReferences,
                'cascade': cascade,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Pre-uninstall info for the confirmation modal
     * Return information needed to render the uninstall confirmation modal:
     * - dependents: installed plugins that depend on this one (via `requires.{capability}`)
     * - tables: Postgres/ClickHouse tables owned by this plugin
     * - data_dirs: filesystem data directories (mainly for utility plugins)
     * @returns UninstallCheckResponse Successful Response
     * @throws ApiError
     */
    public static pluginsUninstallCheck({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<UninstallCheckResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/uninstall-check',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Bulk update status for every installed plugin (B144 cache)
     * Bulk fetch cached update status for every installed plugin.
     *
     * Stale entries (older than ~1h) get a fire-and-forget refresh kicked
     * off in the background so the UI sees fresh data on the next poll.
     * @returns PluginUpdatesListResponse Successful Response
     * @throws ApiError
     */
    public static pluginsUpdatesList(): CancelablePromise<PluginUpdatesListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/updates',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
            },
        });
    }
    /**
     * Force a synchronous update check for one plugin
     * Synchronously check this plugin for an available update.
     *
     * Use when the operator clicks an explicit "Check now" affordance, or
     * when the cached status says no-update but the operator wants to force
     * a re-check after pushing a new version upstream.
     * @returns PluginUpdateInfo Successful Response
     * @throws ApiError
     */
    public static pluginsCheckUpdate({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginUpdateInfo> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/check-update',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Atomic-swap update to the latest version (B145)
     * Update an installed plugin to the latest version from its source.
     *
     * Atomic-swap design (B145): the new code is cloned to a staging directory
     * first, validated, then atomically swapped with the live install. If
     * anything fails before the swap, the live install is untouched. If the
     * post-swap idempotent steps (migrations, grants) fail, the previous live
     * install is restored from a sibling backup.
     *
     * Credentials, settings, and synced data are preserved across the swap
     * (DB tables are not dropped). The plugin briefly becomes unavailable
     * while PM2 reloads to pick up the new routes.
     * @returns PluginUpdateResponse Successful Response
     * @throws ApiError
     */
    public static pluginsUpdate({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginUpdateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/update',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                400: `Cannot determine update source.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a plugin alert definition (YAML, returned verbatim)
     * Get an alert definition.
     * @returns PluginYamlResource Successful Response
     * @throws ApiError
     */
    public static pluginsAlert({
        pluginId,
        alertName,
    }: {
        pluginId: string,
        alertName: string,
    }): CancelablePromise<PluginYamlResource> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/alerts/{alert_name}',
            path: {
                'plugin_id': pluginId,
                'alert_name': alertName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Alert not found in plugin.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read a plugin's saved settings
     * Return current saved settings for a plugin.
     * @returns PluginSettingsResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSettingsGet({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginSettingsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/settings',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upsert a plugin's settings
     * Upsert settings for a plugin. Each key/value pair stored as a separate row.
     * @returns PluginSettingsSaveResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSettingsSet({
        pluginId,
        requestBody,
    }: {
        pluginId: string,
        requestBody: PluginSettingsBody,
    }): CancelablePromise<PluginSettingsSaveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/settings',
            path: {
                'plugin_id': pluginId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin not installed.`,
                422: `Setting key not declared in the plugin manifest.`,
            },
        });
    }
    /**
     * List a plugin's modules with enabled state
     * List modules for a plugin with their enabled state.
     * @returns PluginModulesListResponse Successful Response
     * @throws ApiError
     */
    public static pluginsModulesList({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginModulesListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/modules',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Enable a plugin module (runs migrations, grants tables)
     * Enable a plugin module.
     * @returns PluginModuleToggleResponse Successful Response
     * @throws ApiError
     */
    public static pluginsModulesEnable({
        pluginId,
        moduleName,
    }: {
        pluginId: string,
        moduleName: string,
    }): CancelablePromise<PluginModuleToggleResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/modules/{module_name}/enable',
            path: {
                'plugin_id': pluginId,
                'module_name': moduleName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Module not found in plugin.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Disable a plugin module (data preserved)
     * Disable a plugin module. Data is preserved.
     * @returns PluginModuleToggleResponse Successful Response
     * @throws ApiError
     */
    public static pluginsModulesDisable({
        pluginId,
        moduleName,
    }: {
        pluginId: string,
        moduleName: string,
    }): CancelablePromise<PluginModuleToggleResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/modules/{module_name}/disable',
            path: {
                'plugin_id': pluginId,
                'module_name': moduleName,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read a plugin's connection config (secrets masked)
     * Return connection config for a plugin including module connections. Masks secrets.
     * @returns PluginConnectionsResponse Successful Response
     * @throws ApiError
     */
    public static pluginsConnectionsGet({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginConnectionsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/connections',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Plugin not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Save plugin connection config + run health hook
     * Save connection config for a plugin. Secrets → encrypted DB. Non-secrets → .env.
     * @returns PluginConnectionsSaveResponse Successful Response
     * @throws ApiError
     */
    public static pluginsConnectionsSet({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginConnectionsSaveResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/connections',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                400: `Plugin has no connection config declared.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Sync status snapshot for the unified Sync card (B205)
     * Sync status snapshot for the unified Sync card (B205, v0.9.6).
     *
     * Returns:
     * current: most recent run with status IN ('queued','running','cancelling'),
     * including live progress JSONB and elapsed seconds. None when idle.
     * last_success: most recent successful run.
     * last_failure: most recent failed run (error/timeout/cancelled).
     * last_sync: ISO timestamp of last_success.completed_at — kept for
     * backward compatibility with pre-v0.9.6 frontend code.
     *
     * The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
     * job_runs is the single source of truth.
     * @returns SyncStatusResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSyncStatus({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<SyncStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/sync/status',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Composite read of manifest + override + scheduler state
     * Composite read: manifest cron + override cron + scheduler registry state.
     *
     * Used by the Settings tab's schedule override block (B148).
     * @returns SyncScheduleGetResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSyncScheduleGet({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<SyncScheduleGetResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/sync-schedule',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Write or clear the per-plugin schedule override
     * Write a per-plugin schedule override.
     *
     * Body forms (mutually exclusive):
     * {"cron": "0 *12 * * *"}                 raw cron
     * {"interval_value": 15, "interval_unit": "minutes"}  friendly form
     * {"cron": null} or {"cron": ""}           clear override
     *
     * The scheduler observes the change on its next poll (within ~30s).
     * To make the change visible immediately, we delete the registry row;
     * the scheduler re-creates it on next poll with the new effective cron.
     * @returns SyncScheduleSetResponse Successful Response
     * @throws ApiError
     */
    public static pluginsSyncScheduleSet({
        pluginId,
        requestBody,
    }: {
        pluginId: string,
        requestBody: SyncScheduleBody,
    }): CancelablePromise<SyncScheduleSetResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/sync-schedule',
            path: {
                'plugin_id': pluginId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid cron, invalid interval, or both forms supplied.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.configure permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Plugin's declared React components + trust state (B151)
     * List a plugin's declared frontend components and their trust state.
     *
     * Public-ish: any logged-in user can read (the frontend needs this at boot
     * to know which components to dynamically import). Doesn't expose secrets.
     * @returns PluginFrontendComponentsResponse Successful Response
     * @throws ApiError
     */
    public static pluginsFrontendComponents({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<PluginFrontendComponentsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/frontend-components',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.read permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
                500: `Failed to read manifest.`,
            },
        });
    }
    /**
     * Operator consent: trust this plugin's React components
     * Operator consent: set plugin_settings._trust_frontend = true.
     *
     * Required before the frontend will dynamically import this plugin's
     * declared React components. Audited via plugin_audit_log so revocation
     * history is queryable.
     * @returns TrustFrontendResponse Successful Response
     * @throws ApiError
     */
    public static pluginsTrustFrontend({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<TrustFrontendResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/trust-frontend',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                400: `Plugin declares no frontend.components.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                404: `Plugin not installed.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Operator revoke: clear plugin frontend trust
     * Operator revoke: clear plugin_settings._trust_frontend.
     *
     * Idempotent — calling on an already-untrusted plugin returns success.
     * @returns RevokeFrontendTrustResponse Successful Response
     * @throws ApiError
     */
    public static pluginsRevokeFrontendTrust({
        pluginId,
    }: {
        pluginId: string,
    }): CancelablePromise<RevokeFrontendTrustResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/plugins/{plugin_id}/revoke-frontend-trust',
            path: {
                'plugin_id': pluginId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the plugins.install permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Serve a plugin's bundled JS widget asset
     * Serve a plugin's bundled JS widget file.
     *
     * Refuses unless:
     * - Plugin exists + has a manifest
     * - Plugin is trusted (operator consented via /trust-frontend)
     * - Filename matches a declared component's path basename
     * - File exists on disk inside the plugin dir
     * - Resolved path is contained within the plugin dir (no traversal)
     * @returns any Widget JS bundle.
     * @throws ApiError
     */
    public static pluginsWidgetAsset({
        pluginId,
        filename,
    }: {
        pluginId: string,
        filename: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/plugins/{plugin_id}/widget/{filename}',
            path: {
                'plugin_id': pluginId,
                'filename': filename,
            },
            errors: {
                400: `Invalid filename (must be \`[A-Za-z0-9._-]+\\.js\`).`,
                401: `Missing or invalid session token.`,
                403: `Plugin frontend not trusted by operator.`,
                404: `Plugin not installed or filename not declared.`,
                422: `Validation Error`,
            },
        });
    }
}
