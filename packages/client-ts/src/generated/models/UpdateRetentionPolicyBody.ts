/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * PUT /api/maintenance/retention/{policy_key} body.
 *
 * Either field may be omitted; pass only what's changing.
 */
export type UpdateRetentionPolicyBody = {
    /**
     * New retention threshold (0 means immediate purge of additional_where matches).
     */
    retention_days?: (number | null);
    /**
     * True to pause the policy; false to activate.
     */
    paused?: (boolean | null);
};

