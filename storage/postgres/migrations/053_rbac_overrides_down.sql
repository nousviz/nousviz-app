-- B232 (v0.9.9.0) rollback. Drops the table and its index.
--
-- Note: this is destructive once operators have started editing RBAC
-- via the v0.9.9.1 UI. Only safe to run if rolling back a deployment
-- that hasn't yet ingested any operator overrides. After v0.9.9.1
-- ships, deleting this table loses operator policy data.

DROP INDEX IF EXISTS rbac_role_overrides_role_idx;
DROP TABLE IF EXISTS rbac_role_overrides;
