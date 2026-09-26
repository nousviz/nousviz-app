-- 080_job_runs_missed_status_down.sql — manual rollback only.
--
-- Rows already recorded as `missed` must go first, or the restored
-- constraint cannot be added.

DELETE FROM job_runs WHERE status = 'missed';
ALTER TABLE job_runs DROP CONSTRAINT IF EXISTS job_runs_status_check;
ALTER TABLE job_runs ADD CONSTRAINT job_runs_status_check
    CHECK (status IN (
        'queued', 'running', 'success', 'error', 'timeout',
        'cancelling', 'cancelled', 'paused', 'skipped'
    ));
