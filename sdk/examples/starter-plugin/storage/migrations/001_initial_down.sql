-- starter-plugin: 001_initial_down
-- Reverses 001_initial.sql exactly.
-- Run automatically when the operator uninstalls this plugin with "Remove data" selected.
--
-- Rules:
--   - Use DROP TABLE IF EXISTS (idempotent)
--   - Drop in reverse order of creation (dependents first)
--   - Drop any functions and triggers created in the up migration

DROP TRIGGER  IF EXISTS starter_items_updated_at ON starter_items;
DROP FUNCTION IF EXISTS update_starter_items_updated_at();

DROP INDEX IF EXISTS starter_events_created_idx;
DROP INDEX IF EXISTS starter_events_type_idx;
DROP TABLE IF EXISTS starter_events;

DROP INDEX IF EXISTS starter_items_created_at_idx;
DROP INDEX IF EXISTS starter_items_status_idx;
DROP TABLE IF EXISTS starter_items;
