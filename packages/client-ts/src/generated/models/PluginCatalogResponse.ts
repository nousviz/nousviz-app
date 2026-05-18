/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PluginEntry } from './PluginEntry';
/**
 * GET /api/plugins/catalog — full plugin catalog (Marketplace page).
 *
 * Combines official + installed + community + utilities. Each entry
 * includes installed flag, install_count, featured flag, pricing_model.
 * Sorted: featured first, then by install_count desc.
 */
export type PluginCatalogResponse = {
    plugins: Array<PluginEntry>;
};

