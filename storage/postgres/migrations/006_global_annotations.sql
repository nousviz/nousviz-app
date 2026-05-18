-- Nousviz: Global Annotations System
-- Centrally managed canonical annotations for external events
-- (Google updates, outages, industry events) that provide context across all users.

-- ── Core annotation table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS global_annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    annotation_id   TEXT UNIQUE NOT NULL,                    -- stable ID: ann_google_core_update_2024_03
    slug            TEXT UNIQUE NOT NULL,                    -- URL slug: google-core-update-march-2024
    title           TEXT NOT NULL,
    summary         TEXT,                                    -- short description for cards/tooltips
    description     TEXT,                                    -- full markdown content for canonical page

    -- Classification
    scope           TEXT NOT NULL DEFAULT 'global',          -- global | vendor | product | plugin
    vendor          TEXT,                                    -- google, cloudflare, ahrefs, voluum
    status          TEXT NOT NULL DEFAULT 'draft',           -- draft | published | archived
    visibility      TEXT NOT NULL DEFAULT 'public',          -- public | unlisted | private

    -- Time range
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,                             -- null = ongoing or point event

    -- Trust
    trust_level     TEXT NOT NULL DEFAULT 'official',        -- official | verified | community | system
    review_state    TEXT NOT NULL DEFAULT 'approved',        -- draft | pending | approved | rejected
    created_by      TEXT NOT NULL DEFAULT 'internal_editor',

    -- SEO (for website publishing)
    seo_title       TEXT,
    seo_description TEXT,

    -- Lifecycle
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ga_slug ON global_annotations(slug);
CREATE INDEX IF NOT EXISTS idx_ga_annotation_id ON global_annotations(annotation_id);
CREATE INDEX IF NOT EXISTS idx_ga_vendor ON global_annotations(vendor);
CREATE INDEX IF NOT EXISTS idx_ga_scope ON global_annotations(scope);
CREATE INDEX IF NOT EXISTS idx_ga_status ON global_annotations(status);
CREATE INDEX IF NOT EXISTS idx_ga_dates ON global_annotations(start_time, end_time);

-- ── Taxonomy junction tables ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ga_products (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    product_slug    TEXT NOT NULL,                           -- google-search-console, cloudflare-analytics
    UNIQUE (annotation_id, product_slug)
);

CREATE TABLE IF NOT EXISTS ga_categories (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    category_slug   TEXT NOT NULL,                           -- core-update, outage, delay, schema-change
    UNIQUE (annotation_id, category_slug)
);

CREATE TABLE IF NOT EXISTS ga_industries (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    industry_slug   TEXT NOT NULL,                           -- seo, affiliate-marketing, ecommerce
    UNIQUE (annotation_id, industry_slug)
);

CREATE TABLE IF NOT EXISTS ga_tags (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    tag_slug        TEXT NOT NULL,                           -- rankings, traffic, volatility
    UNIQUE (annotation_id, tag_slug)
);

CREATE TABLE IF NOT EXISTS ga_related_plugins (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    plugin_id       TEXT NOT NULL,                           -- google-search-console, cloudflare
    UNIQUE (annotation_id, plugin_id)
);

CREATE TABLE IF NOT EXISTS ga_related_datasets (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    dataset_name    TEXT NOT NULL,                           -- gsc_performance_raw, cf_http_5m
    UNIQUE (annotation_id, dataset_name)
);

CREATE TABLE IF NOT EXISTS ga_sources (
    id              BIGSERIAL PRIMARY KEY,
    annotation_id   TEXT NOT NULL REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    label           TEXT NOT NULL,                           -- "Google Blog Post", "Status Page"
    source_url      TEXT NOT NULL
);

-- ── Workspace preferences (enable/disable global annotations) ────────
CREATE TABLE IF NOT EXISTS ga_workspace_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Filter level (set one, others null)
    annotation_id   TEXT REFERENCES global_annotations(annotation_id) ON DELETE CASCADE,
    vendor_slug     TEXT,
    product_slug    TEXT,
    category_slug   TEXT,
    industry_slug   TEXT,
    -- Preference
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gawp_annotation ON ga_workspace_preferences(annotation_id);
CREATE INDEX IF NOT EXISTS idx_gawp_vendor ON ga_workspace_preferences(vendor_slug);

-- Auto-update
CREATE OR REPLACE TRIGGER ga_updated_at
    BEFORE UPDATE ON global_annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
