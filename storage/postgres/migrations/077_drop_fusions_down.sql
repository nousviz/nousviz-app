-- Migration 077 down: Recreate fusion-schema scaffolding.
--
-- IMPORTANT: this DOWN restores STRUCTURE only. Data destroyed by the
-- up migration cannot be brought back from this file — restore from
-- a database backup taken before applying 077_drop_fusions.sql.
--
-- The structure mirrors migrations 010, 012, and 063 combined (the
-- net of all fusion-related migrations the up migration tore down).

-- 1. Recreate the fusions table (matches 010 + 012 + 063 cumulatively).
CREATE TABLE IF NOT EXISTS fusions (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT        NOT NULL,
  slug          TEXT        UNIQUE NOT NULL,
  description   TEXT,
  widgets       JSONB       NOT NULL DEFAULT '[]',
  layout        JSONB       NOT NULL DEFAULT '{}',
  is_default    BOOLEAN     NOT NULL DEFAULT FALSE,
  requires      JSONB       NOT NULL DEFAULT '[]',
  published     BOOLEAN     NOT NULL DEFAULT FALSE,
  published_at  TIMESTAMPTZ NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fusions_slug ON fusions (slug);
CREATE INDEX IF NOT EXISTS idx_fusions_is_default ON fusions (is_default);

-- 2. Recreate the fusions schema for published views (matches 063).
CREATE SCHEMA IF NOT EXISTS fusions AUTHORIZATION nousviz;
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

-- 3. Restore the resource-defaults entry for fusion (matches 061).
INSERT INTO rbac_resource_defaults (resource_type, policy)
    VALUES ('fusion', 'allow')
    ON CONFLICT (resource_type) DO NOTHING;
