/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/datasets/upload — newly stored dataset row.
 *
 * Same shape as DatasetSummary plus the `id` returned by the
 * upsert.
 */
export type DatasetUploadResponse = {
    id: string;
    name: string;
    slug: string;
    row_count: number;
    file_size: number;
    columns: Array<string>;
    column_types: Record<string, string>;
    uploaded_at?: (string | null);
    updated_at?: (string | null);
};

