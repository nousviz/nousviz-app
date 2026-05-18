/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShareAccess } from '../models/ShareAccess';
import type { ShareAccessLogResponse } from '../models/ShareAccessLogResponse';
import type { ShareAccessResponse } from '../models/ShareAccessResponse';
import type { ShareCreate } from '../models/ShareCreate';
import type { ShareCreateResponse } from '../models/ShareCreateResponse';
import type { ShareDetailResponse } from '../models/ShareDetailResponse';
import type { ShareListResponse } from '../models/ShareListResponse';
import type { ShareRevokeResponse } from '../models/ShareRevokeResponse';
import type { ShareUpdate } from '../models/ShareUpdate';
import type { ShareUpdateResponse } from '../models/ShareUpdateResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ShareService {
    /**
     * List all shared links (active and revoked)
     * @returns ShareListResponse Successful Response
     * @throws ApiError
     */
    public static sharesList(): CancelablePromise<ShareListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/shares',
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the shares.read permission.`,
            },
        });
    }
    /**
     * Create a shareable link (optional password + expiry)
     * @returns ShareCreateResponse Successful Response
     * @throws ApiError
     */
    public static sharesCreate({
        requestBody,
    }: {
        requestBody: ShareCreate,
    }): CancelablePromise<ShareCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/shares',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Resource type not shareable.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the shares.write permission.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Public metadata for a share landing page
     * @returns ShareDetailResponse Successful Response
     * @throws ApiError
     */
    public static sharesDetail({
        shareId,
    }: {
        shareId: string,
    }): CancelablePromise<ShareDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/shares/{share_id}',
            path: {
                'share_id': shareId,
            },
            errors: {
                404: `Share link not found.`,
                410: `Link has been revoked or has expired.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update a share link's title and/or notes
     * Update share title and/or notes.
     * @returns ShareUpdateResponse Successful Response
     * @throws ApiError
     */
    public static sharesUpdate({
        shareId,
        requestBody,
    }: {
        shareId: string,
        requestBody: ShareUpdate,
    }): CancelablePromise<ShareUpdateResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/shares/{share_id}',
            path: {
                'share_id': shareId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Empty body.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks the shares.write permission.`,
                404: `Share link not found or already revoked.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revoke a share link
     * @returns ShareRevokeResponse Successful Response
     * @throws ApiError
     */
    public static sharesRevoke({
        shareId,
    }: {
        shareId: string,
    }): CancelablePromise<ShareRevokeResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/shares/{share_id}',
            path: {
                'share_id': shareId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the shares.write permission.`,
                404: `Share link not found or already revoked.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Access a share link (public; password-gated when applicable)
     * @returns ShareAccessResponse Successful Response
     * @throws ApiError
     */
    public static sharesAccess({
        shareId,
        requestBody,
    }: {
        shareId: string,
        requestBody: ShareAccess,
    }): CancelablePromise<ShareAccessResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/shares/{share_id}/access',
            path: {
                'share_id': shareId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Password required or incorrect.`,
                404: `Share link not found.`,
                410: `Share link revoked or expired.`,
                422: `Validation Error`,
                429: `Rate-limited (5 attempts / 60s per share+IP).`,
            },
        });
    }
    /**
     * Last 50 access attempts for a share link
     * Return access log for a share link.
     * @returns ShareAccessLogResponse Successful Response
     * @throws ApiError
     */
    public static sharesAccessLog({
        shareId,
    }: {
        shareId: string,
    }): CancelablePromise<ShareAccessLogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/shares/{share_id}/log',
            path: {
                'share_id': shareId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks the shares.read permission.`,
                422: `Validation Error`,
            },
        });
    }
}
