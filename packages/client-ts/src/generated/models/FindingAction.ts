/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Action button on a finding card.
 *
 * Phase 1 (v0.9.11.18) supports `external` (link) and `manual`
 * (copy-to-clipboard SQL/shell). The Phase 2 `sql_with_confirmation`
 * type — execute privileged DROP / VACUUM via a confirmation modal
 * — is deferred pending its own audit + RBAC review.
 */
export type FindingAction = {
    type: FindingAction.type;
    label: string;
    /**
     * Route URL for `external` actions.
     */
    url?: (string | null);
    /**
     * SQL to copy-paste for `manual` actions.
     */
    sql?: (string | null);
    /**
     * Shell command for `manual` actions.
     */
    shell?: (string | null);
};
export namespace FindingAction {
    export enum type {
        EXTERNAL = 'external',
        MANUAL = 'manual',
    }
}

