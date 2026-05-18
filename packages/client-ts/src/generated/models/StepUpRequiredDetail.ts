/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StepUpRequiredErrorBody } from './StepUpRequiredErrorBody';
/**
 * 401 response from any endpoint gated by `requires_step_up`.
 * The `detail` field is a structured dict, not a string.
 */
export type StepUpRequiredDetail = {
    detail: StepUpRequiredErrorBody;
};

