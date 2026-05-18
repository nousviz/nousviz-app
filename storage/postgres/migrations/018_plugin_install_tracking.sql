-- Nousviz: Plugin install tracking (P22-G2b)
-- Adds installed_commit_sha to plugin_registry so the API can verify plugin
-- files have not been modified since install.

ALTER TABLE plugin_registry
    ADD COLUMN IF NOT EXISTS installed_commit_sha  TEXT,
    ADD COLUMN IF NOT EXISTS installed_at          TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS installed_from_url    TEXT;
