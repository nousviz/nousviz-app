-- 029_user_accounts_down.sql
-- Rollback: revert role taxonomy, drop invites, drop trigger, drop activity user_id.
-- WARNING: irreversible if real users with 'analyst' role or superadmin exist.

-- Drop the superadmin invariant trigger
DROP TRIGGER IF EXISTS trg_superadmin_invariant ON users;
DROP FUNCTION IF EXISTS check_superadmin_invariant();

-- Drop user_invites
DROP TABLE IF EXISTS user_invites;

-- Drop custom_role_id column
ALTER TABLE users DROP COLUMN IF EXISTS custom_role_id;

-- Drop activity_events.user_id
ALTER TABLE activity_events DROP COLUMN IF EXISTS user_id;

-- Revert role constraint
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;

-- Rename analyst back to editor
UPDATE users SET role = 'editor' WHERE role = 'analyst';

-- Restore old defaults
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer';
ALTER TABLE users ALTER COLUMN auth_method SET DEFAULT 'cloudflare';
