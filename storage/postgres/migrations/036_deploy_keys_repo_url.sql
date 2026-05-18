ALTER TABLE deploy_keys ADD COLUMN IF NOT EXISTS repo_url TEXT;
CREATE INDEX IF NOT EXISTS idx_deploy_keys_repo ON deploy_keys (repo_url);
