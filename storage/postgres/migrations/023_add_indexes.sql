-- 023_add_indexes.sql
-- Add missing indexes for frequently queried columns. See ticket B143.

-- shared_links: health.py queries WHERE revoked = false AND expires_at > now()
CREATE INDEX IF NOT EXISTS idx_shared_links_active
    ON shared_links (expires_at) WHERE revoked = false;

-- user_sessions: auth.py JOINs on user_id and looks up by token
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
    ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token
    ON user_sessions (token);

-- annotations: dashboard page queries WHERE pinned = true
CREATE INDEX IF NOT EXISTS idx_annotations_pinned
    ON annotations (pinned) WHERE pinned = true;
