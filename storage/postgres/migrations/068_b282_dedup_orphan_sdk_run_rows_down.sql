-- Down-migration for 068: irreversible.
--
-- The deletion is data cleanup, not schema change. The deleted rows
-- carried no information not also present on their worker-claimed twin
-- (same job_id, overlapping time window, same final status). Restoring
-- them would just re-create the duplication this migration removes.
--
-- If a rollback is genuinely needed, restore from the pre-deploy
-- pg_dump captured per the B282 test plan §1.

SELECT 'B282 backfill is irreversible — restore from pg_dump if needed' AS note;
