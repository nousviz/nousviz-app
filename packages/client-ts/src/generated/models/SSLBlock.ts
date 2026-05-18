/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * SSL config status when NOUSVIZ_SSL is set. Absent on HTTP-only deployments.
 *
 * Shape mirrors `_get_ssl_status()` in routes/health.py — `enabled`
 * and `type` are always present; `domain` and `expires` are present
 * when applicable.
 */
export type SSLBlock = {
    /**
     * Always True when this block is present.
     */
    enabled: boolean;
    /**
     * SSL provisioning mode, e.g. 'letsencrypt'.
     */
    type: string;
    /**
     * Configured domain when set.
     */
    domain?: (string | null);
    /**
     * Cert expiry as reported by `openssl x509 -enddate`. Present only when the cert is readable.
     */
    expires?: (string | null);
};

