/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The structured detail body returned by `requires_step_up` (B236)
 * and `PATCH /api/auth/me` with password (B251). Frontend's StepUpController
 * keys off `detail.error == 'stepup_required'` to pop the modal.
 */
export type StepUpRequiredErrorBody = {
    /**
     * Stable machine-readable error code.
     */
    error?: string;
    /**
     * Human-readable explanation.
     */
    message: string;
};

