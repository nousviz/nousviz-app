-- Migration 074: B304 hotfix (v0.10.0.5.4) — grant plugin_admin_sessions
-- CRUD to the nousviz_plugin role.
--
-- The SDK helper `nousviz_sdk.auth.issue_admin_session_cookie()` calls
-- `nousviz_sdk.db.get_pg_conn()` which connects as the `nousviz_plugin`
-- role (per sdk/nousviz_sdk/db.py:50). Migration 072 only granted CRUD
-- to `nousviz`. Every bridge call on prod 2026-05-11 raised
-- `psycopg2.errors.InsufficientPrivilege: permission denied for table
-- plugin_admin_sessions`.
--
-- Trust-model note: granting plugin-CRUD here means any installed plugin
-- can insert/update/delete rows in this table for any plugin_id. In
-- principle, plugin A could insert a row claiming plugin_id='other-plugin'
-- with a known token_hash and bridge into B's admin proxy as a chosen
-- user. In practice this is redundant with the existing plugin trust
-- surface: plugins already share the `nousviz_plugin` role for all DB
-- access (per P203), and plugin-shipped JS runs with FULL host privileges
-- (per B151) — a malicious plugin can already steal the operator's
-- session token via XSS and use it against any plugin. The B304 trust
-- model relies on plugin review + manifest opt-in (`admin_proxy: true`),
-- not DB-level isolation.
--
-- If a future plugin sandboxing surface is added (per-plugin DB roles,
-- jail by AppArmor, etc.) this grant becomes a security hole and would
-- need re-architecting (dedicated admin-session-mint role, or core
-- exposes the mint helper as an HTTP endpoint instead of a direct SDK
-- call).

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_admin_sessions TO nousviz_plugin';
    END IF;
END $$;
