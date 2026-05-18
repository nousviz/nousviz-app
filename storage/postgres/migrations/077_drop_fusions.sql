-- Migration 077: Drop the fusions table and the fusions schema (v0.10.0.14).
--
-- Final step of the fusions -> widget builder simplification. By the time
-- this runs the operator should have:
--   1. Deployed v0.10.0.12+ (the /api/fusions backend strip).
--   2. Run scripts/migrate_fusions_to_dashboards.py so existing fusion
--      records are mirrored into user_dashboards.
--
-- DESTRUCTIVE: drops the fusion source-of-truth table + every published
-- view. There is no automatic restore. Take a backup before applying.
--
-- If the migration script wasn't run, fusion records are LOST after this.

-- 1. Drop the publish-side: every view in the fusions schema, plus the
--    schema itself. The CASCADE handles the view dependencies cleanly.
DROP SCHEMA IF EXISTS fusions CASCADE;

-- 2. Drop the source table.
DROP TABLE IF EXISTS fusions;

-- 3. Resource ACLs may carry fusion-typed grants (B248). Remove the
--    dangling rows + the default-policy entry.
DELETE FROM resource_acls WHERE resource_type = 'fusion';
DELETE FROM rbac_resource_defaults WHERE resource_type = 'fusion';
