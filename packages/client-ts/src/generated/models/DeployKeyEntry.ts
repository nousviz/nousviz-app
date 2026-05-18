/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeployKeyCreator } from './DeployKeyCreator';
/**
 * A single deploy_keys row as returned by GET /api/settings/deploy-keys.
 */
export type DeployKeyEntry = {
    id: string;
    name: string;
    host: string;
    repo_url?: (string | null);
    public_key: string;
    fingerprint?: (string | null);
    created_at?: (string | null);
    /**
     * The actor who created this key. Null if the user has been deleted.
     */
    created_by?: (DeployKeyCreator | null);
};

