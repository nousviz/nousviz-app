/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InviteRow } from './InviteRow';
/**
 * POST /api/auth/users/invite — invite issued.
 *
 * `invite_url` is exposed only when email send failed (operator can
 * copy/paste the link). On successful send, it stays null and only
 * `email_sent=true` is reported.
 */
export type InviteCreateResponse = {
    invite: InviteRow;
    invite_url?: (string | null);
    email_sent: boolean;
    email_error?: (string | null);
};

