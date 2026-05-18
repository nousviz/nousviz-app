/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/settings/database — confirms write + post-write probe.
 *
 * `version` is the live Postgres version when the new connection
 * succeeds. `error` carries the failure message when the new config
 * can't connect (the .env was still patched — operator can fix and
 * retry).
 */
export type DatabaseSaveResponse = {
    ok: boolean;
    version?: (string | null);
    error?: (string | null);
};

