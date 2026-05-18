/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AnnotationCreate = {
    title: string;
    description?: (string | null);
    source?: string;
    category?: string;
    severity?: string;
    color?: (string | null);
    plugin_id?: (string | null);
    dataset?: (string | null);
    date_start: string;
    date_end?: (string | null);
    scope_filters?: Record<string, any>;
    tags?: Array<string>;
    pinned?: boolean;
    semantic_meaning?: (string | null);
    impact_scope?: Array<string>;
    semantic_score?: (string | null);
    semantic_note?: (string | null);
};

