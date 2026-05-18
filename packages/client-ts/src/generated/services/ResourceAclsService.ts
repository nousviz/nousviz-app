/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AclDefaultPolicyResponse } from '../models/AclDefaultPolicyResponse';
import type { AclGrantResponse } from '../models/AclGrantResponse';
import type { AclListResponse } from '../models/AclListResponse';
import type { AclRevokeResponse } from '../models/AclRevokeResponse';
import type { DefaultPolicyUpdate } from '../models/DefaultPolicyUpdate';
import type { GrantCreate } from '../models/GrantCreate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ResourceAclsService {
    /**
     * List per-resource ACL grants + default policy for a resource
     * @returns AclListResponse Successful Response
     * @throws ApiError
     */
    public static resourceAclsList({
        resourceType,
        resourceId,
    }: {
        resourceType: string,
        resourceId: string,
    }): CancelablePromise<AclListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/resource-acls/{resource_type}/{resource_id}',
            path: {
                'resource_type': resourceType,
                'resource_id': resourceId,
            },
            errors: {
                400: `Unknown resource_type.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks rbac.edit.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Grant a permission on a resource to a role or user
     * @returns AclGrantResponse Successful Response
     * @throws ApiError
     */
    public static resourceAclsGrant({
        resourceType,
        resourceId,
        requestBody,
    }: {
        resourceType: string,
        resourceId: string,
        requestBody: GrantCreate,
    }): CancelablePromise<AclGrantResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/resource-acls/{resource_type}/{resource_id}',
            path: {
                'resource_type': resourceType,
                'resource_id': resourceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid principal_kind or unknown resource_type.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks rbac.edit.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revoke a per-resource ACL grant by id
     * @returns AclRevokeResponse Successful Response
     * @throws ApiError
     */
    public static resourceAclsRevoke({
        resourceType,
        resourceId,
        grantId,
    }: {
        resourceType: string,
        resourceId: string,
        grantId: number,
    }): CancelablePromise<AclRevokeResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/resource-acls/{resource_type}/{resource_id}/{grant_id}',
            path: {
                'resource_type': resourceType,
                'resource_id': resourceId,
                'grant_id': grantId,
            },
            errors: {
                401: `Missing or invalid session token.`,
                403: `Caller lacks rbac.edit.`,
                404: `Grant not found.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get the default policy for a resource type
     * @returns AclDefaultPolicyResponse Successful Response
     * @throws ApiError
     */
    public static resourceAclsGetDefaultPolicy({
        resourceType,
    }: {
        resourceType: string,
    }): CancelablePromise<AclDefaultPolicyResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/resource-acls/defaults/{resource_type}',
            path: {
                'resource_type': resourceType,
            },
            errors: {
                400: `Unknown resource_type.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks rbac.edit.`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Set the default policy for a resource type ('allow' or 'deny')
     * @returns AclDefaultPolicyResponse Successful Response
     * @throws ApiError
     */
    public static resourceAclsSetDefaultPolicy({
        resourceType,
        requestBody,
    }: {
        resourceType: string,
        requestBody: DefaultPolicyUpdate,
    }): CancelablePromise<AclDefaultPolicyResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/resource-acls/defaults/{resource_type}',
            path: {
                'resource_type': resourceType,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Invalid policy or unknown resource_type.`,
                401: `Missing or invalid session token.`,
                403: `Caller lacks rbac.edit.`,
                422: `Validation Error`,
            },
        });
    }
}
