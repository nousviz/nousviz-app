-- Revert migration 045.
-- Revokes INSERT on app_logs from the nousviz app user. After revert,
-- the log bridge in log_handler.py + log_events.py will silently fail
-- again (matching pre-v0.8.4 behavior).

DO $$
DECLARE
    app_role TEXT;
BEGIN
    app_role := session_user;
    IF app_role = 'postgres' THEN
        app_role := 'nousviz';
    END IF;
    EXECUTE format('REVOKE INSERT ON TABLE app_logs FROM %I', app_role);
    EXECUTE format('REVOKE USAGE, SELECT ON SEQUENCE app_logs_id_seq FROM %I', app_role);
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Could not revoke app_logs privileges: %', SQLERRM;
END $$;
