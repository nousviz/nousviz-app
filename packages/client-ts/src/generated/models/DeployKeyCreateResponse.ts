/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/settings/deploy-keys — returns the new key's identity + public material.
 *
 * The private key is encrypted with NOUSVIZ_ENCRYPTION_KEY and stored;
 * the response intentionally omits it.
 */
export type DeployKeyCreateResponse = {
    id: string;
    name: string;
    host: string;
    public_key: string;
    fingerprint: string;
};

