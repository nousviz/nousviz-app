-- Migration 069: B284 (v0.9.11.23) — per-job-run failure alert
-- subscriptions.
--
-- Complements B274's system-level diagnostic alerts. Where B274 fires
-- on critical-finding state changes ("4 syncs are consistently
-- failing"), B284 fires on individual job_runs terminal transitions
-- ("sync:quickbooks errored at 14:32"). Reuses the same webhook
-- delivery path + HMAC signing + Slack `text` shim.
--
-- plugin_id = '*' is the wildcard ("any plugin"); otherwise it's a
-- plugin slug like 'quickbooks'. on_status filters which terminal
-- statuses fire the alert (default: error + timeout — operators don't
-- typically want notifications for cancelled runs).
--
-- webhook_id references webhook_endpoints.id (UUID). No FK constraint
-- because the webhooks plugin may be uninstalled; the bridge handles
-- a missing target gracefully (logs + skips).
--
-- UNIQUE (plugin_id, webhook_id): prevents duplicate subscriptions.
-- An operator who wants different status filters for the same
-- (plugin, webhook) pair can update the existing row's on_status.

CREATE TABLE IF NOT EXISTS job_alert_subscriptions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id    TEXT        NOT NULL,
    on_status    TEXT[]      NOT NULL DEFAULT ARRAY['error','timeout']::TEXT[],
    webhook_id   UUID        NOT NULL,
    enabled      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_by   UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (plugin_id, webhook_id)
);

CREATE INDEX IF NOT EXISTS idx_job_alert_subscriptions_active_plugin
    ON job_alert_subscriptions (plugin_id) WHERE enabled = TRUE;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON job_alert_subscriptions TO nousviz';
    END IF;
END $$;
