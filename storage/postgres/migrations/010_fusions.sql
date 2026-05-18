-- Migration 010: Fusions table
-- Cross-plugin command center dashboards with JSONB widget configs

CREATE TABLE IF NOT EXISTS fusions (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL,
  slug        TEXT        UNIQUE NOT NULL,
  description TEXT,
  widgets     JSONB       NOT NULL DEFAULT '[]',
  layout      JSONB       NOT NULL DEFAULT '{}',
  is_default  BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fusions_slug ON fusions (slug);
CREATE INDEX IF NOT EXISTS idx_fusions_is_default ON fusions (is_default);
