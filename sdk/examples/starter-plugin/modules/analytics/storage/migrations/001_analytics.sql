-- Module: analytics — 001_analytics
-- Optional aggregation table for pre-computed analytics.
-- Module migrations run when the module is first enabled.

CREATE TABLE IF NOT EXISTS starter_analytics (
    day         DATE PRIMARY KEY,
    items_total INT NOT NULL DEFAULT 0,
    items_new   INT NOT NULL DEFAULT 0,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
