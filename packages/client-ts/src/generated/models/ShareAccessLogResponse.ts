/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShareAccessLogEntry } from './ShareAccessLogEntry';
/**
 * GET /api/shares/{share_id}/log — last 50 access attempts.
 */
export type ShareAccessLogResponse = {
    log: Array<ShareAccessLogEntry>;
    count: number;
};

