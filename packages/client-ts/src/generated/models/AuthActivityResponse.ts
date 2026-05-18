/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthActivityRow } from './AuthActivityRow';
/**
 * GET /api/auth/activity — admin-only audit view.
 */
export type AuthActivityResponse = {
    activity: Array<AuthActivityRow>;
};

