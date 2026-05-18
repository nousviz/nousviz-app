-- Plugin migration 002 down: B283 (v0.9.11.24) — drop typed channels.

DROP INDEX IF EXISTS idx_webhook_endpoints_channel_type;

ALTER TABLE webhook_endpoints
    DROP COLUMN IF EXISTS channel_type,
    DROP COLUMN IF EXISTS channel_config;
