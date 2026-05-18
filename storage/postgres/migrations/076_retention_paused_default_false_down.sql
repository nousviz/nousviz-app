-- Migration 076 down: revert retention default to TRUE.
--
-- Reverts the column default; does NOT touch existing rows. If you ran
-- the one-time UPDATE to unpause existing policies after this migration
-- was applied, you'll need a separate UPDATE to re-pause them — but the
-- audit's recommendation is to keep retention running.

ALTER TABLE system_retention_overrides
    ALTER COLUMN paused SET DEFAULT TRUE;

COMMENT ON COLUMN system_retention_overrides.paused IS NULL;
