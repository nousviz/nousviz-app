/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Index entry for a documentation page.
 */
export type DocEntry = {
    /**
     * URL-safe identifier, used as the path segment.
     */
    slug: string;
    title: string;
    /**
     * Top-level grouping for the docs sidebar.
     */
    section: string;
    /**
     * True iff the markdown file exists on disk.
     */
    available: boolean;
};

