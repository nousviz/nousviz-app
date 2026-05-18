-- B227 (v0.9.8.0) rollback. Drops the auth_audit table and indexes.
-- Note: the master plan recommends NOT actually rolling this back even on
-- full B227 revert — the table is tiny, has zero foreign-key dependencies,
-- and reapplying is annoying. Keep it. This down-migration exists for
-- completeness and disaster recovery only.

DROP INDEX IF EXISTS auth_audit_mismatch_idx;
DROP INDEX IF EXISTS auth_audit_user_idx;
DROP INDEX IF EXISTS auth_audit_occurred_at_idx;
DROP TABLE IF EXISTS auth_audit;
