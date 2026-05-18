-- Down-migration for 059_password_reset_tokens.sql

DROP INDEX IF EXISTS idx_password_reset_tokens_active;
DROP INDEX IF EXISTS idx_password_reset_tokens_user_id;
DROP TABLE IF EXISTS password_reset_tokens;

-- Restore the rbac_config_audit action constraint to its pre-B251 shape
-- (no password_* actions). Note: any existing rows with password_* actions
-- will fail the new constraint and the migration will abort. That's
-- intentional — operators rolling back B251 must scrub those rows first.
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
    'impersonate_start', 'impersonate_end'
  ));
