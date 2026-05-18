-- 022_drop_dead_tables_down.sql
-- Recreates the 25 dead tables dropped by 022_drop_dead_tables.sql.
-- Tables will be empty — no data recovery. Structure only.

-- This is a safety net for rollback. In practice these tables
-- should not be recreated — they had zero code references.

-- NOTE: This file intentionally left minimal. If a rollback is needed,
-- re-run the original migrations (001, 003, 004, 006, 007, 008, 011, 013)
-- against a fresh database. The tables dropped here were all IF NOT EXISTS
-- in their original migrations, so re-running is safe.

SELECT 'Rollback: re-run original migrations 001-013 to recreate dropped tables' AS notice;
