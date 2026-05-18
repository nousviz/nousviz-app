-- 026_session_token_hashing.sql
-- Hash session tokens at rest. See ticket P3.
--
-- Adds token_hash column, drops plaintext token column.
-- All existing sessions are invalidated (users must re-login).

ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS token_hash TEXT;

-- Backfill existing tokens with their SHA-256 hash
UPDATE user_sessions SET token_hash = encode(sha256(token::bytea), 'hex') WHERE token IS NOT NULL AND token_hash IS NULL;

-- Create index on token_hash (used for lookups on every authenticated request)
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions (token_hash);

-- Drop the plaintext token column and its old index
DROP INDEX IF EXISTS idx_user_sessions_token;
ALTER TABLE user_sessions DROP COLUMN IF EXISTS token;
