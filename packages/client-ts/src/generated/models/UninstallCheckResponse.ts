/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UninstallCheckDataDir } from './UninstallCheckDataDir';
import type { UninstallCheckDependent } from './UninstallCheckDependent';
import type { UninstallCheckTable } from './UninstallCheckTable';
import type { UninstallCheckTableWithSize } from './UninstallCheckTableWithSize';
/**
 * GET /api/plugins/{id}/uninstall-check — info for the confirmation modal.
 */
export type UninstallCheckResponse = {
    plugin_id: string;
    display_name: string;
    type?: (string | null);
    /**
     * Other installed plugins that depend on this one — uninstalling without cascade is blocked.
     */
    dependents?: Array<UninstallCheckDependent>;
    /**
     * External references to this plugin (fusions, dashboards, etc.).
     */
    references?: Array<any>;
    /**
     * DB tables that would be dropped if remove_data=true.
     */
    tables?: Array<UninstallCheckTable>;
    /**
     * Filesystem data dirs under data/{slug}/ (utility plugins).
     */
    data_dirs?: Array<UninstallCheckDataDir>;
    has_dependents: boolean;
    has_references: boolean;
    has_data: boolean;
    /**
     * Each Postgres table the plugin declares with its current size + row count. Drives the 'exactly what will be dropped' disclosure on the uninstall modal.
     */
    tables_to_drop_if_data_removed?: Array<UninstallCheckTableWithSize>;
    /**
     * Sum of size_mb across tables_to_drop_if_data_removed.
     */
    tables_to_drop_total_size_mb?: number;
    /**
     * len(tables_to_drop_if_data_removed). Frontend uses this to decide whether to render the DELETE button at all.
     */
    tables_to_drop_total_count?: number;
};

