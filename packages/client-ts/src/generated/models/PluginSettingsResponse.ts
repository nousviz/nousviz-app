/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PluginSettingEntry } from './PluginSettingEntry';
/**
 * GET /api/plugins/{id}/settings — current saved settings.
 *
 * `_conn.*` keys are excluded (they belong to the /connections surface).
 */
export type PluginSettingsResponse = {
    /**
     * Saved settings, one entry per declared key in the manifest's settings block.
     */
    settings?: Array<PluginSettingEntry>;
};

