-- B236 (v0.9.10.0): step-up auth + impersonation session support.
--
-- step_up_until: when set and > now(), this session has recently
-- re-authenticated (POST /api/auth/step-up) and may perform sensitive
-- operations like RBAC writes and impersonation. NULL or past = normal.
-- 5-minute window (set by the endpoint, not a column default).
--
-- acting_as_user_id: when set, this session is impersonating the named user.
-- The session's user_id is the actor (real human responsible). Permission
-- resolution uses acting_as_user_id when set, falls back to user_id.

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'step_up_until'
  ) THEN
    ALTER TABLE user_sessions ADD COLUMN step_up_until TIMESTAMPTZ;
    COMMENT ON COLUMN user_sessions.step_up_until IS
      'When set and > now(), this session has recently re-authenticated and may '
      'perform sensitive operations (RBAC writes, impersonation). NULL or past = '
      'normal session. Set by POST /api/auth/step-up.';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'acting_as_user_id'
  ) THEN
    ALTER TABLE user_sessions ADD COLUMN acting_as_user_id UUID
      REFERENCES users(id) ON DELETE CASCADE;
    COMMENT ON COLUMN user_sessions.acting_as_user_id IS
      'When set, this session is impersonating the named user. The actual session '
      'user (user_id) is the actor; permission resolution uses acting_as_user_id.';
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_sessions_step_up
  ON user_sessions(step_up_until)
  WHERE step_up_until IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_sessions_acting_as
  ON user_sessions(acting_as_user_id)
  WHERE acting_as_user_id IS NOT NULL;
