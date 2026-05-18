/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConnectionIssue } from './ConnectionIssue';
/**
 * List of banner-shaped connection health issues across plugins.
 */
export type ConnectionHealthResponse = {
    /**
     * May be empty when no plugin reports an issue.
     */
    issues?: Array<ConnectionIssue>;
};

