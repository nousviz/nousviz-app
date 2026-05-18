/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SSLBlock } from './SSLBlock';
import type { StatsBlock } from './StatsBlock';
/**
 * Top-level /health payload.
 *
 * Status is degraded when Postgres reports degraded, the SDK is
 * unavailable, or critical tables are missing. Frontend `evaluateChecks`
 * drives banner display from this shape.
 */
export type HealthResponse = {
    /**
     * Overall instance status. 'healthy' | 'degraded'.
     */
    status: string;
    /**
     * Platform version (matches /VERSION).
     */
    version: string;
    /**
     * When this API process started, ISO-8601.
     */
    startup_time: string;
    /**
     * When this response was generated, ISO-8601.
     */
    timestamp: string;
    /**
     * Per-service health blocks. The 'postgres' key always exists with shape {status, version?, tables?, critical_tables_present?, critical_tables_total?, missing_critical_tables?, drift_hint?}. Utility-plugin entries have shape {status, version?}.
     */
    services?: Record<string, any>;
    /**
     * Runtime check blocks. Currently contains 'sdk' with shape {status, version, import_error?}.
     */
    runtime?: Record<string, any>;
    stats: StatsBlock;
    /**
     * SSL config status. Present iff NOUSVIZ_SSL is set in the environment.
     */
    ssl?: (SSLBlock | null);
};

