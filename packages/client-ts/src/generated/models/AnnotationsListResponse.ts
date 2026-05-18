/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnnotationRow } from './AnnotationRow';
/**
 * GET /api/annotations — pinned-first ordering, rich filter set.
 */
export type AnnotationsListResponse = {
    annotations: Array<AnnotationRow>;
    count: number;
};

