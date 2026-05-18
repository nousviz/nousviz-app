/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FrontendComponent } from './FrontendComponent';
/**
 * Frontend trust + component declarations (B151).
 */
export type FrontendBlock = {
    /**
     * React components declared in the plugin's frontend.components manifest block.
     */
    components?: Array<FrontendComponent>;
    trusted: boolean;
    needs_consent: boolean;
    /**
     * B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path. When true, the auth middleware accepts a nv_admin_<slug> cookie for requests under /api/plugins/<slug>/admin* in addition to the existing X-Session-Token / X-API-Key headers. Cookies are minted by the plugin's own bridge endpoint via nousviz_sdk.auth.issue_admin_session_cookie(). Default false: middleware enforces header-based auth as today.
     */
    admin_proxy?: boolean;
};

