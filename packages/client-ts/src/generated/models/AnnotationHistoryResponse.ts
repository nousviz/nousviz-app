/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnnotationHistoryEntry } from './AnnotationHistoryEntry';
/**
 * GET /api/annotations/{annotation_id}/history.
 */
export type AnnotationHistoryResponse = {
    history: Array<AnnotationHistoryEntry>;
    count: number;
};

