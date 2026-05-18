/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/shares/{share_id}/access — public landing-page access.
 *
 * Returns the page-path + filters needed to render the shared view.
 * Filters is a free-form JSONB blob defined by the dashboard author.
 */
export type ShareAccessResponse = {
    page_path: string;
    title?: (string | null);
    /**
     * Free-form filter state (date range, dimension selections, etc.) — dashboard-author-defined shape.
     */
    filters?: Record<string, any>;
};

