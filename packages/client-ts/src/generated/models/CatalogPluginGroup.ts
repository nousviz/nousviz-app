/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogTable } from './CatalogTable';
/**
 * All discovered tables for one plugin — used by /catalog/tables.
 */
export type CatalogPluginGroup = {
    /**
     * Plugin slug.
     */
    id: string;
    tables: Array<CatalogTable>;
};

