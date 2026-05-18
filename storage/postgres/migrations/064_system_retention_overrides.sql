-- Migration 064: B279 (v0.9.11.17) — automatic retention policies.
--
-- Operator-configurable retention thresholds for log/event/session
-- tables that grow unboundedly by design. The cron worker
-- (apps/worker/src/retention_cleanup.py) reads this table once per
-- day and prunes per active policy.
--
-- Per operator decision 2026-05-04: every policy ships paused. The
-- first daily cron after deploy is a no-op. Operator flips each
-- policy on from /settings/maintenance after reviewing the per-policy
-- "would prune N rows" preview.

CREATE TABLE IF NOT EXISTS system_retention_overrides (
    policy_key            TEXT        PRIMARY KEY,
    retention_days        INTEGER     NOT NULL CHECK (retention_days >= 0),
    paused                BOOLEAN     NOT NULL DEFAULT TRUE,
    last_run_at           TIMESTAMPTZ,
    last_run_rows_deleted INTEGER,
    last_run_error        TEXT,
    updated_by            UUID,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default policy seed. policy_key is the canonical identifier matching
-- the in-code POLICIES registry (apps/api/src/services/retention.py).
-- ON CONFLICT DO NOTHING so re-running this migration on an existing
-- DB doesn't reset any operator-tuned values.
INSERT INTO system_retention_overrides (policy_key, retention_days, paused) VALUES
    ('app_logs',                       30, TRUE),
    ('auth_audit',                     90, TRUE),
    ('health_log',                     30, TRUE),
    ('activity_events',                30, TRUE),
    ('job_runs:success',                7, TRUE),
    ('job_runs:failure',               30, TRUE),
    ('share_access_log',               90, TRUE),
    ('user_sessions:expired',           0, TRUE),
    ('password_reset_tokens:expired',   0, TRUE)
ON CONFLICT (policy_key) DO NOTHING;

-- Grants. nousviz needs full CRUD (cron worker writes last_run_*;
-- API writes paused/retention_days). nousviz_plugin gets nothing —
-- retention is operator-only.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON system_retention_overrides TO nousviz';
    END IF;
END $$;
