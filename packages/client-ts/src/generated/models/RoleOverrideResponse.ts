/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/system/role-overrides — newly written override row.
 */
export type RoleOverrideResponse = {
    id: number;
    role: string;
    permission: string;
    /**
     * 'grant' | 'revoke'.
     */
    kind: string;
    created_by: string;
    created_at: string;
    note?: (string | null);
};

