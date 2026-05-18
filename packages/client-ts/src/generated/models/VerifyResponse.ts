/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/auth/verify — token introspection.
 *
 * Returns `{valid: false}` for any invalid/expired/missing token; the
 * caller-friendly fields are only set when the token resolves to an
 * active user.
 */
export type VerifyResponse = {
    valid: boolean;
    email?: (string | null);
    role?: (string | null);
};

