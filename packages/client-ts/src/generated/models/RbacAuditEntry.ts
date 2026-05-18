/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single rbac_config_audit row — one RBAC config mutation.
 */
export type RbacAuditEntry = {
    id: number;
    occurred_at: string;
    actor_user_id?: (string | null);
    actor_email?: (string | null);
    actor_role?: (string | null);
    /**
     * One of 'grant', 'revoke', 'clear', 'create_role', 'delete_role', 'impersonate_start', 'impersonate_end', 'password_reset_cli', 'password_reset_request', 'password_reset_completed', 'password_change_self', 'acl_grant', 'acl_revoke', 'set_default_policy'.
     */
    action: string;
    target_role?: (string | null);
    target_permission?: (string | null);
    /**
     * B248 (v0.9.10.7): present on acl_grant / acl_revoke / set_default_policy rows.
     */
    target_resource_type?: (string | null);
    /**
     * B248 (v0.9.10.7): present on acl_grant / acl_revoke rows.
     */
    target_resource_id?: (string | null);
    /**
     * JSONB before-state — shape depends on the action.
     */
    before_state?: null;
    /**
     * JSONB after-state — shape depends on the action.
     */
    after_state?: null;
    note?: (string | null);
};

