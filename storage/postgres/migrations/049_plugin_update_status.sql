-- Migration 049: plugin_update_status (B144 / v0.9.2.4)
--
-- Caches per-plugin "is there an update available" status so the UI can
-- render an "Update plugin" button with version diff without doing a
-- network roundtrip on every page load.
--
-- Populated lazily by the API process when an operator hits the plugins
-- list (entries older than 1h get refreshed in the background). Also
-- written by the explicit POST /api/plugins/{id}/check-update endpoint.

CREATE TABLE IF NOT EXISTS plugin_update_status (
    plugin_id          TEXT        PRIMARY KEY,
    source_class       TEXT,                                 -- first_party | git
    source_url         TEXT,                                 -- repo URL for git-installed; null for first_party
    installed_version  TEXT,
    latest_version     TEXT,
    update_available   BOOLEAN     NOT NULL DEFAULT FALSE,
    last_error         TEXT,                                 -- non-null when last check failed
    checked_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS plugin_update_status_checked_at_idx
    ON plugin_update_status(checked_at);

GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_update_status TO nousviz;
