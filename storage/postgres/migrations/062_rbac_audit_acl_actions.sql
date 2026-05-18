-- B248 (v0.9.10.7) phase 7: extend rbac_config_audit for per-resource
-- ACL events.
--
-- Three new actions land in this migration:
--   acl_grant           — POST /api/resource-acls/{type}/{id} created or upserted a grant
--   acl_revoke          — DELETE /api/resource-acls/{type}/{id}/{grant_id}
--   set_default_policy  — PUT /api/resource-acls/defaults/{type}
--
-- The pre-B248 schema treated `target_role` as the universal "what was
-- mutated" key. ACL events target a (resource_type, resource_id,
-- principal_kind, principal_id) tuple instead. To keep the audit feed
-- self-describing without overloading target_role:
--   1. relax target_role to nullable (ACL events do not name a role
--      directly; the principal lives in after_state)
--   2. add nullable target_resource_type + target_resource_id columns
--      so the existing audit feed UI can render them as native chips
--
-- Rolling forward is safe — every existing row already has target_role
-- populated, and the new columns are nullable.

-- 1. relax target_role NOT NULL
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'rbac_config_audit'
      AND column_name = 'target_role'
      AND is_nullable = 'NO'
  ) THEN
    ALTER TABLE rbac_config_audit ALTER COLUMN target_role DROP NOT NULL;
  END IF;
END $$;

-- 2. add target_resource_type + target_resource_id (nullable)
ALTER TABLE rbac_config_audit
  ADD COLUMN IF NOT EXISTS target_resource_type TEXT,
  ADD COLUMN IF NOT EXISTS target_resource_id   TEXT;

CREATE INDEX IF NOT EXISTS rbac_config_audit_resource_idx
  ON rbac_config_audit (target_resource_type, target_resource_id, occurred_at DESC);

-- 3. extend the CHECK constraint with the three new actions
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
    'password_change_self',
    -- B248 (v0.9.10.7): per-resource ACL events.
    'acl_grant',
    'acl_revoke',
    'set_default_policy'
  ));
