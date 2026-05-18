/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type QueryResponse = {
    columns: Array<string>;
    types: Array<string>;
    rows: Array<Record<string, any>>;
    row_count: number;
    total_rows_available?: (number | null);
    truncated?: boolean;
    elapsed_ms: number;
    db_engine?: string;
    guardrails?: (Record<string, any> | null);
};

