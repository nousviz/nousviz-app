/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single connections row.
 *
 * `config` is the JSONB blob with the password masked as '••••••••'.
 * Plugin-managed connections have name='plugin:<slug>' and store
 * credentials in the credentials table instead of in config.
 */
export type ConnectionRow = Record<string, any>;
