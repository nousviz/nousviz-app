-- Down for migration 075 (B305).
ALTER TABLE user_invites
    DROP COLUMN IF EXISTS plugin_access_pending;
