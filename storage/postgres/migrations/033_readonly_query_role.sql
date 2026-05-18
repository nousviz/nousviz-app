-- Read-only role for the query API (B200 #1, B101)
-- User queries execute via SET ROLE nousviz_query, which has
-- SELECT-only grants on plugin-declared tables. Core tables
-- (users, user_sessions, api_keys, etc.) are never accessible.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nousviz_query') THEN
        CREATE ROLE nousviz_query NOLOGIN;
    END IF;

    -- Ensure current user can SET ROLE and GRANT this role.
    -- Uses ADMIN OPTION so non-superusers can manage it.
    -- Handles both fresh installs (role just created) and existing
    -- installs (role already existed from another database).
    BEGIN
        EXECUTE 'GRANT nousviz_query TO ' || quote_ident(current_user) || ' WITH ADMIN OPTION';
    EXCEPTION WHEN OTHERS THEN
        -- If we can't grant ADMIN (e.g. shared cluster, no superuser),
        -- try a plain grant so SET ROLE still works.
        BEGIN
            EXECUTE 'GRANT nousviz_query TO ' || quote_ident(current_user);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Could not grant nousviz_query to %. Query sandboxing may not work. A superuser can fix this: GRANT nousviz_query TO % WITH ADMIN OPTION;', current_user, current_user;
        END;
    END;
END
$$;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO nousviz_query;

-- Plugin table grants are handled by each plugin's own install/migration
-- scripts, not by core migrations. Plugins should grant nousviz_query
-- SELECT on their tables when they create them.