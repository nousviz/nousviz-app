-- Migration 037: User dashboards table
-- User-created dashboard views composed from plugin datasets, fusions, custom components, and raw SQL.
-- Separate from plugin dashboards (YAML, read-only) and fusions (cross-plugin data composition).

CREATE TABLE IF NOT EXISTS user_dashboards (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL,
  slug        TEXT        UNIQUE NOT NULL,
  description TEXT,
  widgets     JSONB       NOT NULL DEFAULT '[]',
  layout      JSONB       NOT NULL DEFAULT '{}',
  sources     JSONB       NOT NULL DEFAULT '[]',
  created_by  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_dashboards_slug ON user_dashboards (slug);
CREATE INDEX IF NOT EXISTS idx_user_dashboards_created_by ON user_dashboards (created_by);
