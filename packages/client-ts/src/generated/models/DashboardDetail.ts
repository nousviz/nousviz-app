/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Full dashboard row.
 *
 * `widgets` and `layout` are JSONB blobs whose shape is defined by the
 * dashboard editor / widget runtime. We accept them verbatim with
 * `extra='allow'` covering any future top-level columns.
 */
export type DashboardDetail = Record<string, any>;
