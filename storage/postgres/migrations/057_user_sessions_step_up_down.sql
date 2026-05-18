-- Down-migration for 057_user_sessions_step_up.sql

DROP INDEX IF EXISTS idx_user_sessions_acting_as;
DROP INDEX IF EXISTS idx_user_sessions_step_up;

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'acting_as_user_id'
  ) THEN
    ALTER TABLE user_sessions DROP COLUMN acting_as_user_id;
  END IF;
END $$;

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'step_up_until'
  ) THEN
    ALTER TABLE user_sessions DROP COLUMN step_up_until;
  END IF;
END $$;
