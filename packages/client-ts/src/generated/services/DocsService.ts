/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DocResponse } from '../models/DocResponse';
import type { DocsListResponse } from '../models/DocsListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DocsService {
    /**
     * Index of available documentation pages
     * List all available documentation pages.
     *
     * Pages are allowlisted in DOCS_INDEX — no filesystem traversal. The
     * `available` flag reflects whether the markdown file exists on disk
     * so the frontend can grey-out stale entries during dev.
     * @returns DocsListResponse Successful Response
     * @throws ApiError
     */
    public static docsList(): CancelablePromise<DocsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/docs',
            errors: {
                401: `Missing or invalid session token.`,
            },
        });
    }
    /**
     * Full markdown body of a documentation page
     * Return the markdown content of a documentation page by slug.
     * @returns DocResponse Successful Response
     * @throws ApiError
     */
    public static docsDetail({
        slug,
    }: {
        slug: string,
    }): CancelablePromise<DocResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/docs/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                401: `Missing or invalid session token.`,
                404: `Slug not in allowlist or file missing on disk.`,
                422: `Validation Error`,
            },
        });
    }
}
