-- Migration 040: Application logs table (P104)
-- Operator-visible logs for plugin install, sync, credentials, health checks.

CREATE TABLE IF NOT EXISTS app_logs (
    id          BIGSERIAL PRIMARY KEY,
    level       TEXT NOT NULL,
    source      TEXT NOT NULL,
    message     TEXT NOT NULL,
    detail      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_logs_source ON app_logs (source);
CREATE INDEX IF NOT EXISTS idx_app_logs_level ON app_logs (level);
CREATE INDEX IF NOT EXISTS idx_app_logs_created ON app_logs (created_at DESC);

-- Grant SELECT to nousviz_query for the admin logs endpoint
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'nousviz_query') THEN
        GRANT SELECT ON app_logs TO nousviz_query;
    END IF;
END $$;
