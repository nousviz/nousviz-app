-- Migration 072: B304 (v0.10.0.5) — plugin admin-session cookies.
--
-- Storage for path-scoped admin-session cookies minted by plugins that
-- declare frontend.admin_proxy: true in their manifest. Each row backs
-- one nv_admin_<plugin_id> cookie.
--
-- The cookie's raw token never lives in the DB — only its SHA256 hash.
-- Validation is server-side: middleware looks up token_hash in this
-- table when it sees the cookie on a /api/plugins/<slug>/admin/*
-- request.
--
-- Mirrors the user_sessions pattern (apps/api/src/routes/auth.py:104+)
-- so plugin admin sessions get the same security model as the existing
-- session story: opaque random tokens, server-side row, revocation by
-- DELETE.
--
-- path_scope is denormalised onto the row (always
-- "/api/plugins/<plugin_id>/admin") so a future audit / debug tool can
-- enumerate "what cookies grant access to which paths" without
-- reconstructing the path from plugin_id at query time.
--
-- Cleanup: rows with expires_at older than NOW() - INTERVAL '7 days'
-- are removed by the existing session-cleanup cron (extension lands in
-- a follow-up); the covering index supports that sweep efficiently.
--
-- No FK on plugin_id (plugin slugs aren't a tracked PK; same pattern as
-- job_alert_subscriptions in migration 069).

CREATE TABLE IF NOT EXISTS plugin_admin_sessions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id    TEXT        NOT NULL,
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT        NOT NULL UNIQUE,
    path_scope   TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL,
    ip_address   INET,
    user_agent   TEXT
);

CREATE INDEX IF NOT EXISTS idx_plugin_admin_sessions_token_hash
    ON plugin_admin_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_plugin_admin_sessions_expires_at
    ON plugin_admin_sessions (expires_at);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_admin_sessions TO nousviz';
    END IF;
END $$;
