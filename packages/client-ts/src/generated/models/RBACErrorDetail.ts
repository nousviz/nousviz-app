/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 403 response from the RBAC layer (B227+). Same `detail` field but
 * with a documented format: `Permission denied: this action requires <permission>.`
 */
export type RBACErrorDetail = {
    /**
     * Permission-deny message naming the required permission.
     */
    detail: string;
};

