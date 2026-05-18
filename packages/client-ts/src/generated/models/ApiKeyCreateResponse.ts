/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/auth/users/{user_id}/api-key.
 *
 * The raw key is returned exactly once — store it immediately.
 */
export type ApiKeyCreateResponse = {
    /**
     * Raw API key (nv_<random>); shown only on creation.
     */
    api_key: string;
    message: string;
};

