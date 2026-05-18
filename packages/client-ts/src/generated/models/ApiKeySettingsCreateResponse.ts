/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/settings/api-keys — newly created key (raw key included once).
 */
export type ApiKeySettingsCreateResponse = {
    id: string;
    name: string;
    key_prefix: string;
    /**
     * Raw API key — shown exactly once at creation.
     */
    key: string;
    created_at?: (string | null);
    message: string;
};

