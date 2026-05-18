-- Migration 045: grant INSERT on app_logs to the app user (P114 v0.8.4).
--
-- Context: migration 040 created app_logs owned by postgres superuser and
-- granted SELECT to nousviz_query. The app user (POSTGRES_USER, typically
-- 'nousviz') was never granted INSERT/UPDATE — so the log bridge in
-- apps/api/src/log_handler.py has been silently failing since P104.
-- The failure is caught inside the handler so nothing crashed, but
-- app_logs has been empty since it shipped.
--
-- v0.8.4 P114 adds another app_logs writer (log_events.py for the jobs
-- worker). This migration grants the app user the privileges it needs
-- so both the existing bridge and the new log_job_event helper can
-- actually write.
--
-- Idempotent: GRANT is a no-op if the privilege already exists.

DO $$
DECLARE
    app_role TEXT;
BEGIN
    -- Grant to whichever role currently connects as nousviz app user.
    -- session_user is the OS/login role; current_user can flip via SET
    -- ROLE for the query sandbox, so use session_user here.
    app_role := session_user;
    IF app_role = 'postgres' THEN
        -- Running the migration as postgres — grant to the nousviz role
        -- by name. If someone runs this as a different app user they'll
        -- need to adjust.
        app_role := 'nousviz';
    END IF;
    EXECUTE format('GRANT INSERT ON TABLE app_logs TO %I', app_role);
    EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE app_logs_id_seq TO %I', app_role);
    RAISE NOTICE 'Granted INSERT on app_logs + sequence to %', app_role;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Could not grant app_logs privileges: %', SQLERRM;
END $$;
