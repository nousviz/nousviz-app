-- Nousviz: Notes & Alert Feedback

-- ── Page Notes ───────────────────────────────────────────────────────
-- Time-aware notes attached to specific pages. A note is always visible
-- on its page but grayed out unless the current date range overlaps
-- the note's time range.

CREATE TABLE IF NOT EXISTS notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_path       TEXT NOT NULL,                           -- e.g. "/plugin/plausible-analytics/dashboards/traffic"
    plugin_id       TEXT,                                    -- optional plugin scope

    -- Content
    body            TEXT NOT NULL,                           -- the note text (markdown ok)
    created_by      TEXT NOT NULL DEFAULT 'user',

    -- Time relevance
    date_start      DATE,                                    -- when this note is relevant from
    date_end        DATE,                                    -- when this note is relevant to (null = open-ended)

    -- State
    pinned          BOOLEAN NOT NULL DEFAULT false,
    resolved        BOOLEAN NOT NULL DEFAULT false,          -- mark as resolved/addressed
    archived        BOOLEAN NOT NULL DEFAULT false,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notes_page ON notes(page_path);
CREATE INDEX IF NOT EXISTS idx_notes_plugin ON notes(plugin_id);
CREATE INDEX IF NOT EXISTS idx_notes_dates ON notes(date_start, date_end);

-- ── Alert Feedback ───────────────────────────────────────────────────
-- Tracks user response to every alert trigger. Used to learn which
-- alerts are useful and auto-suggest disabling noisy ones.

CREATE TABLE IF NOT EXISTS alert_triggers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID NOT NULL,                           -- FK to alerts (JSON for now, Postgres later)
    alert_name      TEXT NOT NULL,
    plugin_id       TEXT NOT NULL,

    -- What triggered
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    trigger_data    JSONB NOT NULL DEFAULT '{}',             -- snapshot of what fired (group, values, change%)

    -- User feedback
    feedback        TEXT,                                     -- helpful | dismissed | snoozed | muted | null (no response)
    feedback_at     TIMESTAMPTZ,
    snooze_until    TIMESTAMPTZ,                             -- if snoozed, don't fire again until
    mute_group      TEXT,                                     -- if muted, which group to suppress (e.g. "King Billy")
    feedback_note   TEXT,                                     -- optional user comment on why

    -- Resolution
    resolved        BOOLEAN NOT NULL DEFAULT false,
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alert_triggers_alert ON alert_triggers(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_triggers_plugin ON alert_triggers(plugin_id);
CREATE INDEX IF NOT EXISTS idx_alert_triggers_feedback ON alert_triggers(feedback);
CREATE INDEX IF NOT EXISTS idx_alert_triggers_time ON alert_triggers(triggered_at DESC);

-- Auto-update notes timestamp
CREATE OR REPLACE TRIGGER notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
