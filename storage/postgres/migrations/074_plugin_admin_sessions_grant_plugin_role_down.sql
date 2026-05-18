-- Down for migration 074 (B304 hotfix).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON plugin_admin_sessions FROM nousviz_plugin';
    END IF;
END $$;
