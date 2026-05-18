/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/shares — link issued.
 */
export type ShareCreateResponse = {
    share_id: string;
    /**
     * Relative URL of the share landing page (/shared/<id>).
     */
    url: string;
    has_password: boolean;
    expires_at?: (string | null);
};

