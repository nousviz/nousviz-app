-- B208 (v0.9.6.1) rollback. Drops the promoted columns and indexes.
-- Existing rows in app_logs are preserved — only the column data is lost
-- (still recoverable from detail JSONB).

DROP INDEX IF EXISTS idx_app_logs_plugin_id;
DROP INDEX IF EXISTS idx_app_logs_actor_user_id;
DROP INDEX IF EXISTS idx_app_logs_run_id;
DROP INDEX IF EXISTS idx_app_logs_detail_gin;

ALTER TABLE app_logs
    DROP COLUMN IF EXISTS run_id,
    DROP COLUMN IF EXISTS actor_user_id,
    DROP COLUMN IF EXISTS plugin_id;
