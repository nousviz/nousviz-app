/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/settings/git — boolean status + masked token preview.
 *
 * Never exposes the full token. The `github_token_preview` field is
 * `<first8>...<last4>` for tokens longer than 12 chars, or '••••'
 * when only short/redacted tokens are stored.
 */
export type GitSettingsGetResponse = {
    /**
     * True iff GITHUB_TOKEN is set in the environment.
     */
    github_token_set: boolean;
    /**
     * Masked preview of the token. Empty string when no token is set.
     */
    github_token_preview: string;
};

