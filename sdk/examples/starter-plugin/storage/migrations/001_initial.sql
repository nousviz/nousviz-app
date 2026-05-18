-- starter-plugin: 001_initial
-- Creates the plugin's two core tables.
--
-- Rules:
--   - Use CREATE TABLE IF NOT EXISTS (idempotent — safe to run twice)
--   - Use CREATE INDEX IF NOT EXISTS
--   - Table names must be prefixed or scoped to avoid collisions with core tables
--   - All tables declared here must also be listed in plugin.yaml databases.postgres.tables
--   - Every table created here must have a matching DROP in 001_initial_down.sql

CREATE TABLE IF NOT EXISTS starter_items (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL UNIQUE,
    status      TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'inactive', 'archived')),
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS starter_items_status_idx ON starter_items(status);
CREATE INDEX IF NOT EXISTS starter_items_created_at_idx ON starter_items(created_at DESC);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_starter_items_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS starter_items_updated_at ON starter_items;
CREATE TRIGGER starter_items_updated_at
    BEFORE UPDATE ON starter_items
    FOR EACH ROW EXECUTE FUNCTION update_starter_items_updated_at();


CREATE TABLE IF NOT EXISTS starter_events (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT        NOT NULL,   -- 'sync', 'install', 'error', etc.
    detail      JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS starter_events_type_idx     ON starter_events(event_type);
CREATE INDEX IF NOT EXISTS starter_events_created_idx  ON starter_events(created_at DESC);
