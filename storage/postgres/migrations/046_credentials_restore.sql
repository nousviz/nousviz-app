-- 046_credentials_restore.sql (v0.8.6.3 / B128)
--
-- Migration 022_drop_dead_tables dropped the `credentials` and
-- `credential_audit_log` tables in v0.3.x era, but they are required by
-- plugin_credentials.py / store_plugin_credential — any plugin trying to
-- save a secret field hits a "relation does not exist" error at runtime.
-- The tables were never recreated by a later migration, so every install
-- that ran 022 has been silently broken for this path.
--
-- This migration restores both tables using the v0.8.x-compatible schema
-- (matching plugin_credentials.py expectations). Uses IF NOT EXISTS so
-- installs where the tables still exist (never ran 022, or already healed
-- by B128's hotfix path) are no-ops.

CREATE TABLE IF NOT EXISTS credentials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    credential_type TEXT NOT NULL,                          -- api_key | api_token | oauth2 | basic_auth | database
    encrypted_value BYTEA NOT NULL,                        -- AES-256-GCM ciphertext + auth tag
    nonce           BYTEA NOT NULL,                        -- 12-byte GCM nonce (unique per encryption)
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_rotated_at      TIMESTAMPTZ,
    last_used_at         TIMESTAMPTZ,
    last_used_by         TEXT,
    rotation_reminder_days INT DEFAULT 365,
    UNIQUE (connection_id, name)
);

CREATE TABLE IF NOT EXISTS credential_audit_log (
    id            BIGSERIAL PRIMARY KEY,
    credential_id UUID NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    action        TEXT NOT NULL,                            -- created | rotated | used | deleted | health_check_failed
    performed_by  TEXT,                                     -- user or system identifier
    detail        TEXT,                                     -- optional context
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credentials_connection ON credentials(connection_id);
CREATE INDEX IF NOT EXISTS idx_credential_audit_log_credential ON credential_audit_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_credential_audit_log_connection ON credential_audit_log(connection_id);
