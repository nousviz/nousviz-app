/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/plugins/{id}/install — success path.
 *
 * Returns `status='already_installed'` when the plugin's directory
 * already exists (idempotent). Otherwise `status='installed'` with
 * the manifest plus migrations + route-load status.
 */
export type PluginInstallResponse = Record<string, any>;
