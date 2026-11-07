-- Down for migration 080 (B342). Manual only.
-- `fetch` audit rows have no credential; remove them before restoring NOT NULL.
DROP INDEX IF EXISTS idx_credential_audit_log_action_created;
DELETE FROM credential_audit_log WHERE credential_id IS NULL;
ALTER TABLE credential_audit_log ALTER COLUMN credential_id SET NOT NULL;
DROP TABLE IF EXISTS credential_usage_daily;
