-- Datasets — uploaded CSV files stored as JSONB for query and CMS embedding.
-- Each dataset has its own column structure; no shared schema required.

CREATE TABLE IF NOT EXISTS datasets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    slug         TEXT NOT NULL UNIQUE,
    description  TEXT,
    columns      JSONB NOT NULL DEFAULT '[]',
    column_types JSONB NOT NULL DEFAULT '{}',
    data         JSONB NOT NULL DEFAULT '[]',
    row_count    INTEGER NOT NULL DEFAULT 0,
    file_size    INTEGER NOT NULL DEFAULT 0,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_datasets_slug    ON datasets(slug);
CREATE INDEX IF NOT EXISTS idx_datasets_updated ON datasets(updated_at DESC);
