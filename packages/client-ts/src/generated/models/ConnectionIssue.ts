/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single banner-displayable connection health issue.
 */
export type ConnectionIssue = {
    plugin_id: string;
    /**
     * 'warning' | 'error'
     */
    severity: string;
    message: string;
    detail?: (Record<string, any> | null);
};

