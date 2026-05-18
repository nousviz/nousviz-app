/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single plugin entry from /plugins or /plugins/{id}.
 *
 * Carries the consistent envelope (id, version, display_name, status)
 * plus any number of plugin-author-defined fields (dashboards,
 * datasets, actions, settings, capabilities, …). The `extra='allow'`
 * config is intentional — plugin manifests are open-ended.
 */
export type PluginEntry = Record<string, any>;
