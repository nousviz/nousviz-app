/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/settings/deploy-keys/check — does a key exist for `repo_url`?
 *
 * `match='repo'` indicates an exact-URL match (B204). The legacy
 * host-fallback was removed; only exact URL hits return has_key=True.
 */
export type DeployKeyCheckResponse = {
    has_key: boolean;
    key_name?: (string | null);
    /**
     * 'repo' for exact URL match.
     */
    match?: (string | null);
};

