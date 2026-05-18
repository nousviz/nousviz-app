-- Migration 039: Plugin modules table (P103)
-- Tracks which modules within a plugin are enabled/disabled.

CREATE TABLE IF NOT EXISTS plugin_modules (
    plugin_id   TEXT NOT NULL,
    module_name TEXT NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT true,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plugin_id, module_name)
);
