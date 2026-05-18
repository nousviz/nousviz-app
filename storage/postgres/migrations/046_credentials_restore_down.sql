-- 046_credentials_restore_down.sql — reverse of the restore
-- Drops credentials and credential_audit_log. Only used in dev rollback.

DROP TABLE IF EXISTS credential_audit_log;
DROP TABLE IF EXISTS credentials;
