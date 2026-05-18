/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * GET /api/shares/{share_id} — public metadata for the share landing page.
 *
 * Returns 410 (gone) for revoked or expired links — the response below
 * is the success path only.
 */
export type ShareDetailResponse = {
    share_id: string;
    title?: (string | null);
    page_path: string;
    resource_type: string;
    has_password: boolean;
    expires_at?: (string | null);
};

