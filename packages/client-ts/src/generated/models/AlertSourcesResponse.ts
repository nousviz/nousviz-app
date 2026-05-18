/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlertSourceEntry } from './AlertSourceEntry';
/**
 * GET /api/alerts/sources — grouped by origin (postgres / connections / plugins).
 */
export type AlertSourcesResponse = {
    postgres: Array<AlertSourceEntry>;
    connections: Array<AlertSourceEntry>;
    plugins: Array<AlertSourceEntry>;
};

