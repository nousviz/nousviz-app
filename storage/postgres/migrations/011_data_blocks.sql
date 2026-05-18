-- Nousviz: Data Blocks
-- Saved queries with visualization config, embeddable in CMS pages.

CREATE TABLE IF NOT EXISTS data_blocks (
    id          SERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    source_type TEXT NOT NULL DEFAULT 'sql',   -- sql | postgres_sql | widget_api
    source_config JSONB NOT NULL DEFAULT '{}',  -- {sql: "..."} or {endpoint: "/api/..."}
    viz_type    TEXT NOT NULL DEFAULT 'table',  -- table | kpi | bar | metric | number
    viz_config  JSONB NOT NULL DEFAULT '{}',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    is_public   BOOLEAN NOT NULL DEFAULT TRUE,
    cache_ttl   INTEGER NOT NULL DEFAULT 3600,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_blocks_slug ON data_blocks (slug);
CREATE INDEX IF NOT EXISTS idx_data_blocks_is_public ON data_blocks (is_public);
