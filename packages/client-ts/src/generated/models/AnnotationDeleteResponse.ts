/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * DELETE /api/annotations/{annotation_id}.
 *
 * `permanent=true` actually deletes; default is soft-delete (archived=true).
 */
export type AnnotationDeleteResponse = {
    /**
     * Always 'deleted' (soft or hard).
     */
    status?: string;
    permanent: boolean;
};

