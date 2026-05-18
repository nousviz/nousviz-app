/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * POST /api/settings/deploy-keys/{key_id}/test — SSH-auth probe.
 *
 * `ok=True` means GitHub responded 'successfully authenticated'. The
 * `detail` carries either the short SSH stderr or a timeout / failure
 * description.
 */
export type DeployKeyTestResponse = {
    ok: boolean;
    /**
     * Truncated SSH output (200 chars) or error description.
     */
    detail: string;
};

