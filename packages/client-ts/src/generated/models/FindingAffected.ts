/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One thing the finding is about (a table, sync, index, etc.).
 *
 * `detail` is freeform plain-language extra context (size, row count,
 * timestamp). The frontend renders these as small chips on the
 * expanded card — they're meant to give the operator enough context
 * to act without expanding further.
 */
export type FindingAffected = {
    /**
     * 'table' | 'sync' | 'index' | 'plugin' | 'db' | 'host'.
     */
    type: string;
    name: string;
    detail?: (string | null);
};

