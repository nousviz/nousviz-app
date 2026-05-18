-- Migration 048: Grant nousviz CRUD on core platform tables (B142 / v0.9.2.2)
--
-- Symptom: on a fresh install where migrations are applied by the postgres
-- superuser, core platform tables (plugin_modules, plugin_settings, etc.)
-- end up owned by `postgres`, not `nousviz`. The API process running as
-- `nousviz` then can't INSERT into them, and multi-module plugin install
-- fails with `permission denied for table plugin_modules`.
--
-- Migration 045 grants `app_logs` to nousviz; migration 047 covers
-- nousviz_plugin's grants on job_runs / app_logs. This migration closes
-- the remaining hole: the API role's writes on every core platform table
-- it manages.
--
-- Idempotent — re-running re-issues the same GRANTs.

DO $$
BEGIN
    -- plugin_modules (migration 039) — install flow inserts on auto-enable
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_modules') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_modules TO nousviz';
    END IF;

    -- plugin_settings (migration 020) — connection-field saves write here
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_settings') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_settings TO nousviz';
    END IF;

    -- plugin_registry — install handler upserts
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_registry') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_registry TO nousviz';
    END IF;

    -- schema_migrations — applied-migration tracking
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'schema_migrations') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON schema_migrations TO nousviz';
    END IF;

    -- job_runs / app_logs — same gap that setup.sh already covers as a
    -- belt-and-braces backfill. Adding here so the schema-side contract
    -- is self-contained.
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'job_runs') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON job_runs TO nousviz';
        IF EXISTS (SELECT 1 FROM information_schema.sequences
                   WHERE sequence_schema = 'public' AND sequence_name = 'job_runs_id_seq') THEN
            EXECUTE 'GRANT USAGE, SELECT, UPDATE ON SEQUENCE job_runs_id_seq TO nousviz';
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'app_logs') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON app_logs TO nousviz';
        IF EXISTS (SELECT 1 FROM information_schema.sequences
                   WHERE sequence_schema = 'public' AND sequence_name = 'app_logs_id_seq') THEN
            EXECUTE 'GRANT USAGE, SELECT, UPDATE ON SEQUENCE app_logs_id_seq TO nousviz';
        END IF;
    END IF;
END $$;
