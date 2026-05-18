-- 025_alert_rules.sql
-- Postgres-backed alert definitions. Replaces apps/alerts.json.
-- See ticket N1.

CREATE TABLE IF NOT EXISTS alert_rules (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT        NOT NULL,
    label            TEXT        NOT NULL,
    description      TEXT,
    plugin_id        TEXT,
    dataset          TEXT        NOT NULL,
    db_engine        TEXT        NOT NULL DEFAULT 'postgres',
    metric           TEXT        NOT NULL,
    aggregation      TEXT        NOT NULL DEFAULT 'sum',
    condition_type   TEXT        NOT NULL DEFAULT 'threshold_drop',
    threshold        DOUBLE PRECISION,
    compare_to       TEXT        DEFAULT '7d_avg',
    scope            TEXT        NOT NULL DEFAULT 'all',
    group_by         TEXT,
    scope_filters    JSONB       NOT NULL DEFAULT '{}',
    check_frequency  TEXT        NOT NULL DEFAULT 'daily',
    check_period     TEXT        NOT NULL DEFAULT 'yesterday',
    cooldown_hours   INTEGER     NOT NULL DEFAULT 24,
    min_baseline     DOUBLE PRECISION NOT NULL DEFAULT 0,
    notify_channels  TEXT[]      NOT NULL DEFAULT '{}',
    enabled          BOOLEAN     NOT NULL DEFAULT true,
    is_template      BOOLEAN     NOT NULL DEFAULT false,
    last_triggered   TIMESTAMPTZ,
    trigger_count    INTEGER     NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_plugin ON alert_rules (plugin_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules (enabled) WHERE enabled = true;
