-- B251 (v0.9.10.0.3): password reset tokens.
--
-- Stores one row per "Forgot password?" request. The raw token is sent
-- to the user via email; only its SHA-256 hash is stored here (matches
-- the user_sessions / user_invites pattern). Token is marked used
-- (used_at) when consumed by POST /api/auth/reset-password; expired
-- (expires_at past) tokens are unusable.
--
-- Tokens are not deleted on consumption — kept for audit. The retention
-- job (B249, v0.9.10.8) will eventually clean rows past
-- created_at + RETENTION_DAYS.
--
-- Table is owned by nousviz (created via this migration running as the
-- nousviz role); falls in pass 2 of the deploy.

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash    TEXT NOT NULL UNIQUE,
  expires_at    TIMESTAMPTZ NOT NULL,
  used_at       TIMESTAMPTZ,
  requested_ip  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE password_reset_tokens IS
  'B251 (v0.9.10.0.3): forgot-password reset tokens. SHA-256 hashed; '
  'raw token only ever lives in the email body sent to the user.';

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
  ON password_reset_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_active
  ON password_reset_tokens(expires_at)
  WHERE used_at IS NULL;

-- Extend rbac_config_audit.action to allow the four new password events.
-- Operators reading rbac_config_audit see who reset whose password when,
-- via what mechanism (CLI vs email vs self-change).
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.check_constraints
    WHERE constraint_name = 'rbac_config_audit_action_check'
  ) THEN
    ALTER TABLE rbac_config_audit DROP CONSTRAINT rbac_config_audit_action_check;
  END IF;
END $$;

ALTER TABLE rbac_config_audit
  ADD CONSTRAINT rbac_config_audit_action_check
  CHECK (action IN (
    'grant', 'revoke', 'clear', 'create_role', 'delete_role',
    'impersonate_start', 'impersonate_end',
    'password_reset_cli',          -- B251: scripts/reset-password.sh
    'password_reset_request',      -- B251: POST /api/auth/forgot-password
    'password_reset_completed',    -- B251: POST /api/auth/reset-password
    'password_change_self'         -- B251: PATCH /api/auth/me with password
  ));
