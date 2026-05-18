-- Nousviz: Plugin Registry & Publisher Directory

-- ── Publishers (companies behind plugins) ────────────────────────────
CREATE TABLE IF NOT EXISTS publishers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT UNIQUE NOT NULL,                    -- url-friendly: "plausible-analytics", "ahrefs"
    name            TEXT NOT NULL,                           -- "Plausible Inc.", "Ahrefs Pte. Ltd."
    description     TEXT,                                    -- company bio
    website         TEXT,                                    -- https://example.com
    logo_url        TEXT,                                    -- company logo
    contact_email   TEXT,
    github_org      TEXT,                                    -- github org name
    verified        BOOLEAN NOT NULL DEFAULT false,          -- manually verified by Nousviz team
    featured        BOOLEAN NOT NULL DEFAULT false,          -- show on homepage/featured section

    -- Stats (updated periodically)
    plugin_count    INT NOT NULL DEFAULT 0,
    total_installs  INT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_publishers_slug ON publishers(slug);

-- ── Plugin Registry ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plugin_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT UNIQUE NOT NULL,                    -- "plausible-analytics", "google-search-console"
    publisher_id    UUID REFERENCES publishers(id),

    -- Identity
    name            TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    description     TEXT,
    long_description TEXT,                                   -- markdown, for detail page
    version         TEXT NOT NULL DEFAULT '1.0.0',
    license         TEXT DEFAULT 'MIT',
    icon            TEXT,                                    -- icon name or URL
    category        TEXT NOT NULL DEFAULT 'analytics',       -- analytics | marketing | finance | monitoring | productivity

    -- Visibility
    visibility      TEXT NOT NULL DEFAULT 'public',          -- fully_private | private | public | public_premium
    listed          BOOLEAN NOT NULL DEFAULT true,           -- show in marketplace search
    featured        BOOLEAN NOT NULL DEFAULT false,

    -- Links
    homepage        TEXT,
    repository      TEXT,                                    -- null for private/fully_private
    documentation   TEXT,
    support_url     TEXT,
    changelog_url   TEXT,

    -- Pricing (for public_premium)
    pricing_model   TEXT,                                     -- free | one_time | subscription | usage
    price_amount    DECIMAL(10,2),
    price_currency  TEXT DEFAULT 'USD',
    price_period    TEXT,                                     -- monthly | yearly | null for one_time

    -- Stats
    install_count   INT NOT NULL DEFAULT 0,
    active_installs INT NOT NULL DEFAULT 0,
    avg_rating      DECIMAL(3,2) DEFAULT 0,
    rating_count    INT NOT NULL DEFAULT 0,

    -- Metadata
    min_engine_version TEXT,                                  -- minimum Nousviz version required
    tags            TEXT[] NOT NULL DEFAULT '{}',
    screenshots     TEXT[] NOT NULL DEFAULT '{}',             -- URLs

    -- Lifecycle
    published_at    TIMESTAMPTZ,
    deprecated      BOOLEAN NOT NULL DEFAULT false,
    deprecated_message TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plugins_publisher ON plugin_registry(publisher_id);
CREATE INDEX IF NOT EXISTS idx_plugins_visibility ON plugin_registry(visibility);
CREATE INDEX IF NOT EXISTS idx_plugins_category ON plugin_registry(category);
CREATE INDEX IF NOT EXISTS idx_plugins_listed ON plugin_registry(listed);
CREATE INDEX IF NOT EXISTS idx_plugins_tags ON plugin_registry USING GIN(tags);

-- Auto-update timestamps
CREATE OR REPLACE TRIGGER publishers_updated_at
    BEFORE UPDATE ON publishers
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();

CREATE OR REPLACE TRIGGER plugin_registry_updated_at
    BEFORE UPDATE ON plugin_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_connections_timestamp();
