/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type TableStat = {
    schema: string;
    name: string;
    /**
     * Plugin slug, or null for host-owned tables
     */
    plugin?: (string | null);
    total_size_mb: number;
    data_mb: number;
    index_mb: number;
    rows: number;
    dead_rows: number;
    dead_pct: number;
    last_vacuum?: (string | null);
    last_analyze?: (string | null);
    seq_scan_count: number;
    idx_scan_count: number;
    seq_scan_pct: number;
};

