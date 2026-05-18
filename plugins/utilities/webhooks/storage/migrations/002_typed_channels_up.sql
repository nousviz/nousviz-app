-- Plugin migration 002: B283 (v0.9.11.24) — typed webhook channels.
--
-- Adds `channel_type` enum + `channel_config` JSONB to webhook_endpoints
-- so a Slack incoming webhook can render Block Kit instead of the
-- generic flat `text + structured fields` payload.
--
-- channel_type=generic preserves byte-identical behavior (every existing
-- row defaults to it). Operators upgrade individual rows to slack via
-- the webhooks-plugin endpoint editor; channel_config carries the
-- per-channel options (mention_user_ids, mention_on_severities,
-- channel_override).
--
-- Discord and Teams are listed in the CHECK constraint so the schema is
-- ready for follow-up tickets, but the dispatcher only formats Slack
-- specially in B283. Discord/Teams rows that switch to the typed value
-- before the formatters land would receive their generic payload —
-- harmless but undocumented, so the editor disables those options
-- until their tickets ship.

ALTER TABLE webhook_endpoints
    ADD COLUMN IF NOT EXISTS channel_type TEXT NOT NULL DEFAULT 'generic'
        CHECK (channel_type IN ('generic', 'slack', 'discord', 'teams')),
    ADD COLUMN IF NOT EXISTS channel_config JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_channel_type
    ON webhook_endpoints (channel_type) WHERE channel_type <> 'generic';
