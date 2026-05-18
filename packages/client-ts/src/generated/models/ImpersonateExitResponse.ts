/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/auth/impersonate/exit — idempotent, always returns 200.
 */
export type ImpersonateExitResponse = {
    ok?: boolean;
    wasImpersonating: boolean;
};

