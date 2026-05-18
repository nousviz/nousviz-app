/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/catalog/plugins/{plugin_id}/tables/{table_name}/rows.
 */
export type CatalogTableRowsResponse = {
    rows: Array<Record<string, any>>;
    total: number;
    page: number;
    limit: number;
};

