-- B236 (v0.9.10.0): custom-role rank for impersonation.
--
-- Custom roles default to rank 0 (cannot impersonate anyone) unless the
-- operator sets a value 1-3 at creation or via /api/system/custom-roles
-- update. Rank 4 is reserved for the built-in superadmin role and is
-- not assignable to custom roles.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS via DO block.

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'rbac_custom_roles' AND column_name = 'rank'
  ) THEN
    ALTER TABLE rbac_custom_roles ADD COLUMN rank SMALLINT NOT NULL DEFAULT 0;
    ALTER TABLE rbac_custom_roles ADD CONSTRAINT rbac_custom_roles_rank_check
      CHECK (rank BETWEEN 0 AND 3);
    COMMENT ON COLUMN rbac_custom_roles.rank IS
      'Impersonation rank. 0 = cannot impersonate anyone. 1-3 maps onto '
      'viewer/analyst/admin tier. 4 (superadmin) is not assignable to '
      'custom roles. Set by B236 (v0.9.10.0).';
  END IF;
END $$;
