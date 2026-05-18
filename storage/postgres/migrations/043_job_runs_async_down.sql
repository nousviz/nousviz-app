-- Revert migration 043 — async job queue schema extensions.
--
-- Drops the new indexes and columns and restores the pre-v0.8.2 status
-- CHECK constraint. Rows with the new statuses would violate the reverted
-- constraint — this down migration refuses to run if such rows exist
-- (operator must resolve them before rollback).

DO $$
DECLARE
    blocked_count INT;
BEGIN
    SELECT COUNT(*) INTO blocked_count
    FROM job_runs
    WHERE status IN ('queued', 'cancelling', 'cancelled', 'paused', 'skipped');
    IF blocked_count > 0 THEN
        RAISE EXCEPTION 'Cannot revert 043: % job_runs rows use new v0.8.2 statuses. '
                        'Update them to a v0.8.1-compatible status first '
                        '(or delete them) and re-run.', blocked_count;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_job_runs_queued;
DROP INDEX IF EXISTS idx_job_runs_running_heartbeat;

ALTER TABLE job_runs DROP CONSTRAINT IF EXISTS job_runs_status_check;
ALTER TABLE job_runs ADD CONSTRAINT job_runs_status_check
    CHECK (status IN ('running', 'success', 'error', 'timeout'));

ALTER TABLE job_runs
    DROP COLUMN IF EXISTS progress,
    DROP COLUMN IF EXISTS cancelled_at,
    DROP COLUMN IF EXISTS paused_at,
    DROP COLUMN IF EXISTS claimed_by,
    DROP COLUMN IF EXISTS claimed_at,
    DROP COLUMN IF EXISTS heartbeat_at;
