-- Plugin settings: per-plugin key/value store for operator-configurable fields.
-- key is the field name declared in plugin.yaml settings[].name.
-- value is JSONB so it handles strings, booleans, numbers, and arrays uniformly.

CREATE TABLE IF NOT EXISTS plugin_settings (
    plugin_id   TEXT        NOT NULL,
    key         TEXT        NOT NULL,
    value       JSONB       NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plugin_id, key)
);
