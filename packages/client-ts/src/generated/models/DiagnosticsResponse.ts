/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DiagnosticsSummary } from './DiagnosticsSummary';
import type { Finding } from './Finding';
/**
 * GET /api/system/diagnostics.
 */
export type DiagnosticsResponse = {
    collected_at: string;
    summary: DiagnosticsSummary;
    findings: Array<Finding>;
};

