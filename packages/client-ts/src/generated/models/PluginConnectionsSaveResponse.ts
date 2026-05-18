/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SaveConnectionsHealthBlock } from './SaveConnectionsHealthBlock';
/**
 * POST /api/plugins/{id}/connections — confirms write + post-save health check.
 */
export type PluginConnectionsSaveResponse = {
    ok?: boolean;
    /**
     * Result of the plugin's health_check hook, or null if none declared.
     */
    health?: (SaveConnectionsHealthBlock | null);
};

