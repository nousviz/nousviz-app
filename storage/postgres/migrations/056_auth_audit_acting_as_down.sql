-- Down-migration for 056_auth_audit_acting_as.sql

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'auth_audit' AND column_name = 'acting_as_user_id'
  ) THEN
    ALTER TABLE auth_audit DROP COLUMN acting_as_user_id;
  END IF;
END $$;

-- Restore the original action check constraint (without impersonate_*).
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
  CHECK (action IN ('grant', 'revoke', 'clear', 'create_role', 'delete_role'));
