/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/launchpad — single-call data feed for the Overview page.
 *
 * Each block is best-effort populated from a separate query inside the
 * handler; failures roll back the inner transaction and leave the
 * block at its empty default.
 */
export type LaunchpadResponse = Record<string, any>;
