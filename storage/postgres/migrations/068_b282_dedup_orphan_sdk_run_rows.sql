-- Migration 068: B282 (v0.9.11.22) — backfill duplicate job_runs rows.
--
-- Pre-B282 the SDK's BaseSyncScript._start_run() unconditionally inserted
-- a job_runs row at the start of main(), even when invoked under the
-- async worker which had already claimed a row for the same sync. Result:
-- every cron sync produced two rows that both progressed to terminal
-- status independently. The SDK-inserted twin is uniquely identified by
-- the absence of scheduler bookkeeping in `details`:
--
--   * source = 'cron' (manual / backfill / install set source explicitly)
--   * claimed_by IS NULL (worker-claimed rows always set claimed_by)
--   * details does NOT contain a 'scheduler_id' key — the scheduler
--     always writes {cron_source, scheduler_id, cron_expression,
--     scheduled_fire_at}. The SDK twin's details either stay as '{}' or
--     pick up only `_complete_run()`'s fields ({rows_failed: 0, ...}).
--     We use NOT (details ? 'scheduler_id') rather than details = '{}'
--     because the SDK's _complete_run() updates details on success.
--   * job_id LIKE 'sync:%' (hooks / alerts / health-monitor unaffected)
--   * status terminal — leave running rows alone so this migration cannot
--     race with an in-flight sync that's mid-_complete_run().
--
-- Verified against production 2026-05-05: predicate matches 469 twins
-- vs 444 scheduler-originals over the past 7 days (≈50% twin rate, as
-- expected from one-twin-per-cron-tick behaviour).
--
-- Idempotent: a second run finds no rows matching the predicate and
-- writes an audit log entry with deleted_count=0.

WITH deleted AS (
    DELETE FROM job_runs
    WHERE source = 'cron'
      AND claimed_by IS NULL
      AND NOT (details ? 'scheduler_id')
      AND job_id LIKE 'sync:%'
      AND status IN ('success', 'error', 'cancelled', 'timeout')
    RETURNING id
)
INSERT INTO app_logs (level, source, message, detail, created_at)
SELECT
    'info',
    'migration',
    'B282 backfill: removed ' || count(*) || ' orphan SDK-inserted job_runs rows',
    jsonb_build_object(
        'migration', '068_b282_dedup_orphan_sdk_run_rows',
        'deleted_count', count(*)
    ),
    now()
FROM deleted;
