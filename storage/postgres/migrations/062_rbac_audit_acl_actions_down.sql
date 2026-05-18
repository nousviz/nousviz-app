-- B248 (v0.9.10.7) phase 7 rollback. Drops the new columns + index +
-- restores the pre-062 CHECK constraint. NOT NULL on target_role is
-- not restored to avoid failing on any acl_* rows already inserted.

DROP INDEX IF EXISTS rbac_config_audit_resource_idx;

ALTER TABLE rbac_config_audit
  DROP COLUMN IF EXISTS target_resource_type,
  DROP COLUMN IF EXISTS target_resource_id;

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.check_constraints
    WHERE constraint_name = 'rbac_config_audit_action_check'
  ) THEN
    ALTER TABLE rbac_config_audit DROP CONSTRAINT rbac_config_audit_action_check;
  END IF;
END $$;

ALTER TABLE rbac_config_audit
  ADD CONSTRAINT rbac_config_audit_action_check
  CHECK (action IN (
    'grant', 'revoke', 'clear', 'create_role', 'delete_role',
    'impersonate_start', 'impersonate_end',
    'password_reset_cli',
    'password_reset_request',
    'password_reset_completed',
    'password_change_self'
  ));
