-- Named connections (P96, B102)
--
-- Migration 001 created `connections` with the old plugin-connections schema
-- (plugin_id, connection_type, status, health fields). This migration evolves
-- it to the named-connections schema. Handles three cases:
--   1. Fresh install: 001 already ran, table has old schema → ALTER
--   2. Existing install: 001 ran long ago, 034 never ran → ALTER
--   3. Edge case: table doesn't exist at all → CREATE with final schema

DO $$
BEGIN
    -- If the table doesn't exist at all, create it with the final schema
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'connections'
    ) THEN
        CREATE TABLE connections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('postgres', 'mysql', 'clickhouse')),
            config JSONB NOT NULL DEFAULT '{}',
            is_default BOOLEAN NOT NULL DEFAULT false,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    ELSE
        -- Table exists — evolve from 001 schema to 034 schema

        -- Add new columns (idempotent)
        IF NOT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'type'
        ) THEN
            ALTER TABLE connections ADD COLUMN type TEXT;
        END IF;

        IF NOT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'is_default'
        ) THEN
            ALTER TABLE connections ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT false;
        END IF;

        IF NOT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'is_active'
        ) THEN
            ALTER TABLE connections ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
        END IF;

        IF NOT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'created_by'
        ) THEN
            ALTER TABLE connections ADD COLUMN created_by UUID REFERENCES users(id);
        END IF;

        -- Migrate data: populate type from connection_type if it exists
        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'connection_type'
        ) THEN
            UPDATE connections SET type = connection_type WHERE type IS NULL;
        END IF;

        -- Set NOT NULL + CHECK on type (only if not already constrained)
        -- Default unmigrated rows to 'postgres' so NOT NULL doesn't fail
        UPDATE connections SET type = 'postgres' WHERE type IS NULL;

        -- Add NOT NULL if not already set
        ALTER TABLE connections ALTER COLUMN type SET NOT NULL;

        -- Add CHECK constraint if not already present
        IF NOT EXISTS (
            SELECT FROM pg_constraint
            WHERE conrelid = 'connections'::regclass
              AND conname = 'connections_type_check'
        ) THEN
            ALTER TABLE connections ADD CONSTRAINT connections_type_check
                CHECK (type IN ('postgres', 'mysql', 'clickhouse'));
        END IF;

        -- Drop old columns from 001 schema (idempotent)
        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'plugin_id'
        ) THEN
            ALTER TABLE connections DROP COLUMN plugin_id;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'connection_type'
        ) THEN
            ALTER TABLE connections DROP COLUMN connection_type;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'status'
        ) THEN
            ALTER TABLE connections DROP COLUMN status;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'last_health_check'
        ) THEN
            ALTER TABLE connections DROP COLUMN last_health_check;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'last_successful_sync'
        ) THEN
            ALTER TABLE connections DROP COLUMN last_successful_sync;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'last_error'
        ) THEN
            ALTER TABLE connections DROP COLUMN last_error;
        END IF;

        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'connections' AND column_name = 'consecutive_failures'
        ) THEN
            ALTER TABLE connections DROP COLUMN consecutive_failures;
        END IF;
    END IF;
END
$$;

-- Drop old indexes from 001 schema (idempotent)
DROP INDEX IF EXISTS idx_connections_plugin;
DROP INDEX IF EXISTS idx_connections_status;

-- Create new indexes
CREATE INDEX IF NOT EXISTS idx_connections_type ON connections (type);

-- Ensure only one default per type
CREATE UNIQUE INDEX IF NOT EXISTS idx_connections_default_per_type
    ON connections (type) WHERE is_default = true;