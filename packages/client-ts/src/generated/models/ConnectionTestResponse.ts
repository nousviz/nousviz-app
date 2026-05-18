/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/connections/{conn_id}/test — connectivity probe.
 *
 * `ok` reflects whether the engine accepted the credentials and
 * responded to a version query. `detail` carries the engine version
 * string on success or a short failure description.
 */
export type ConnectionTestResponse = {
    ok: boolean;
    detail?: (string | null);
    error?: (string | null);
};

