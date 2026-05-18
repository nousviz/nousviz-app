-- User authentication and roles
-- Works with Cloudflare Access (reads email from JWT) or standalone login.

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    name        TEXT,
    avatar_url  TEXT,
    role        TEXT NOT NULL DEFAULT 'viewer',  -- admin | editor | viewer
    auth_method TEXT DEFAULT 'cloudflare',        -- cloudflare | password | api_key
    password_hash TEXT,                           -- only if auth_method = password
    api_key     TEXT UNIQUE,                      -- for programmatic access
    is_active   BOOLEAN NOT NULL DEFAULT true,
    last_login  TIMESTAMPTZ,
    login_count INTEGER NOT NULL DEFAULT 0,
    settings    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Session tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT NOT NULL UNIQUE,
    ip_address  TEXT,
    user_agent  TEXT,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Activity log — who did what
CREATE TABLE IF NOT EXISTS user_activity (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    email       TEXT,
    action      TEXT NOT NULL,           -- login | logout | view | create | update | delete | export | run_agent
    resource    TEXT,                     -- plugin:plausible-analytics | page:settings | agent:nexus-a1
    resource_id TEXT,
    details     JSONB DEFAULT '{}',
    ip_address  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key) WHERE api_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_action ON user_activity(action, created_at DESC);
