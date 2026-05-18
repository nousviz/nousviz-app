-- Newsletter subscribers
-- Core table, not plugin-specific. Any plugin or CMS site can collect subscribers.

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    name        TEXT,
    source      TEXT NOT NULL DEFAULT 'website',  -- website | footer | academy | blog | api
    status      TEXT NOT NULL DEFAULT 'active',    -- active | unsubscribed | bounced
    tags        TEXT[] NOT NULL DEFAULT '{}',
    ip_address  TEXT,
    subscribed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    unsubscribed_at TIMESTAMPTZ,
    UNIQUE(email)
);

CREATE INDEX IF NOT EXISTS idx_newsletter_status ON newsletter_subscribers(status);
CREATE INDEX IF NOT EXISTS idx_newsletter_source ON newsletter_subscribers(source);
