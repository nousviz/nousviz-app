-- B234 (v0.9.9.2) rollback. DESTRUCTIVE — operator audit history is
-- lost. Only safe to roll back during the v0.9.9.2 deployment window
-- before any RBAC mutations have occurred. After v0.9.9.3 ships,
-- the table contains compliance-relevant data that should not be lost.

DROP INDEX IF EXISTS rbac_config_audit_target_idx;
DROP INDEX IF EXISTS rbac_config_audit_actor_idx;
DROP INDEX IF EXISTS rbac_config_audit_occurred_at_idx;
DROP TABLE IF EXISTS rbac_config_audit;
