/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PluginAuditEntry } from './PluginAuditEntry';
/**
 * GET /api/plugins/audit-log — recent plugin lifecycle events.
 */
export type PluginAuditLogResponse = {
    entries: Array<PluginAuditEntry>;
};

