-- Manual rollback for migration 063 (B264). Drops the fusions schema
-- (cascades through any published views) and removes publish columns.
-- WARNING: published view content is lost; re-publishing recreates.
-- The fusions table itself (configs, widgets, layout) is untouched.

DROP SCHEMA IF EXISTS fusions CASCADE;
ALTER TABLE fusions DROP COLUMN IF EXISTS published;
ALTER TABLE fusions DROP COLUMN IF EXISTS published_at;
