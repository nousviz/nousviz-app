/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type GrantCreate = {
    /**
     * 'role' or 'user'.
     */
    principal_kind: string;
    /**
     * Role name or user_id.
     */
    principal_id: string;
    /**
     * e.g. dashboards.read, fusions.write.
     */
    permission: string;
    note?: (string | null);
};

