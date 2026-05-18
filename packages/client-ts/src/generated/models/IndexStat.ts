/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type IndexStat = {
    schema: string;
    table: string;
    name: string;
    size_mb: number;
    scans_lifetime: number;
    tuples_read: number;
    /**
     * True for primary-key indexes. Surfaced so the unused_index diagnostic rule can exclude PKs (load-bearing for INSERT / UPDATE / DELETE + foreign-key lookups regardless of idx_scan count).
     */
    is_primary?: boolean;
    /**
     * True for unique indexes (including PKs). Same exclusion rationale as is_primary — unique indexes enforce a constraint, not just speed up lookups.
     */
    is_unique?: boolean;
};

