-- 024_notes_and_activity.sql
-- Postgres-backed storage for notes and activity events.
-- Replaces JSON file storage (notes.json, activity_log.json).
-- See ticket B144.

-- ── Notes ──────────────────────────────────────────────────────────────
-- Page-scoped notes (different from annotations which are chart-scoped).
CREATE TABLE IF NOT EXISTS notes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    page_path   TEXT        NOT NULL,
    plugin_id   TEXT,
    body        TEXT        NOT NULL,
    date_start  DATE,
    date_end    DATE,
    pinned      BOOLEAN     NOT NULL DEFAULT false,
    resolved    BOOLEAN     NOT NULL DEFAULT false,
    archived    BOOLEAN     NOT NULL DEFAULT false,
    created_by  TEXT        NOT NULL DEFAULT 'user',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notes_page_path ON notes (page_path);
CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes (pinned) WHERE pinned = true;

-- ── Activity events ────────────────────────────────────────────────────
-- Page views, actions, plugin interactions. Source for analytics page.
CREATE TABLE IF NOT EXISTS activity_events (
    id          BIGSERIAL   PRIMARY KEY,
    action      TEXT        NOT NULL,
    category    TEXT        NOT NULL DEFAULT 'general',
    page_path   TEXT,
    plugin_id   TEXT,
    detail      JSONB       NOT NULL DEFAULT '{}',
    duration_ms INTEGER,
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_activity_events_created ON activity_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_events_action ON activity_events (action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_events_page ON activity_events (page_path) WHERE page_path IS NOT NULL;
