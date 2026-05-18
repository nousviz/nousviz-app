-- Migration 063: B264 (v0.9.11.6) — publishable fusions as reusable datasets.
--
-- Adds a dedicated `fusions` schema for published-fusion views, plus
-- publish-state columns on the fusions table. No fusions are auto-
-- published; existing rows default to published=false.

-- 1. Schema for published fusion views, owned by nousviz.
CREATE SCHEMA IF NOT EXISTS fusions AUTHORIZATION nousviz;

-- 2. Grant USAGE + default SELECT privs so views auto-inherit grants
--    when CREATE VIEW runs at publish time. The IF EXISTS guard handles
--    fresh dev installs that haven't created the role yet.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA fusions TO nousviz_plugin';
        EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE nousviz IN SCHEMA fusions
                 GRANT SELECT ON TABLES TO nousviz_plugin';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_query') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA fusions TO nousviz_query';
        EXECUTE 'ALTER DEFAULT PRIVILEGES FOR ROLE nousviz IN SCHEMA fusions
                 GRANT SELECT ON TABLES TO nousviz_query';
    END IF;
END $$;

-- 3. Extend the fusions table with publish state.
ALTER TABLE fusions
    ADD COLUMN IF NOT EXISTS published     BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS published_at  TIMESTAMPTZ NULL;
