-- Migration 080: B342 (v1.0.8) — credential usage telemetry without a row per read.
--
-- Before B342 every credential read wrote one `credential_audit_log` row per
-- credential the plugin owned (a bulk read of 2,281 credentials wrote 2,281
-- rows), so a busy plugin wrote hundreds of millions of rows a day.
--
-- From B342:
--   * credential_usage_daily: one row per credential, per day, per accessor,
--     with a read counter and first/last time. "When, how often and by what"
--     at a bounded size.
--   * credential_audit_log keeps events (created, rotated, deleted,
--     decrypt_failed, access_denied) and one `fetch` row per broker or bulk
--     request. A `fetch` row is about the request, not one credential, so
--     credential_id may now be NULL.
--   * An index for the retention policy on (action, created_at).

CREATE TABLE IF NOT EXISTS credential_usage_daily (
    credential_id UUID        NOT NULL REFERENCES credentials(id) ON DELETE CASCADE,
    day           DATE        NOT NULL,
    accessor      TEXT        NOT NULL,                 -- api:<plugin> | broker:<plugin> | settings_read | ...
    reads         BIGINT      NOT NULL DEFAULT 0,
    first_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (credential_id, day, accessor)
);

CREATE INDEX IF NOT EXISTS idx_credential_usage_daily_last_at ON credential_usage_daily(last_at);

ALTER TABLE credential_audit_log ALTER COLUMN credential_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_credential_audit_log_action_created
    ON credential_audit_log(action, created_at);
