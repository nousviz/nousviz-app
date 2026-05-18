/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Aggregate counts surfaced in /health for the operator dashboard.
 */
export type StatsBlock = {
    /**
     * Count of currently-firing alerts.
     */
    active_alerts: number;
    /**
     * Count of configured fusions.
     */
    fusions: number;
    /**
     * Count of operator annotations.
     */
    annotations: number;
    /**
     * Count of plugins installed locally.
     */
    installed_plugins: number;
    /**
     * Count of plugin-managed tables in Postgres.
     */
    plugin_tables: number;
    /**
     * Count of non-revoked shared links.
     */
    active_shares: number;
};

