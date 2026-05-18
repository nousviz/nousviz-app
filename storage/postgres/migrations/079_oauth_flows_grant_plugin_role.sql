-- Migration 079: B312 hotfix (v0.10.3.1) — grant oauth_flows CRUD to the
-- nousviz_plugin role.
--
-- The SDK helper `nousviz_sdk.oauth.start_flow()` calls
-- `nousviz_sdk.db.get_pg_conn()` which connects as the `nousviz_plugin`
-- role (per sdk/nousviz_sdk/db.py:50). Migration 078 only granted CRUD
-- to `nousviz` (the core API role). Every `start_flow` call on prod
-- 2026-05-18 silently failed inside the plugin's start route with
-- `psycopg2.errors.InsufficientPrivilege: permission denied for table
-- oauth_flows`; rows were never persisted, and the subsequent callback
-- hit invalid_state because the state hash had nothing to match.
--
-- Trust-model note: granting plugin-CRUD here means any installed plugin
-- can insert/update/delete rows in this table for any plugin_id. In
-- principle, plugin A could insert a row claiming plugin_id='other-plugin'
-- with a known token_hash, then trick the operator into completing an
-- OAuth dance whose `code` is exchanged by other-plugin's handler under
-- plugin-A's chosen user_id. Practical exploit requires:
--   * knowing plugin-B's exact slug (public via /api/plugins)
--   * triggering plugin-B's handler with a usable provider auth code
--     (which only fires after the provider hand-redirects the operator,
--     and the provider's redirect_uri is configured per-plugin in the
--     provider's dashboard — so plugin A can't force the provider to
--     redirect to plugin B's callback)
-- The B312 trust model relies on plugin review + the provider's own
-- redirect_uri allowlist, not DB-level isolation. Same shape as B304's
-- migration 074.
--
-- If a future plugin sandboxing surface is added (per-plugin DB roles,
-- jail by AppArmor, etc.) this grant becomes a security hole and would
-- need re-architecting (dedicated oauth-state-mint role, or core exposes
-- the mint helper as an HTTP endpoint instead of a direct SDK call).

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_flows TO nousviz_plugin';
    END IF;
END $$;
