/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Generic `{ok, message}` response — used by forgot-password and
 * reset-password to keep the response shape constant across success
 * and silent-no-op paths (enumeration resistance).
 */
export type GenericMessageResponse = {
    ok?: boolean;
    message: string;
};

