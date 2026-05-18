-- Nousviz: Connections & Credentials Schema
-- Stores external data source connections and their encrypted API keys/tokens.

-- Connections: external data sources linked to plugins
CREATE TABLE IF NOT EXISTS connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id       TEXT NOT NULL,                          -- e.g. "cloudflare", "plausible-analytics"
    name            TEXT NOT NULL,                          -- user-facing label
    connection_type TEXT NOT NULL,                          -- e.g. "api_key", "mysql", "oauth2"
    status          TEXT NOT NULL DEFAULT 'pending',        -- connected | disconnected | error | pending
    config          JSONB NOT NULL DEFAULT '{}',            -- non-secret config (host, port, region, etc.)

    -- Health tracking
    last_health_check    TIMESTAMPTZ,
    last_successful_sync TIMESTAMPTZ,
    last_error           TEXT,
    consecutive_failures INT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Credentials: encrypted API keys, tokens, passwords
-- The actual secret is AES-256-GCM encrypted; only the app can decrypt it.
CREATE TABLE IF NOT EXISTS credentials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,                          -- e.g. "api_token", "db_password"
    credential_type TEXT NOT NULL,                          -- api_key | api_token | oauth2 | basic_auth | database

    -- Encrypted storage — never store plaintext
    encrypted_value BYTEA NOT NULL,                        -- AES-256-GCM ciphertext + auth tag
    nonce           BYTEA NOT NULL,                        -- 12-byte GCM nonce (unique per encryption)

    -- Audit trail
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_rotated_at      TIMESTAMPTZ,                      -- set when user updates the key
    last_used_at         TIMESTAMPTZ,                      -- set each time a sync reads this credential
    last_used_by         TEXT,                              -- which sync script last used it

    -- Staleness tracking
    rotation_reminder_days INT DEFAULT 365,                 -- warn user after this many days without rotation

    UNIQUE (connection_id, name)                            -- one credential per name per connection
);

-- Credential audit log: immutable record of all credential operations
-- This is write-only — rows are never updated or deleted.
CREATE TABLE IF NOT EXISTS credential_audit_log (
    id            BIGSERIAL PRIMARY KEY,
    credential_id UUID NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    action        TEXT NOT NULL,                            -- created | rotated | used | deleted | health_check_failed
    performed_by  TEXT,                                     -- user or system identifier
    detail        TEXT,                                     -- optional context, e.g. "sync_cf.py daily run"
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_credentials_connection ON credentials(connection_id);
CREATE INDEX IF NOT EXISTS idx_credential_audit_log_credential ON credential_audit_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_credential_audit_log_connection ON credential_audit_log(connection_id);
CREATE INDEX IF NOT EXISTS idx_connections_plugin ON connections(plugin_id);
CREATE INDEX IF NOT EXISTS idx_connections_status ON connections(status);

-- Helper: auto-update updated_at on connections
CREATE OR REPLACE FUNCTION update_connections_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER connections_updated_at
    BEFORE UPDATE ON connections
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
