/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/jobs/{run_id}/{cancel|pause|resume} response.
 *
 * `changed` is True when the operation moved the run into a new
 * status; False when the operation was a no-op (e.g. cancelling an
 * already-terminal run).
 */
export type JobRunControlResponse = {
    ok?: boolean;
    changed: boolean;
    /**
     * The run's status after the operation.
     */
    status: string;
};

