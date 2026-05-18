-- 029_user_accounts.sql (P58 + P83-A)
--
-- Multi-user accounts: role taxonomy, password auth, invite flow, superadmin invariant.
-- Feature-gated by MULTI_USER_ACCOUNTS env var (default false until v0.3.1 ships).

-- ── 1. Role taxonomy ────────────────────────────────────────────────────

-- Rename editor → analyst
UPDATE users SET role = 'analyst' WHERE role = 'editor';

-- Add check constraint for the 5-value role set
-- (no existing constraint to drop — role column was unconstrained text)
ALTER TABLE users ADD CONSTRAINT users_role_check
  CHECK (role IN ('superadmin', 'admin', 'analyst', 'viewer', 'custom'));

-- Change default from 'viewer' (the old default) — new users via invite
-- get their role from the invite row, but the column default is still useful
-- as a safety net
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer';

-- auth_method default: password (was 'cloudflare' from the original schema)
ALTER TABLE users ALTER COLUMN auth_method SET DEFAULT 'password';

-- ── 2. custom_role_id FK (populated by v0.3.2) ─────────────────────────

ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_role_id UUID;
-- FK deferred until custom_roles table exists in v0.3.2

-- ── 3. user_invites table ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_invites (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'viewer')),
  token_hash   TEXT NOT NULL UNIQUE,
  invited_by   UUID NOT NULL REFERENCES users(id),
  expires_at   TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
  used_at      TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_invites_email_pending
  ON user_invites (email) WHERE used_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_user_invites_token_pending
  ON user_invites (token_hash) WHERE used_at IS NULL;

-- ── 4. Superadmin invariant trigger ─────────────────────────────────────
-- Prevents reducing the superadmin count to zero via UPDATE or DELETE.

CREATE OR REPLACE FUNCTION check_superadmin_invariant()
RETURNS TRIGGER AS $$
DECLARE
  remaining INT;
BEGIN
  -- After the operation, count remaining active superadmins
  SELECT count(*) INTO remaining
  FROM users
  WHERE role = 'superadmin' AND is_active = true;

  IF remaining = 0 THEN
    RAISE EXCEPTION 'At least one superadmin must exist. Cannot remove or demote the last superadmin.';
  END IF;

  RETURN NULL; -- AFTER trigger, return value ignored
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_superadmin_invariant ON users;
CREATE CONSTRAINT TRIGGER trg_superadmin_invariant
  AFTER UPDATE OR DELETE ON users
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  WHEN (OLD.role = 'superadmin')
  EXECUTE FUNCTION check_superadmin_invariant();

-- ── 5. activity_events.user_id column ───────────────────────────────────

ALTER TABLE activity_events ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
CREATE INDEX IF NOT EXISTS idx_activity_events_user_id ON activity_events (user_id) WHERE user_id IS NOT NULL;
