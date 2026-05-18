/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single insight from a Tier 1 (YAML) or Tier 2 (plugin endpoint) source.
 *
 * Insight shape is plugin-author-defined; the consistent envelope is
 * `severity` + a free-form payload. extra='allow' covers
 * plugin-specific fields like `metric`, `evidence`, `actions`, etc.
 */
export type InsightEntry = Record<string, any>;
