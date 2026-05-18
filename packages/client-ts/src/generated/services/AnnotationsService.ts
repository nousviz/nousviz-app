/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnnotationCreate } from '../models/AnnotationCreate';
import type { AnnotationDeleteResponse } from '../models/AnnotationDeleteResponse';
import type { AnnotationHistoryResponse } from '../models/AnnotationHistoryResponse';
import type { AnnotationRow } from '../models/AnnotationRow';
import type { AnnotationScoreResponse } from '../models/AnnotationScoreResponse';
import type { AnnotationsListResponse } from '../models/AnnotationsListResponse';
import type { AnnotationUndoResponse } from '../models/AnnotationUndoResponse';
import type { AnnotationUpdate } from '../models/AnnotationUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AnnotationsService {
    /**
     * List annotations (pinned-first; rich filter set)
     * @returns AnnotationsListResponse Successful Response
     * @throws ApiError
     */
    public static annotationsList({
        pluginId,
        dataset,
        category,
        dateFrom,
        dateTo,
        semanticScore,
        pinned,
        includeArchived = false,
        limit = 200,
    }: {
        pluginId?: (string | null),
        dataset?: (string | null),
        category?: (string | null),
        dateFrom?: (string | null),
        dateTo?: (string | null),
        semanticScore?: (string | null),
        pinned?: (boolean | null),
        includeArchived?: boolean,
        limit?: number,
    }): CancelablePromise<AnnotationsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/annotations',
            query: {
                'plugin_id': pluginId,
                'dataset': dataset,
                'category': category,
                'date_from': dateFrom,
                'date_to': dateTo,
                'semantic_score': semanticScore,
                'pinned': pinned,
                'include_archived': includeArchived,
                'limit': limit,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create an annotation (writes a 'created' history snapshot)
     * @returns AnnotationRow Successful Response
     * @throws ApiError
     */
    public static annotationsCreate({
        requestBody,
    }: {
        requestBody: AnnotationCreate,
    }): CancelablePromise<AnnotationRow> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/annotations',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get a single annotation
     * @returns AnnotationRow Successful Response
     * @throws ApiError
     */
    public static annotationsDetail({
        annotationId,
    }: {
        annotationId: string,
    }): CancelablePromise<AnnotationRow> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/annotations/{annotation_id}',
            path: {
                'annotation_id': annotationId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.read permission.`,
                404: `Annotation not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update an annotation (writes an 'updated' history snapshot)
     * @returns AnnotationRow Successful Response
     * @throws ApiError
     */
    public static annotationsUpdate({
        annotationId,
        requestBody,
    }: {
        annotationId: string,
        requestBody: AnnotationUpdate,
    }): CancelablePromise<AnnotationRow> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/annotations/{annotation_id}',
            path: {
                'annotation_id': annotationId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.write permission.`,
                404: `Annotation not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete an annotation (soft by default; permanent=true to hard-delete)
     * @returns AnnotationDeleteResponse Successful Response
     * @throws ApiError
     */
    public static annotationsDelete({
        annotationId,
        permanent = false,
    }: {
        annotationId: string,
        permanent?: boolean,
    }): CancelablePromise<AnnotationDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/annotations/{annotation_id}',
            path: {
                'annotation_id': annotationId,
            },
            query: {
                'permanent': permanent,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.write permission.`,
                404: `Annotation not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Full change history for an annotation (newest-first)
     * Show the full change history for an annotation.
     * @returns AnnotationHistoryResponse Successful Response
     * @throws ApiError
     */
    public static annotationsHistory({
        annotationId,
    }: {
        annotationId: string,
    }): CancelablePromise<AnnotationHistoryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/annotations/{annotation_id}/history',
            path: {
                'annotation_id': annotationId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.read permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Restore the annotation to its previous state
     * Restore the annotation to its state before the last change.
     *
     * Two outcomes: undoing a 'created' action archives the annotation
     * (since there's nothing to restore to); undoing an 'updated' action
     * restores the previous snapshot and removes that history entry.
     * @returns AnnotationUndoResponse Successful Response
     * @throws ApiError
     */
    public static annotationsUndo({
        annotationId,
    }: {
        annotationId: string,
    }): CancelablePromise<AnnotationUndoResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/annotations/{annotation_id}/undo',
            path: {
                'annotation_id': annotationId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.write permission.`,
                404: `No undoable history.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Quick semantic score (useful | neutral | useless)
     * Quick-score an annotation as useful / neutral / useless.
     * @returns AnnotationScoreResponse Successful Response
     * @throws ApiError
     */
    public static annotationsScore({
        annotationId,
        score,
        note,
    }: {
        annotationId: string,
        score: string,
        note?: (string | null),
    }): CancelablePromise<AnnotationScoreResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/annotations/{annotation_id}/score',
            path: {
                'annotation_id': annotationId,
            },
            query: {
                'score': score,
                'note': note,
            },
            errors: {
                400: `Invalid score value.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the annotations.write permission.`,
                404: `Annotation not found.`,
                422: `Validation Error`,
            },
        });
    }
}
