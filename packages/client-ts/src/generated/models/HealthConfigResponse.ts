/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Boolean status of security-sensitive config — never the values themselves.
 */
export type HealthConfigResponse = {
    /**
     * True iff NOUSVIZ_ENCRYPTION_KEY is set.
     */
    encryption_key_set: boolean;
    /**
     * True iff AUTH_REQUIRED=true in .env.
     */
    auth_required: boolean;
    /**
     * True iff at least one superadmin user row exists.
     */
    superadmin_exists: boolean;
    /**
     * Always False since S108 (v0.8.1) — kept for response-shape back-compat.
     */
    postgres_password_is_default: boolean;
    /**
     * True iff SMTP_HOST is set.
     */
    smtp_configured: boolean;
    /**
     * True iff a newer release is available on GitHub.
     */
    update_available: boolean;
    /**
     * Latest release tag if known.
     */
    update_latest?: (string | null);
    /**
     * Currently-running version.
     */
    update_current?: (string | null);
};

