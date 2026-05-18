-- Migration 078: B312 (v0.10.3) — plugin OAuth callback flow state.
--
-- Backs the core-owned OAuth callback at GET /api/oauth/callback/{slug}.
--
-- The plugin starts the flow via nousviz_sdk.oauth.start_flow(...), which
-- writes one row here binding an opaque state token to the originating
-- user, the plugin that initiated the flow, and the return_to URL we'll
-- redirect to once the provider hands back the auth code. Provider then
-- redirects the user's browser to /api/oauth/callback/{slug}?code=...&
-- state=...; the core handler validates the state row, marks it consumed
-- (single-use), and dispatches to the plugin's declared callback handler.
--
-- Only the SHA256 hash of the state token is stored — the raw value lives
-- briefly in the URL bar and the provider's records. Mirrors the
-- user_sessions / plugin_admin_sessions pattern: opaque random tokens,
-- server-side row, single-use semantics via `consumed_at`.
--
-- consumed_at NOT NULL after a successful match prevents replay (a second
-- request with the same `state` hits the WHERE consumed_at IS NULL guard
-- and finds no row). Rows older than NOW() - INTERVAL '24 hours' are swept
-- by the existing cleanup cron; the covering index supports that sweep.
--
-- No FK on plugin_id (plugin slugs aren't a tracked PK; same pattern as
-- plugin_admin_sessions in migration 072).

CREATE TABLE IF NOT EXISTS oauth_flows (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    state_token_hash  TEXT        NOT NULL UNIQUE,
    plugin_id         TEXT        NOT NULL,
    user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    return_to         TEXT        NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ NOT NULL,
    consumed_at       TIMESTAMPTZ,
    ip_address        INET,
    user_agent        TEXT
);

CREATE INDEX IF NOT EXISTS idx_oauth_flows_state_token_hash
    ON oauth_flows (state_token_hash);

CREATE INDEX IF NOT EXISTS idx_oauth_flows_expires_at
    ON oauth_flows (expires_at);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_flows TO nousviz';
    END IF;
END $$;
