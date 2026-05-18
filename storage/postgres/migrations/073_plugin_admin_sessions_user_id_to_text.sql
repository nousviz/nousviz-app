-- Migration 073: B304 hotfix (v0.10.0.5.3) — plugin_admin_sessions.user_id
-- changes from UUID to TEXT.
--
-- The original v0.10.0.5 design assumed `request.state.user_identity` was
-- a UUID — wrong. NousViz core's `_verify_session_token` returns the
-- user's EMAIL after the `session:` prefix (see
-- apps/api/src/middleware/auth.py:336-346, B236 / B254 — impersonation
-- requires resolving to the effective user's email, not their id).
--
-- The `user_id UUID REFERENCES users(id)` column type therefore rejected
-- every bridge call on prod with `psycopg2.errors.InvalidTextRepresentation:
-- invalid input syntax for type uuid: "admin@example.com"`.
--
-- Fix: drop the FK + change type to TEXT. Operators querying the table
-- now match on email. The "user_id" name is kept for stability (re-naming
-- would force every consumer to change); semantically it now holds a user
-- identifier — currently an email, would still work if core later switched
-- to UUID format for session identity.
--
-- The table is empty on production at deploy time (no bridge call has
-- ever succeeded), so ALTER TYPE is safe — no data conversion needed.
-- If a fresh install runs both 072 and 073 on the same boot, the column
-- never holds any UUID values; the type change is a no-op at row level.

ALTER TABLE plugin_admin_sessions
    DROP CONSTRAINT IF EXISTS plugin_admin_sessions_user_id_fkey;

ALTER TABLE plugin_admin_sessions
    ALTER COLUMN user_id TYPE TEXT;
