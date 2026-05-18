/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single resource_acls row.
 */
export type AclGrantRow = {
    id: number;
    resource_type: string;
    resource_id: string;
    principal_kind: string;
    principal_id: string;
    permission: string;
    granted_by?: (string | null);
    note?: (string | null);
    created_at?: (string | null);
};

