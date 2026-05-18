/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/auth/step-up — re-auth confirmed.
 */
export type StepUpResponse = {
    /**
     * ISO-8601 timestamp until which sensitive ops are unlocked (default 5 min).
     */
    step_up_until: string;
};

