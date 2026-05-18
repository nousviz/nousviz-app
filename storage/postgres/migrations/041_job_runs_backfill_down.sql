-- Revert migration 041: remove backfill rows and indexes.
-- Leaves plugin_settings._last_sync rows untouched (those were the source).

DELETE FROM job_runs WHERE source = 'backfill';

DROP INDEX IF EXISTS idx_job_runs_backfill_dedupe;
DROP INDEX IF EXISTS idx_job_runs_job_id_started;
