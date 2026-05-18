/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SyncScheduleRegistry } from './SyncScheduleRegistry';
/**
 * GET /api/plugins/{id}/sync-schedule — composite read used by the Settings tab.
 */
export type SyncScheduleGetResponse = {
    plugin_id: string;
    /**
     * Cron from plugin.yaml (sync.schedule).
     */
    manifest_cron?: (string | null);
    /**
     * Human label for manifest_cron, when expressible.
     */
    manifest_cron_display?: (string | null);
    override_cron?: (string | null);
    override_cron_display?: (string | null);
    /**
     * override_cron when set, else manifest_cron.
     */
    effective_cron?: (string | null);
    effective_cron_display?: (string | null);
    /**
     * 'override' | 'manifest'.
     */
    source: string;
    registry?: (SyncScheduleRegistry | null);
    /**
     * True iff the scheduler row was updated within the last 5 minutes.
     */
    scheduler_alive: boolean;
};

