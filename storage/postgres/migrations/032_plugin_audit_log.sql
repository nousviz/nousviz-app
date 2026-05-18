CREATE TABLE IF NOT EXISTS plugin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    action TEXT NOT NULL,
    detail JSONB DEFAULT '{}',
    user_id UUID REFERENCES users(id),
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plugin_audit_plugin ON plugin_audit_log (plugin_id);
CREATE INDEX IF NOT EXISTS idx_plugin_audit_created ON plugin_audit_log (created_at DESC);
