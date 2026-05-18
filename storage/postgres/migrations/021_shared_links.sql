-- Shared links: password-protected, expiring shareable URLs for dashboards.
-- Replaces the JSON file-based storage from the original share.py.

CREATE TABLE IF NOT EXISTS shared_links (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_id    TEXT UNIQUE NOT NULL,               -- URL-safe token (128-bit entropy)
    resource_type TEXT NOT NULL DEFAULT 'dashboard', -- what kind of thing is shared
    page_path   TEXT NOT NULL,                      -- e.g. /plugin/hello-nousviz/analytics
    title       TEXT,
    filters     JSONB NOT NULL DEFAULT '{}',
    password_hash TEXT,                             -- bcrypt hash, null = public
    expires_at  TIMESTAMPTZ NOT NULL,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked     BOOLEAN NOT NULL DEFAULT false,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS shared_links_share_id_idx ON shared_links(share_id);
CREATE INDEX IF NOT EXISTS shared_links_expires_idx ON shared_links(expires_at);

-- Access log for shared links
CREATE TABLE IF NOT EXISTS share_access_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_id    TEXT NOT NULL REFERENCES shared_links(share_id) ON DELETE CASCADE,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address  TEXT,
    user_agent  TEXT,
    success     BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS share_access_log_share_id_idx ON share_access_log(share_id);
