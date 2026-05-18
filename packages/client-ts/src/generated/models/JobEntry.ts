/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single row in /api/jobs response — one schedulable job.
 *
 * Plugin sync jobs carry the additional fields `manifest_schedule`,
 * `override`, and `scheduler` (B150 — surfacing the v0.9.3 scheduler
 * state to the operator UI). Core jobs (alerts-runner, health-monitor)
 * omit those.
 */
export type JobEntry = Record<string, any>;
