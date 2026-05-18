/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * B280 (v0.9.11.15): per-table data for the honest uninstall modal —
 * name + current row count + size on disk. Drives the "exactly what will
 * be dropped" disclosure block.
 */
export type UninstallCheckTableWithSize = {
    name: string;
    size_mb: number;
    rows: number;
};

