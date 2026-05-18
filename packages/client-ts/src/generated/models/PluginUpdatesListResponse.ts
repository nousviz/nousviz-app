/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PluginUpdateInfo } from './PluginUpdateInfo';
/**
 * GET /api/plugins/updates — bulk status across every installed plugin.
 */
export type PluginUpdatesListResponse = {
    updates: Array<PluginUpdateInfo>;
};

