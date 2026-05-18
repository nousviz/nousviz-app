-- Down for migration 048. Revoke the explicit grants. Doesn't restore
-- the prior table-ownership state if it was different — that's not
-- recoverable from a migration. In practice this is a no-op for the
-- common case (postgres-owned tables: revoking just removes the explicit
-- grants we added).

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'plugin_modules') THEN
            EXECUTE 'REVOKE ALL ON plugin_modules FROM nousviz';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'plugin_settings') THEN
            EXECUTE 'REVOKE ALL ON plugin_settings FROM nousviz';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'plugin_registry') THEN
            EXECUTE 'REVOKE ALL ON plugin_registry FROM nousviz';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'schema_migrations') THEN
            EXECUTE 'REVOKE ALL ON schema_migrations FROM nousviz';
        END IF;
        -- job_runs / app_logs left intact — revoking would break runtime
    END IF;
END $$;
