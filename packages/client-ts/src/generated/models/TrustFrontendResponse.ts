/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FrontendComponent } from './FrontendComponent';
/**
 * POST /api/plugins/{id}/trust-frontend.
 */
export type TrustFrontendResponse = {
    plugin_id: string;
    trusted?: boolean;
    /**
     * Components now permitted to render after operator trust grant.
     */
    components?: Array<FrontendComponent>;
};

