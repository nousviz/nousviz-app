-- B248 (v0.9.10.7) down-migration.
-- Drops the resource_acls + rbac_resource_defaults tables and the
-- resource_principal_kind enum. Idempotent.

DROP TABLE IF EXISTS resource_acls;
DROP TABLE IF EXISTS rbac_resource_defaults;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resource_principal_kind') THEN
        DROP TYPE resource_principal_kind;
    END IF;
END$$;
