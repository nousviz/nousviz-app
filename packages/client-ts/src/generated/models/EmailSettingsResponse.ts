/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/settings/email — SMTP config without password.
 */
export type EmailSettingsResponse = {
    host: string;
    port: string;
    username: string;
    from_address: string;
    from_name: string;
    use_tls: string;
    configured: boolean;
};

