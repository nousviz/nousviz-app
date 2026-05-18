/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ServerResourcesCpu } from './ServerResourcesCpu';
import type { ServerResourcesDisk } from './ServerResourcesDisk';
import type { ServerResourcesLoad } from './ServerResourcesLoad';
import type { ServerResourcesMemory } from './ServerResourcesMemory';
import type { ServerResourcesSwap } from './ServerResourcesSwap';
/**
 * Server-level metrics. Fields are Optional because the API runs
 * on Linux production but also on macOS dev (no /proc/meminfo etc.).
 */
export type ServerResources = {
    cpu?: (ServerResourcesCpu | null);
    memory?: (ServerResourcesMemory | null);
    swap?: (ServerResourcesSwap | null);
    disk_root?: (ServerResourcesDisk | null);
    load?: (ServerResourcesLoad | null);
    uptime_seconds?: (number | null);
};

