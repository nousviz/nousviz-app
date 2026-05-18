-- Nousviz: Annotations Schema
-- Contextual notes attached to data — algorithm updates, outages, campaign changes, analyst notes.

-- Annotation scopes define what level the annotation targets
-- point: specific dataset + date + optional filters
-- range: dataset + date range
-- plugin: entire plugin/source for a time period
-- global: whole workspace/instance

CREATE TABLE IF NOT EXISTS annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What created it
    source          TEXT NOT NULL DEFAULT 'manual',          -- manual | plugin | alert | api
    plugin_id       TEXT,                                    -- which plugin (null = global)
    created_by      TEXT NOT NULL DEFAULT 'user',            -- user identifier or system

    -- Content
    title           TEXT NOT NULL,                           -- short label shown on charts
    description     TEXT,                                    -- longer explanation (markdown ok)
    category        TEXT NOT NULL DEFAULT 'note',            -- note | incident | deployment | update | campaign | terms_change
    severity        TEXT NOT NULL DEFAULT 'info',            -- info | warning | critical
    color           TEXT,                                    -- optional hex color override for chart markers

    -- Scope: when
    date_start      DATE NOT NULL,                           -- start date (or exact date for point annotations)
    date_end        DATE,                                    -- null = single point, set = date range

    -- Scope: what (optional targeting)
    dataset         TEXT,                                    -- specific dataset (e.g. 'reports_raw')
    scope_filters   JSONB NOT NULL DEFAULT '{}',             -- optional column filters e.g. {"program_name": "King Billy", "site": "domain.com"}

    -- Tags for grouping and filtering
    tags            TEXT[] NOT NULL DEFAULT '{}',             -- e.g. ['google-update', 'seo', 'algorithm']

    -- Lifecycle
    pinned          BOOLEAN NOT NULL DEFAULT false,          -- pinned annotations always show on dashboards
    archived        BOOLEAN NOT NULL DEFAULT false,          -- soft delete
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common access patterns
CREATE INDEX IF NOT EXISTS idx_annotations_dates ON annotations(date_start, date_end);
CREATE INDEX IF NOT EXISTS idx_annotations_plugin ON annotations(plugin_id);
CREATE INDEX IF NOT EXISTS idx_annotations_category ON annotations(category);
CREATE INDEX IF NOT EXISTS idx_annotations_source ON annotations(source);
CREATE INDEX IF NOT EXISTS idx_annotations_tags ON annotations USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_annotations_active ON annotations(archived, date_start DESC);

-- Auto-update updated_at
CREATE OR REPLACE TRIGGER annotations_updated_at
    BEFORE UPDATE ON annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
