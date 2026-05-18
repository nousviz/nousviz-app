/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/jobs/{job_id}/fire-now response.
 *
 * For plugin sync jobs, this returns the same shape as POST
 * /api/plugins/{id}/sync (the SyncResponse from B205). The fields
 * here mirror that shape with `extra='allow'` to absorb any keys the
 * underlying handler adds.
 */
export type FireNowResponse = Record<string, any>;
