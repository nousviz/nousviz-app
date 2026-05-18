/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LogEntry } from './LogEntry';
/**
 * GET /api/admin/logs — paginated log feed.
 *
 * Pagination is keyset on `id` descending. When `next_cursor` is
 * non-null, pass it back as the `cursor` query param to fetch the
 * next page. A null cursor means the response was shorter than
 * `limit` and there are no more rows.
 */
export type LogsListResponse = {
    logs: Array<LogEntry>;
    /**
     * ID of the last entry; pass back as ?cursor=… to paginate.
     */
    next_cursor?: (number | null);
};

