/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CustomRoleCreateRequest } from '../models/CustomRoleCreateRequest';
import type { CustomRoleCreateResponse } from '../models/CustomRoleCreateResponse';
import type { DiagnosticsHistoryResponse } from '../models/DiagnosticsHistoryResponse';
import type { DiagnosticsResponse } from '../models/DiagnosticsResponse';
import type { PermissionsMatrixResponse } from '../models/PermissionsMatrixResponse';
import type { RbacAuditLogResponse } from '../models/RbacAuditLogResponse';
import type { ResourcesHistoryResponse } from '../models/ResourcesHistoryResponse';
import type { ResourcesResponse } from '../models/ResourcesResponse';
import type { RoleOverrideRequest } from '../models/RoleOverrideRequest';
import type { RoleOverrideResponse } from '../models/RoleOverrideResponse';
import type { UsersWithPermissionsResponse } from '../models/UsersWithPermissionsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SystemService {
    /**
     * Full RBAC matrix snapshot for /system/permissions
     * Full RBAC registry snapshot for the audit matrix UI.
     *
     * Response shape:
     * {
         * "permissions": {
             * "<name>": {"description": "...", "sensitive": bool}
             * },
             * "roles": {
                 * "<role>": ["<permission>", ...]
                 * },
                 * "routes": [
                     * {
                         * "method": "GET",
                         * "path": "/api/...",
                         * "permission": "plugins.read",
                         * "is_plugin_route": bool,
                         * "is_plugin_default": bool,
                         * "last_accessed": {
                             * "viewer": "<iso ts>" | null,
                             * "analyst": "<iso ts>" | null,
                             * ...
                             * }
                             * }
                             * ],
                             * "public_routes": [["GET", "/api/health"], ...],
                             * "audit_summary": {
                                 * "window_hours": 24,
                                 * "decisions": {"allow": N, "deny": M, "shadow_mismatch": K},
                                 * "top_denials": [{"permission": "...", "count": N}, ...]
                                 * },
                                 * "shadow_mode": bool,
                                 * "version": "0.9.8.3"
                                 * }
                                 * @returns PermissionsMatrixResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemPermissions(): CancelablePromise<PermissionsMatrixResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/permissions',
                                        errors: {
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                        },
                                    });
                                }
                                /**
                                 * Per-user permission audit data (Users tab on the matrix page)
                                 * B231 (v0.9.8.4) — per-user permission audit data.
                                 *
                                 * Backs the Users tab on the matrix page. For each user, returns:
                                 * - identity (id, email, name, role, is_active)
                                 * - their resolved permission set (from role -> permissions catalog)
                                 * - their most-recent allow decision in auth_audit (last 30d)
                                 *
                                 * The resolved permission set comes from the static catalog because
                                 * v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
                                 * top — this endpoint will return the post-override resolved set so
                                 * the frontend contract doesn't change.
                                 *
                                 * Sorted by email for stable rendering. An empty list is valid —
                                 * e.g. a fresh install before the wizard creates the first superadmin.
                                 * @returns UsersWithPermissionsResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemUsersWithPermissions(): CancelablePromise<UsersWithPermissionsResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/users-with-permissions',
                                        errors: {
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                        },
                                    });
                                }
                                /**
                                 * Grant or revoke a permission for a role (B233; step-up required)
                                 * Grant or revoke a permission for a role. Upserts: if a prior
                                 * override exists for the same (role, permission), it's deleted before
                                 * the new row is inserted. Cache invalidated so the change is visible
                                 * immediately.
                                 *
                                 * Refuses to grant a sensitive permission to a non-admin role (409).
                                 * @returns RoleOverrideResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemRoleOverridesUpsert({
                                    requestBody,
                                }: {
                                    requestBody: RoleOverrideRequest,
                                }): CancelablePromise<RoleOverrideResponse> {
                                    return __request(OpenAPI, {
                                        method: 'POST',
                                        url: '/api/system/role-overrides',
                                        body: requestBody,
                                        mediaType: 'application/json',
                                        errors: {
                                            400: `Unknown permission/role, or sensitive-revoke blocked.`,
                                            401: `Step-up auth required (B236).`,
                                            403: `Caller lacks the rbac.edit permission.`,
                                            409: `Sensitive permission can't be granted to non-admin role.`,
                                            422: `Validation Error`,
                                            500: `Failed to write override.`,
                                        },
                                    });
                                }
                                /**
                                 * Clear an override (idempotent; 204 even on no-op)
                                 * Clear any override for (role, permission). Idempotent — returns
                                 * 204 even when no override existed (no audit row in the no-op case).
                                 * @returns void
                                 * @throws ApiError
                                 */
                                public static systemRoleOverridesClear({
                                    role,
                                    permission,
                                }: {
                                    role: string,
                                    permission: string,
                                }): CancelablePromise<void> {
                                    return __request(OpenAPI, {
                                        method: 'DELETE',
                                        url: '/api/system/role-overrides/{role}/{permission}',
                                        path: {
                                            'role': role,
                                            'permission': permission,
                                        },
                                        errors: {
                                            401: `Step-up auth required (B236).`,
                                            403: `Caller lacks the rbac.edit permission.`,
                                            422: `Validation Error`,
                                            500: `Failed to clear override.`,
                                        },
                                    });
                                }
                                /**
                                 * Create a custom role (B233; step-up required)
                                 * Create a new operator-defined role.
                                 *
                                 * If `permissions` is omitted and `based_on` is a built-in role, the
                                 * new role's permission set starts as a copy of that role's defaults.
                                 * If both are omitted, the role starts empty and overrides must be
                                 * added separately via /role-overrides.
                                 *
                                 * B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
                                 * rejected with 409 (was silently filtered before — operators were
                                 * creating roles thinking they got the requested permissions).
                                 * `based_on` seeds still filter sensitive perms from the source role's
                                 * defaults, since the operator didn't ask for them explicitly.
                                 * @returns CustomRoleCreateResponse Custom role created.
                                 * @throws ApiError
                                 */
                                public static systemCustomRolesCreate({
                                    requestBody,
                                }: {
                                    requestBody: CustomRoleCreateRequest,
                                }): CancelablePromise<CustomRoleCreateResponse> {
                                    return __request(OpenAPI, {
                                        method: 'POST',
                                        url: '/api/system/custom-roles',
                                        body: requestBody,
                                        mediaType: 'application/json',
                                        errors: {
                                            400: `Invalid slug, unknown permission, or based_on not built-in.`,
                                            401: `Step-up auth required (B236).`,
                                            403: `Caller lacks the rbac.edit permission.`,
                                            409: `Slug collision or sensitive permission requested in seed.`,
                                            422: `Validation Error`,
                                            500: `Failed to create custom role.`,
                                        },
                                    });
                                }
                                /**
                                 * Delete a custom role (refuses if any user is assigned)
                                 * Delete a custom role. Refuses if any user is assigned this role
                                 * (operator must reassign first). Built-in roles cannot be deleted.
                                 * Override rows for this role are also deleted.
                                 * @returns void
                                 * @throws ApiError
                                 */
                                public static systemCustomRolesDelete({
                                    role,
                                }: {
                                    role: string,
                                }): CancelablePromise<void> {
                                    return __request(OpenAPI, {
                                        method: 'DELETE',
                                        url: '/api/system/custom-roles/{role}',
                                        path: {
                                            'role': role,
                                        },
                                        errors: {
                                            400: `Cannot delete built-in roles, or users still assigned.`,
                                            401: `Step-up auth required (B236).`,
                                            403: `Caller lacks the rbac.edit permission.`,
                                            404: `Custom role not found.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Paginated RBAC config-mutation audit log
                                 * Recent RBAC config mutations. Filters: actor / target_role /
                                 * action / time window. Cursor-based pagination (opaque numeric
                                 * cursor = the smallest id from the previous page).
                                 *
                                 * Joins users.email so renamed users still show up correctly.
                                 *
                                 * Gated by system.audit (admin+). Read-only.
                                 * @returns RbacAuditLogResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemRbacAuditLog({
                                    actorUserId,
                                    targetRole,
                                    action,
                                    since,
                                    until,
                                    cursor,
                                    limit = 50,
                                }: {
                                    actorUserId?: (string | null),
                                    targetRole?: (string | null),
                                    action?: (string | null),
                                    since?: (string | null),
                                    until?: (string | null),
                                    cursor?: (number | null),
                                    limit?: number,
                                }): CancelablePromise<RbacAuditLogResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/rbac-audit-log',
                                        query: {
                                            'actor_user_id': actorUserId,
                                            'target_role': targetRole,
                                            'action': action,
                                            'since': since,
                                            'until': until,
                                            'cursor': cursor,
                                            'limit': limit,
                                        },
                                        errors: {
                                            400: `Unknown action filter.`,
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * System + Postgres + per-plugin resource snapshot (B271)
                                 * Return server (CPU, memory, swap, disk, load) + Postgres
                                 * (db size, cache hit %, connections, pg_stat_statements installed)
                                 * + per-table + per-plugin + per-sync metrics in one call.
                                 *
                                 * Cached in-process for 30 seconds; pass `?fresh=true` to bypass the
                                 * cache and force a fresh collection.
                                 * @returns ResourcesResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemResources({
                                    fresh = false,
                                }: {
                                    fresh?: boolean,
                                }): CancelablePromise<ResourcesResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/resources',
                                        query: {
                                            'fresh': fresh,
                                        },
                                        errors: {
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Diagnostic findings derived from /system/resources data (B272)
                                 * Return findings produced by the diagnostic rules engine.
                                 *
                                 * 12 pure-function rules (apps/api/src/services/system_diagnostics.py)
                                 * each produce zero or more named findings with severity, evidence,
                                 * and a recommendation. Cached in-process for 30 seconds; pass
                                 * `?fresh=true` to bypass and re-evaluate.
                                 * @returns DiagnosticsResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemDiagnostics({
                                    fresh = false,
                                }: {
                                    fresh?: boolean,
                                }): CancelablePromise<DiagnosticsResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/diagnostics',
                                        query: {
                                            'fresh': fresh,
                                        },
                                        errors: {
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Time-series for one resource metric over the snapshot window (B273)
                                 * Return [{snapshot_at, value}] over the last N days for one
                                 * metric. Snapshots come from the daily worker
                                 * `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).
                                 *
                                 * Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
                                 * `plugin_size` requires the `plugin` parameter.
                                 * @returns ResourcesHistoryResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemResourcesHistory({
                                    metric,
                                    plugin,
                                    days = 30,
                                }: {
                                    metric: string,
                                    plugin?: (string | null),
                                    days?: number,
                                }): CancelablePromise<ResourcesHistoryResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/resources/history',
                                        query: {
                                            'metric': metric,
                                            'plugin': plugin,
                                            'days': days,
                                        },
                                        errors: {
                                            400: `Unsupported metric or missing required parameter.`,
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Presence-per-snapshot history for one diagnostic finding (B273)
                                 * Return [{snapshot_at, present, severity}] over the last N days
                                 * for one diagnostic finding. The frontend renders this as a
                                 * timeline strip on the expanded FindingCard.
                                 *
                                 * Snapshots without the finding return `present=false, severity=null`.
                                 * @returns DiagnosticsHistoryResponse Successful Response
                                 * @throws ApiError
                                 */
                                public static systemDiagnosticsHistory({
                                    id,
                                    days = 30,
                                }: {
                                    id: string,
                                    days?: number,
                                }): CancelablePromise<DiagnosticsHistoryResponse> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/system/diagnostics/history',
                                        query: {
                                            'id': id,
                                            'days': days,
                                        },
                                        errors: {
                                            400: `Invalid finding_id.`,
                                            401: `Missing or invalid session token.`,
                                            403: `Caller lacks the system.audit permission.`,
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                            }
