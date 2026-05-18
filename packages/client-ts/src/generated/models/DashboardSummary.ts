/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Compact dashboard row from the list endpoint — widgets blob
 * replaced by `widget_count`.
 */
export type DashboardSummary = {
    id: string;
    name: string;
    slug: string;
    description?: (string | null);
    /**
     * Plugin/dataset references; shape is dashboard-author-defined.
     */
    sources?: Array<any>;
    created_by?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    widget_count?: number;
};

