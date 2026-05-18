-- Migration 038: Connections health checks and credential rotation (P101)
-- Adds health tracking, description/tags, and credential rotation fields.
-- All columns are additive with defaults — safe for existing data.

-- ── Connections table extensions ─────────────────────────────────────

ALTER TABLE connections ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
ALTER TABLE connections ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE connections ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMPTZ;
ALTER TABLE connections ADD COLUMN IF NOT EXISTS health_status TEXT DEFAULT 'unknown';
ALTER TABLE connections ADD COLUMN IF NOT EXISTS health_history JSONB DEFAULT '[]';

-- ── Credentials table extensions ────────────────────────────────────

-- Only add if credentials table exists (created by migration 001)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'credentials') THEN
        ALTER TABLE credentials ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
        ALTER TABLE credentials ADD COLUMN IF NOT EXISTS rotation_status TEXT DEFAULT 'ok';
    END IF;
END $$;

-- ── Plugin settings connection reference ────────────────────────────

ALTER TABLE plugin_settings ADD COLUMN IF NOT EXISTS connection_id UUID;

-- Note: No FK constraint to connections(id) — plugin_settings uses a composite PK
-- (plugin_id, key) and connection_id is optional. The reference is validated at
-- application level, not database level, to avoid cascade complications.
