/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type PostgresSummary = {
    db_size_mb: number;
    /**
     * 0-100; target > 99 on a healthy install
     */
    cache_hit_pct: number;
    active_connections: number;
    idle_connections: number;
    max_connections: number;
    pg_stat_statements_installed: boolean;
};

