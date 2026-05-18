/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FrontendComponentEntry } from './FrontendComponentEntry';
/**
 * GET /api/plugins/{id}/frontend-components.
 */
export type PluginFrontendComponentsResponse = {
    plugin_id: string;
    components: Array<FrontendComponentEntry>;
    trusted: boolean;
    needs_consent: boolean;
    /**
     * B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path. Surfaced here so the trust banner can render the admin-proxy consent line.
     */
    admin_proxy?: boolean;
};

