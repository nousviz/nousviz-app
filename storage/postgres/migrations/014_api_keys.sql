-- Instance-level API keys for programmatic/MCP access.
-- Raw keys are never stored — only a SHA-256 hash and the first 8 chars for display.

CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,                    -- human label, e.g. "MCP Server" or "CI pipeline"
    key_prefix  TEXT NOT NULL,                    -- first 8 chars of raw key, for display
    key_hash    TEXT NOT NULL UNIQUE,             -- SHA-256 of raw key (hex)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ                       -- NULL = active
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
