/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/system/custom-roles — newly created custom role.
 */
export type CustomRoleCreateResponse = {
    role: string;
    display_name: string;
    description?: (string | null);
    based_on?: (string | null);
    /**
     * Sorted seed permission set after sensitive-permission filtering.
     */
    permissions?: Array<string>;
    created_by: string;
};

