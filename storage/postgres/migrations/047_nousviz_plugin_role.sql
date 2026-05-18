-- Migration 047 — Plugin-scoped Postgres role (P203 / v0.9.0).
--
-- Defines the privilege boundary between core and plugin code. Plugin
-- subprocesses connect as `nousviz_plugin` via the SDK; this role has:
--
--   • SELECT on reference tables (schema_migrations, plugin_registry, plugin_modules)
--   • INSERT / SELECT on job_runs and app_logs
--   • CRUD on each plugin's own declared tables (granted per-plugin at install time)
--   • NO access to credentials, credential_audit_log, users, api_keys,
--     deploy_keys, plugin_audit_log, or other core-privileged tables
--
-- Role creation (and password generation) happen in scripts/setup.sh as
-- superuser — SQL migrations run as the app user and can't CREATE ROLE.
-- This migration file is the schema-side contract: GRANT and REVOKE
-- statements that the app user (table owner) can issue.
--
-- Idempotent: running against a DB where the role does not yet exist is
-- a no-op (the DO blocks guard with IF EXISTS).

-- Only apply grants if the role exists. Gives a graceful upgrade path —
-- a box that ran migrations before setup.sh created the role won't fail
-- the migration; setup.sh will re-run grants on its next invocation.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        RAISE NOTICE 'nousviz_plugin role does not exist yet; skipping grants. Run scripts/setup.sh to create it.';
        RETURN;
    END IF;

    -- ── Reference tables: SELECT only ─────────────────────────────
    -- Plugins may need to introspect what else is installed, their
    -- own manifest state, etc. Read-only on these.
    GRANT USAGE ON SCHEMA public TO nousviz_plugin;
    GRANT SELECT ON schema_migrations TO nousviz_plugin;
    GRANT SELECT ON plugin_registry TO nousviz_plugin;

    -- plugin_modules (if present) — added in migration 039
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_modules') THEN
        GRANT SELECT ON plugin_modules TO nousviz_plugin;
    END IF;

    -- ── Shared append-only tables: INSERT + narrow SELECT ─────────
    -- Plugins INSERT their own sync/hook rows, and the SDK's
    -- jobs.heartbeat() helper needs UPDATE on its own runs.
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'job_runs') THEN
        GRANT INSERT, SELECT, UPDATE ON job_runs TO nousviz_plugin;
        -- BIGSERIAL primary key needs sequence access
        GRANT USAGE, SELECT ON SEQUENCE job_runs_id_seq TO nousviz_plugin;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'app_logs') THEN
        GRANT INSERT ON app_logs TO nousviz_plugin;
        GRANT USAGE, SELECT ON SEQUENCE app_logs_id_seq TO nousviz_plugin;
    END IF;

    -- ── plugin_settings: plugins manage their own settings ────────
    -- Row-level filtering is enforced in the SDK (settings helpers
    -- always pass plugin_id). RLS policies are a v0.9.4 hardening.
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_settings') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_settings TO nousviz_plugin;
    END IF;

    -- ── Explicit REVOKE for sensitive tables (defense in depth) ───
    -- Nothing was granted, but being explicit about what we block
    -- makes the threat model legible and catches accidental future
    -- grants at review time.
    REVOKE ALL ON credentials FROM nousviz_plugin;
    REVOKE ALL ON credential_audit_log FROM nousviz_plugin;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'users') THEN
        REVOKE ALL ON users FROM nousviz_plugin;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'user_accounts') THEN
        REVOKE ALL ON user_accounts FROM nousviz_plugin;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'user_sessions') THEN
        REVOKE ALL ON user_sessions FROM nousviz_plugin;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'api_keys') THEN
        REVOKE ALL ON api_keys FROM nousviz_plugin;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'deploy_keys') THEN
        REVOKE ALL ON deploy_keys FROM nousviz_plugin;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_audit_log') THEN
        REVOKE ALL ON plugin_audit_log FROM nousviz_plugin;
    END IF;

    RAISE NOTICE 'nousviz_plugin grants applied.';
END $$;
