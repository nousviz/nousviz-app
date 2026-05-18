-- 022_drop_dead_tables.sql
-- Drop 25 tables + 1 view that have zero code references.
-- These were created by early migrations for features never implemented
-- or replaced by JSON file storage. See ticket B142.

-- Domain: Credentials (001 partial — connections table is LIVE, keep it)
DROP TABLE IF EXISTS credential_audit_log CASCADE;
DROP TABLE IF EXISTS credentials CASCADE;

-- Domain: Notes (003 — DB table unused, notes.py uses JSON file)
DROP TABLE IF EXISTS notes CASCADE;

-- Domain: Activity/Telemetry (004 — all dead, activity.py uses JSON file)
DROP TABLE IF EXISTS activity_log CASCADE;
DROP TABLE IF EXISTS plugin_telemetry_settings CASCADE;
DROP TABLE IF EXISTS plugin_telemetry CASCADE;
DROP TABLE IF EXISTS data_overrides CASCADE;

-- Domain: Global Annotations (006 — entire feature never implemented)
DROP TABLE IF EXISTS ga_workspace_preferences CASCADE;
DROP TABLE IF EXISTS ga_sources CASCADE;
DROP TABLE IF EXISTS ga_related_datasets CASCADE;
DROP TABLE IF EXISTS ga_related_plugins CASCADE;
DROP TABLE IF EXISTS ga_tags CASCADE;
DROP TABLE IF EXISTS ga_industries CASCADE;
DROP TABLE IF EXISTS ga_categories CASCADE;
DROP TABLE IF EXISTS ga_products CASCADE;
DROP TABLE IF EXISTS global_annotations CASCADE;

-- Domain: Community/Semantic (007 partial — annotation_history is LIVE, keep it)
DROP VIEW IF EXISTS community_annotation_scores CASCADE;
DROP TABLE IF EXISTS community_annotation_votes CASCADE;
DROP TABLE IF EXISTS community_annotations CASCADE;
DROP TABLE IF EXISTS alert_semantic CASCADE;

-- Domain: Backups (008 — entire feature never implemented)
DROP TABLE IF EXISTS backup_table_snapshots CASCADE;
DROP TABLE IF EXISTS backup_history CASCADE;
DROP TABLE IF EXISTS backup_schedules CASCADE;
DROP TABLE IF EXISTS backup_destinations CASCADE;

-- Domain: CMS (011 — data_blocks never used)
DROP TABLE IF EXISTS data_blocks CASCADE;

-- Domain: Newsletter (013 — never used)
DROP TABLE IF EXISTS newsletter_subscribers CASCADE;
