/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result of running a plugin's setup_schema.py or health_check.py.
 *
 * Both endpoints return the same shape: subprocess exit code plus
 * combined stdout+stderr. `status` is 'success' on returncode 0,
 * 'error' otherwise. Used by the plugin Settings tab to surface the
 * setup/health output to the operator.
 */
export type PluginScriptRunResponse = {
    /**
     * 'success' | 'error' (derived from subprocess exit code).
     */
    status: string;
    /**
     * Combined stdout + stderr from the plugin script.
     */
    output: string;
    /**
     * The subprocess exit code.
     */
    exit_code: number;
};

