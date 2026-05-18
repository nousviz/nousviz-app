/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/docs/{slug} — full doc page content.
 */
export type DocResponse = {
    slug: string;
    title: string;
    section: string;
    /**
     * Markdown body, UTF-8.
     */
    content: string;
};

