-- Migration 043 — Async job queue schema extensions
--
-- Adds the columns and statuses needed for the async job worker (P107)
-- and the skipped status for concurrency policy (P108). Bundled into one
-- migration because both land in v0.8.2 and the status CHECK constraint
-- must be rewritten once, not twice.
--
-- New columns:
--   progress        — plugin-written progress snapshot (rows_done, etc.)
--   cancelled_at    — when operator requested cancel
--   paused_at       — when operator requested pause
--   claimed_by      — worker identity ('hostname:pid') for debugging
--   claimed_at      — when worker took the queued row
--   heartbeat_at    — last time plugin called heartbeat(); used by the
--                     worker to detect dead subprocesses
--
-- New statuses: queued, cancelling, cancelled, paused (P107), skipped (P108)

ALTER TABLE job_runs
    ADD COLUMN IF NOT EXISTS progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS claimed_by TEXT,
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

-- Replace the status CHECK constraint to include the new states.
ALTER TABLE job_runs DROP CONSTRAINT IF EXISTS job_runs_status_check;
ALTER TABLE job_runs ADD CONSTRAINT job_runs_status_check
    CHECK (status IN (
        'queued',      -- P107: waiting for worker to claim
        'running',     -- existing
        'success',     -- existing
        'error',       -- existing
        'timeout',     -- existing
        'cancelling',  -- P107: operator requested cancel mid-run
        'cancelled',   -- P107: plugin exited cleanly after cancel
        'paused',      -- P107: operator requested pause; resume re-queues
        'skipped'      -- P108: concurrency policy suppressed this run
    ));

-- Worker poll index: only needs to scan queued rows, which are a tiny
-- fraction of the total. Partial index keeps it small.
CREATE INDEX IF NOT EXISTS idx_job_runs_queued
    ON job_runs (started_at)
    WHERE status = 'queued';

-- Heartbeat-based orphan detection: worker on startup finds rows that are
-- still 'running' but haven't heartbeat'd recently. Partial index again
-- because only 'running' rows matter for this check.
CREATE INDEX IF NOT EXISTS idx_job_runs_running_heartbeat
    ON job_runs (heartbeat_at)
    WHERE status = 'running';
