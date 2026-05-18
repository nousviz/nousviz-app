-- Down for migration 079 (B312 hotfix).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON oauth_flows FROM nousviz_plugin';
    END IF;
END $$;
