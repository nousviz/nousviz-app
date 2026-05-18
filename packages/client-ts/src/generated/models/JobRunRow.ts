/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single job_runs row — used by /api/jobs/runs and /api/jobs/{run_id}.
 *
 * Datetimes are ISO-8601 strings. Extra fields are allowed because the
 * detail endpoint returns more columns than the list endpoint
 * (claimed_by, heartbeat_at, progress, etc).
 */
export type JobRunRow = Record<string, any>;
