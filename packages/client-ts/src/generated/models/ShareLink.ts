/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single shared_links row from /api/shares list.
 */
export type ShareLink = {
    share_id: string;
    title?: (string | null);
    page_path: string;
    resource_type: string;
    notes?: (string | null);
    has_password: boolean;
    created_at?: (string | null);
    expires_at?: (string | null);
    access_count?: number;
    last_accessed?: (string | null);
    revoked?: boolean;
    /**
     * True iff the link's expiry has passed at query time.
     */
    expired: boolean;
};

