-- Migration tracking: records which migrations have been applied.
-- setup.sh checks this table before running each file and skips already-applied ones.
-- This file is safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
