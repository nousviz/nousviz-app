-- 028_health_log.sql
-- Background health monitoring log. See tickets B138, B140.

CREATE TABLE IF NOT EXISTS health_log (
    id          BIGSERIAL   PRIMARY KEY,
    level       TEXT        NOT NULL DEFAULT 'healthy',  -- healthy | warning | critical
    checks      JSONB       NOT NULL DEFAULT '[]',
    postgres_ok BOOLEAN     NOT NULL DEFAULT true,
    tables      INTEGER,
    version     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_health_log_created ON health_log (created_at DESC);

-- Keep only 30 days of history (cleanup via cron or API)
