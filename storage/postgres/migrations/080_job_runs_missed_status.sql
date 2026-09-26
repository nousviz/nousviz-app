-- 080_job_runs_missed_status.sql
--
-- Adds the `missed` status to job_runs.
--
-- A scheduled sync that never starts (worker down, run stuck in the
-- queue) never reaches the worker's _finalize_run, so it could never
-- raise a failure alert. The scheduler's watchdog
-- (apps/api/src/services/job_alerts.py:check_missed_runs) now records
-- such a fire as a `missed` row: visible in job history, the dedupe key
-- for its alert, and inert to the worker (which only claims `queued`).

ALTER TABLE job_runs DROP CONSTRAINT IF EXISTS job_runs_status_check;
ALTER TABLE job_runs ADD CONSTRAINT job_runs_status_check
    CHECK (status IN (
        'queued',
        'running',
        'success',
        'error',
        'timeout',
        'cancelling',
        'cancelled',
        'paused',
        'skipped',
        'missed'       -- 080: scheduled fire produced no run in time
    ));
