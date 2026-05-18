/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IndexStat } from './IndexStat';
import type { PluginStat } from './PluginStat';
import type { PostgresSummary } from './PostgresSummary';
import type { ServerResources } from './ServerResources';
import type { SyncStat } from './SyncStat';
import type { TableStat } from './TableStat';
/**
 * GET /api/system/resources — all server + Postgres + per-plugin metrics in one snapshot.
 */
export type ResourcesResponse = {
    /**
     * ISO 8601; cached 30s
     */
    collected_at: string;
    server: ServerResources;
    postgres: PostgresSummary;
    /**
     * Top 50 by total size
     */
    tables?: Array<TableStat>;
    /**
     * Sorted by total size desc
     */
    plugins?: Array<PluginStat>;
    /**
     * Sorted by cpu_load_pct_estimate desc
     */
    syncs?: Array<SyncStat>;
    /**
     * Top 20 by size
     */
    indexes_largest?: Array<IndexStat>;
};

