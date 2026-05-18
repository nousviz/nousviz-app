-- Nousviz: Activity Log, Plugin Telemetry, Data Overrides

-- ── Activity Log ─────────────────────────────────────────────────────
-- Tracks all user actions in the app for dashboard analytics and audit.

CREATE TABLE IF NOT EXISTS activity_log (
    id              BIGSERIAL PRIMARY KEY,

    -- Who
    user_id         TEXT NOT NULL DEFAULT 'user',
    session_id      TEXT,

    -- What
    action          TEXT NOT NULL,                           -- page_view | query | export | alert_triggered | annotation_created | note_created | connection_added | plugin_installed | setting_changed
    category        TEXT NOT NULL DEFAULT 'general',        -- navigation | data | alert | annotation | plugin | system

    -- Where
    page_path       TEXT,                                    -- e.g. "/plugin/plausible-analytics/dashboards/traffic"
    plugin_id       TEXT,

    -- Details
    detail          JSONB NOT NULL DEFAULT '{}',             -- action-specific data (query text, export filename, alert name, etc.)

    -- Timing
    duration_ms     INT,                                     -- how long the action took (for queries)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_log(action);
CREATE INDEX IF NOT EXISTS idx_activity_page ON activity_log(page_path);
CREATE INDEX IF NOT EXISTS idx_activity_plugin ON activity_log(plugin_id);
CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);

-- ── Plugin Telemetry ─────────────────────────────────────────────────
-- Aggregated, privacy-respecting analytics for plugin creators.
-- Only stores counts and aggregates, never raw user data.

CREATE TABLE IF NOT EXISTS plugin_telemetry (
    id              BIGSERIAL PRIMARY KEY,
    plugin_id       TEXT NOT NULL,
    period          DATE NOT NULL,                           -- aggregation date (daily)

    -- Usage metrics
    active_users    INT NOT NULL DEFAULT 0,
    page_views      INT NOT NULL DEFAULT 0,
    queries_run     INT NOT NULL DEFAULT 0,
    exports         INT NOT NULL DEFAULT 0,
    alerts_fired    INT NOT NULL DEFAULT 0,
    alerts_helpful  INT NOT NULL DEFAULT 0,
    alerts_dismissed INT NOT NULL DEFAULT 0,
    errors          INT NOT NULL DEFAULT 0,

    -- Feature usage
    datasets_queried JSONB NOT NULL DEFAULT '{}',            -- {"reports_raw": 42, "dynamic_variables_raw": 15}
    dashboards_viewed JSONB NOT NULL DEFAULT '{}',           -- {"revenue": 30, "campaigns": 12}

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (plugin_id, period)
);

CREATE INDEX IF NOT EXISTS idx_telemetry_plugin ON plugin_telemetry(plugin_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_period ON plugin_telemetry(period DESC);

-- ── Plugin Telemetry Settings ────────────────────────────────────────
-- Per-user opt-in/out for sharing telemetry with plugin creators.

CREATE TABLE IF NOT EXISTS plugin_telemetry_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id       TEXT NOT NULL,
    share_usage     BOOLEAN NOT NULL DEFAULT false,          -- share usage counts with plugin author
    share_errors    BOOLEAN NOT NULL DEFAULT true,           -- share error reports (no user data, just error types)
    share_feedback  BOOLEAN NOT NULL DEFAULT false,          -- share alert feedback aggregates
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (plugin_id)
);

-- ── Data Overrides ───────────────────────────────────────────────────
-- Virtual data corrections without modifying source data in ClickHouse.
-- Each override targets specific rows and either excludes them or
-- substitutes values.

CREATE TABLE IF NOT EXISTS data_overrides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id       TEXT NOT NULL,
    dataset         TEXT NOT NULL,                           -- e.g. "reports_raw"

    -- Targeting: which rows does this override affect?
    match_filters   JSONB NOT NULL,                          -- e.g. {"program_name": "Bad Program", "date": "2025-12-15"}

    -- Action
    override_type   TEXT NOT NULL,                           -- exclude | replace | adjust
    -- exclude: row is hidden from reports/dashboards
    -- replace: substitute specific column values
    -- adjust: apply a multiplier or offset to numeric columns

    -- Override values (for replace/adjust)
    override_values JSONB NOT NULL DEFAULT '{}',             -- e.g. {"total_com": 150.00} or {"total_com": {"multiply": 0.5}}

    -- Metadata
    reason          TEXT,                                     -- why this override exists
    created_by      TEXT NOT NULL DEFAULT 'user',
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_overrides_plugin ON data_overrides(plugin_id);
CREATE INDEX IF NOT EXISTS idx_overrides_dataset ON data_overrides(dataset);
CREATE INDEX IF NOT EXISTS idx_overrides_active ON data_overrides(active);

-- Auto-update
CREATE OR REPLACE TRIGGER overrides_updated_at
    BEFORE UPDATE ON data_overrides
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
