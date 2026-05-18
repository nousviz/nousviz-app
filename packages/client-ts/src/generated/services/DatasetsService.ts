/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DatasetDeleteResponse } from '../models/DatasetDeleteResponse';
import type { DatasetDetailResponse } from '../models/DatasetDetailResponse';
import type { DatasetsListResponse } from '../models/DatasetsListResponse';
import type { DatasetUploadResponse } from '../models/DatasetUploadResponse';
import type { upload } from '../models/upload';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DatasetsService {
    /**
     * Upload a CSV dataset (multipart form)
     * @returns DatasetUploadResponse Successful Response
     * @throws ApiError
     */
    public static datasetsUpload({
        formData,
    }: {
        formData: upload,
    }): CancelablePromise<DatasetUploadResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/datasets/upload',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                400: `Missing/invalid file or empty CSV.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * List dataset metadata (no data blob)
     * @returns DatasetsListResponse Successful Response
     * @throws ApiError
     */
    public static datasetsList(): CancelablePromise<DatasetsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/datasets',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
            },
        });
    }
    /**
     * Get a dataset including its data matrix (sortable, paginated)
     * @returns DatasetDetailResponse Successful Response
     * @throws ApiError
     */
    public static datasetsDetail({
        slug,
        limit,
        offset,
        sortBy,
        sortOrder = 'asc',
    }: {
        slug: string,
        /**
         * Limit rows (0 = all)
         */
        limit?: number,
        offset?: number,
        sortBy?: (string | null),
        sortOrder?: string,
    }): CancelablePromise<DatasetDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/datasets/{slug}',
            path: {
                'slug': slug,
            },
            query: {
                'limit': limit,
                'offset': offset,
                'sort_by': sortBy,
                'sort_order': sortOrder,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the datasets.read permission.`,
                404: `Dataset not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete a dataset (admin only)
     * @returns DatasetDeleteResponse Successful Response
     * @throws ApiError
     */
    public static datasetsDelete({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<DatasetDeleteResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/datasets/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the system.admin permission.`,
                404: `Dataset not found.`,
                422: `Validation Error`,
            },
        });
    }
}
