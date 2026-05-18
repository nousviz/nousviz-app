/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/admin/ssl/setup — Let's Encrypt provisioning result.
 *
 * On success, `ssl` carries the new SSL config (mirrors `_get_ssl_status`).
 * On failure, `reason` carries a machine-readable classification (e.g.
 * 'timeout', 'dns_no_match') and `error` carries the human-readable message.
 */
export type SslSetupResponse = Record<string, any>;
