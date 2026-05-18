-- B236 (v0.9.10.0): impersonation audit support.
--
-- When a request is made by an actor who is impersonating a target user, the
-- auth_audit row records the actor in user_id (the human responsible) and the
-- target in acting_as_user_id (the effective identity for permission checks).
-- For non-impersonated requests acting_as_user_id is NULL.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS would be cleaner but Postgres doesn't
-- support it; check via information_schema first.

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'auth_audit' AND column_name = 'acting_as_user_id'
  ) THEN
    ALTER TABLE auth_audit ADD COLUMN acting_as_user_id TEXT;
    COMMENT ON COLUMN auth_audit.acting_as_user_id IS
      'When set, the request was made by user_id while impersonating this user. '
      'Set by B236 (v0.9.10.0). NULL for non-impersonated requests.';
  END IF;
END $$;

-- Extend the rbac_config_audit action constraint to allow impersonation events.
-- Using ALTER ... DROP/ADD pattern because Postgres doesn't support modifying
-- CHECK constraints in place.
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
  CHECK (action IN ('grant', 'revoke', 'clear', 'create_role', 'delete_role',
                    'impersonate_start', 'impersonate_end'));
