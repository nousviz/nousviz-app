-- B233 (v0.9.9.1) rollback. Drops the custom roles table.
--
-- Destructive — operator-created custom roles vanish. Override rows
-- in rbac_role_overrides referencing these custom roles become
-- orphaned but harmless (the resolver returns empty for unknown roles).

DROP TABLE IF EXISTS rbac_custom_roles;
