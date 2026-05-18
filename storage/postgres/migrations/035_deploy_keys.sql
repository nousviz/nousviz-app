CREATE TABLE IF NOT EXISTS deploy_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    host TEXT NOT NULL DEFAULT 'github.com',
    public_key TEXT NOT NULL,
    private_key_encrypted TEXT NOT NULL,
    fingerprint TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deploy_keys_host ON deploy_keys (host);
