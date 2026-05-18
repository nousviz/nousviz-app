-- Down for migration 073 (B304 hotfix).
--
-- Best-effort revert. Only safe if every existing row's user_id is a
-- valid UUID literal — which won't be true after v0.10.0.5.3 ships
-- (rows will hold emails). Operator should TRUNCATE plugin_admin_sessions
-- first if rolling back; cookies get invalidated either way during the
-- downgrade.

ALTER TABLE plugin_admin_sessions
    ALTER COLUMN user_id TYPE UUID USING user_id::uuid;

ALTER TABLE plugin_admin_sessions
    ADD CONSTRAINT plugin_admin_sessions_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
