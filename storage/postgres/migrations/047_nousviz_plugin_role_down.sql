-- Rollback for migration 047. Revokes all grants from nousviz_plugin
-- (the role itself is dropped in setup.sh's tear-down path, not here —
-- SQL migrations run as the app user and can't DROP ROLE).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        RETURN;
    END IF;

    REVOKE ALL ON SCHEMA public FROM nousviz_plugin;
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM nousviz_plugin;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM nousviz_plugin;
END $$;
