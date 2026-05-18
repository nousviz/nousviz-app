/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/admin/cli — operator CLI command output.
 *
 * `ok` is True only when the command parsed and the handler returned
 * without raising. The `output` field is the human-readable text the
 * UI prints in the CLI panel.
 */
export type CliResponse = {
    output: string;
    ok: boolean;
};

