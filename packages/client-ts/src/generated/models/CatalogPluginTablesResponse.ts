/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogTable } from './CatalogTable';
/**
 * GET /api/catalog/plugins/{plugin_id}/tables.
 *
 * Returns empty `tables` (not 404) when the plugin has no discovered
 * tables, so the frontend can render an empty state.
 */
export type CatalogPluginTablesResponse = {
    plugin_id: string;
    tables: Array<CatalogTable>;
    /**
     * Output of catalog.detect_manifest_drift — shape varies, may be null.
     */
    manifest_drift?: any;
};

