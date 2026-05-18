/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LogFilterUser } from './LogFilterUser';
/**
 * GET /api/admin/logs/filters — distinct values for dropdown filters.
 *
 * Limited to events from the last 30 days so the dropdowns don't
 * accumulate stale plugin slugs or deleted users.
 */
export type LogFiltersResponse = {
    plugins: Array<string>;
    users: Array<LogFilterUser>;
};

