-- Down-migration for 060_user_sessions_acting_as_until.sql

DROP INDEX IF EXISTS idx_user_sessions_acting_as_until;

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'acting_as_until'
  ) THEN
    ALTER TABLE user_sessions DROP COLUMN acting_as_until;
  END IF;
END $$;
