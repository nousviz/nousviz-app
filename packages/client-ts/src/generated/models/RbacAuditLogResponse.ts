/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RbacAuditEntry } from './RbacAuditEntry';
/**
 * GET /api/system/rbac-audit-log — paginated RBAC config mutations.
 *
 * Pagination is keyset on `id` descending. Pass `next_cursor` back as
 * `?cursor=…` to fetch the next page.
 */
export type RbacAuditLogResponse = {
    entries: Array<RbacAuditEntry>;
    next_cursor?: (number | null);
};

