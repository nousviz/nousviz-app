/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single api_keys row (prefix + metadata only — never the raw key).
 */
export type ApiKeyEntry = {
    id: string;
    name: string;
    key_prefix: string;
    created_at?: (string | null);
    last_used_at?: (string | null);
};

