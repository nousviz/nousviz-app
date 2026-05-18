/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/data-port/plugins/{plugin_slug}/tab/{tab_id}.
 *
 * Paginated rows from the tab's declared SQL table. `rows` is a list
 * of plugin-table-shaped dicts (column types vary per table), so
 * typed as `list[dict[str, Any]]` rather than a fixed shape.
 */
export type DataportTabRowsResponse = {
    rows: Array<Record<string, any>>;
    total: number;
    page: number;
    page_size: number;
};

