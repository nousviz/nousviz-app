/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * DELETE /api/plugins/{id}/install.
 *
 * Two response shapes:
 * - `status='has_dependents'` (when other plugins depend on this one
 * and `cascade=false`): the frontend should prompt the operator to
 * confirm cascade or cancel. `dependents` lists the affected plugins.
 * - `status='uninstalled'` (success): lists what was removed and
 * whether data was kept or dropped.
 */
export type PluginUninstallResponse = Record<string, any>;
