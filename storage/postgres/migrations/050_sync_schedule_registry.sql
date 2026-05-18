-- Migration 050: sync_schedule_registry (B147 / v0.9.3)
--
-- Per-plugin scheduling state, written by run_scheduler on each poll.
-- Single source of truth for "what cron is this plugin running on" and
-- "when does it next fire."
--
-- Read by:
--   - schedule_active predicate (freshness-based: row + recent updated_at)
--   - GET /api/plugins/{id}/sync-schedule (composite response)
--   - Override UI (next_fire_at preview)
--
-- Written by:
--   - run_scheduler poll loop only

CREATE TABLE IF NOT EXISTS sync_schedule_registry (
    plugin_id          TEXT        PRIMARY KEY,
    cron_expression    TEXT        NOT NULL,
    cron_source        TEXT        NOT NULL,            -- 'manifest' | 'override'
    next_fire_at       TIMESTAMPTZ,
    last_enqueued_at   TIMESTAMPTZ,
    last_run_id        BIGINT,
    last_error         TEXT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sync_schedule_registry_next_fire_idx
    ON sync_schedule_registry(next_fire_at);

CREATE INDEX IF NOT EXISTS sync_schedule_registry_updated_idx
    ON sync_schedule_registry(updated_at);

-- Grants. nousviz needs full CRUD (scheduler runs as nousviz; override
-- endpoint writes as nousviz). nousviz_plugin gets read-only — plugins
-- can inspect their own schedule but never modify it.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON sync_schedule_registry TO nousviz';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'GRANT SELECT ON sync_schedule_registry TO nousviz_plugin';
    END IF;
END $$;
