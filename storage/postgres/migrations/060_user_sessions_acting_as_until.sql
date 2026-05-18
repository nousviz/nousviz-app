-- B254 (v0.9.10.0.5): session-flag impersonation refactor.
--
-- B236 (v0.9.10.0) shipped impersonation as a token-swap model: clicking
-- "Impersonate Alice" issued a new short-lived session row and replaced
-- the actor's localStorage token. That model produced bad UX (operator
-- had to re-login on exit) and architectural awkwardness (two session
-- rows per human, discontinuous audit metadata, stale rows in
-- user_sessions until the cleanup cron swept them).
--
-- This migration replaces the model: impersonation is now a pair of
-- transient flags on the actor's existing session row.
--
--   acting_as_user_id  (added in 057, B236) — non-null = impersonating
--   acting_as_until    (added here, B254)   — auto-expiry of the flag
--
-- The session itself (and its token) is unchanged across the entire
-- impersonation lifecycle. Exit clears both flags. Auto-expiry fires
-- at acting_as_until <= now() via a lazy clear in _verify_session_token.

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions' AND column_name = 'acting_as_until'
  ) THEN
    ALTER TABLE user_sessions ADD COLUMN acting_as_until TIMESTAMPTZ;
    COMMENT ON COLUMN user_sessions.acting_as_until IS
      'B254 (v0.9.10.0.5): when set, the impersonation flag '
      '(acting_as_user_id) auto-expires at this timestamp. NULL when '
      'not impersonating. Replaces the v0.9.10.0 model where '
      'impersonation created a separate short-lived session row.';
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_sessions_acting_as_until
  ON user_sessions(acting_as_until)
  WHERE acting_as_until IS NOT NULL;
