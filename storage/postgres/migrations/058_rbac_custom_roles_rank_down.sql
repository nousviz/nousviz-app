-- Down-migration for 058_rbac_custom_roles_rank.sql

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'rbac_custom_roles' AND column_name = 'rank'
  ) THEN
    ALTER TABLE rbac_custom_roles DROP CONSTRAINT IF EXISTS rbac_custom_roles_rank_check;
    ALTER TABLE rbac_custom_roles DROP COLUMN rank;
  END IF;
END $$;
