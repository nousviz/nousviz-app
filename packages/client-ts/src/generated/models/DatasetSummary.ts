/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single datasets row in the list response — metadata only, no `data` blob.
 */
export type DatasetSummary = {
    id: string;
    name: string;
    slug: string;
    description?: (string | null);
    /**
     * Column names in the order they appeared in the source CSV.
     */
    columns?: Array<string>;
    /**
     * Inferred type per column ('number' | 'string' | etc.) — used for sort + render hints.
     */
    column_types?: Record<string, string>;
    row_count?: number;
    /**
     * Total stored size in bytes.
     */
    file_size?: (number | null);
    /**
     * Operator-assigned labels.
     */
    tags?: Array<string>;
    uploaded_at?: (string | null);
    updated_at?: (string | null);
};

