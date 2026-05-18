-- Migration 041: Backfill job_runs from legacy plugin_settings._last_sync
--
-- Context: Before v0.7.3, plugin sync status was tracked in two broken ways:
--   (1) SDK BaseSyncScript wrote to a sync_log table that never existed
--   (2) Core UIs read from plugin_settings._last_sync, which no SDK plugin wrote
-- v0.7.3 unifies on job_runs (migration 031). This migration backfills any
-- legacy _last_sync entries so existing installs don't show "Never run" after
-- upgrade. Idempotent via ON CONFLICT DO NOTHING (the primary key is BIGSERIAL,
-- but we dedupe on (job_id, started_at) via a partial unique index first).

-- Partial unique index so the backfill is idempotent
CREATE UNIQUE INDEX IF NOT EXISTS idx_job_runs_backfill_dedupe
    ON job_runs (job_id, started_at)
    WHERE source = 'backfill';

-- Compound index for the common read pattern (jobs UI reads latest success per plugin)
CREATE INDEX IF NOT EXISTS idx_job_runs_job_id_started
    ON job_runs (job_id, started_at DESC);

-- Backfill: pull any _last_sync entries into job_runs as synthetic 'success' rows.
-- Value shape varies: either a JSON string (quoted ISO timestamp) or an object
-- with a "timestamp" key. Handle both; skip anything we can't parse.
INSERT INTO job_runs (job_id, started_at, completed_at, status, source, details)
SELECT
    'sync:' || plugin_id,
    ts,
    ts,
    'success',
    'backfill',
    jsonb_build_object('backfilled_from', '_last_sync')
FROM (
    SELECT
        plugin_id,
        COALESCE(
            -- JSON object with timestamp key
            NULLIF(value->>'timestamp', '')::timestamptz,
            -- Raw JSON string (strip quotes)
            CASE
                WHEN jsonb_typeof(value) = 'string'
                THEN (value #>> '{}')::timestamptz
                ELSE NULL
            END
        ) AS ts
    FROM plugin_settings
    WHERE key = '_last_sync' AND value IS NOT NULL
) parsed
WHERE ts IS NOT NULL
ON CONFLICT (job_id, started_at) WHERE source = 'backfill' DO NOTHING;
