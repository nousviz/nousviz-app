/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/settings/database — current Postgres config without password.
 */
export type DatabaseSettingsResponse = {
    host: string;
    port: string;
    db: string;
    user: string;
    sslmode: string;
};

