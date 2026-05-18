/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/settings/email/test — send a test email + report outcome.
 */
export type EmailTestResponse = {
    ok: boolean;
    error?: (string | null);
    sent_to?: (string | null);
};

