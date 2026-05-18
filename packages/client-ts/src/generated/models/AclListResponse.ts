/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AclGrantRow } from './AclGrantRow';
/**
 * GET /api/resource-acls/{type}/{id}.
 */
export type AclListResponse = {
    resource_type: string;
    resource_id: string;
    default_policy: string;
    grants: Array<AclGrantRow>;
};

