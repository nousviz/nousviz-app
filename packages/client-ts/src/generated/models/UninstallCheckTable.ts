/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Table that would be dropped if remove_data=true.
 */
export type UninstallCheckTable = {
    table: string;
    /**
     * 'postgres' | 'clickhouse' | etc.
     */
    engine: string;
};

