/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/system/permissions — full RBAC registry snapshot.
 *
 * Used by the audit matrix UI on /system/permissions. The deep
 * blocks (role_data, routes, audit_summary) are typed as
 * dict[str, Any] / list[dict[str, Any]] because they carry per-role
 * and per-route metadata whose shape varies (built-in vs custom
 * roles, overrides present vs absent, etc.).
 */
export type PermissionsMatrixResponse = Record<string, any>;
