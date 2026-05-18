/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Plugin loader runtime state (P204).
 *
 * `routes_registered=true` means the plugin's api/routes.py imported
 * cleanly at API startup. False means the loader caught an exception;
 * `failure_reason` carries the class + message (the full traceback
 * stays in app_logs for admin-visible debugging).
 */
export type LoadStatus = {
    routes_registered: boolean;
    /**
     * Where the loader was when it failed.
     */
    stage?: (string | null);
    failure_reason?: (string | null);
};

