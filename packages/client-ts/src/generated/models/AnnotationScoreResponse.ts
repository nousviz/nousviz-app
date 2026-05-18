/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/annotations/{annotation_id}/score — quick semantic score.
 */
export type AnnotationScoreResponse = {
    /**
     * Always 'scored' on success.
     */
    status?: string;
    /**
     * 'useful' | 'neutral' | 'useless'.
     */
    score: string;
};

