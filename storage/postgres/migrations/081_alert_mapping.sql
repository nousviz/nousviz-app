-- Migration 081: P230 (v1.1.0) — alerts on any database, with column mapping.
--
-- Alert definitions stay in Postgres; these columns describe where the data
-- an alert reads lives (engine + connection) and how the user mapped its
-- columns. All additive with defaults, so pre-P230 alerts evaluate exactly
-- as before (db_engine 'postgres', date column 'date').
--
-- connection_id is validated by the application, not a foreign key, like
-- plugin_settings.connection_id (migration 038).

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS source_kind             TEXT             NOT NULL DEFAULT 'table',
    ADD COLUMN IF NOT EXISTS connection_id           UUID,
    ADD COLUMN IF NOT EXISTS date_column             TEXT             NOT NULL DEFAULT 'date',
    ADD COLUMN IF NOT EXISTS value_kind              TEXT             NOT NULL DEFAULT 'column',
    ADD COLUMN IF NOT EXISTS denominator             TEXT,
    ADD COLUMN IF NOT EXISTS denominator_aggregation TEXT             NOT NULL DEFAULT 'sum',
    ADD COLUMN IF NOT EXISTS group_by_columns        TEXT[]           NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS filters                 JSONB            NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS min_volume_column       TEXT,
    ADD COLUMN IF NOT EXISTS min_volume              DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS currency_column         TEXT,
    ADD COLUMN IF NOT EXISTS query_id                TEXT,
    ADD COLUMN IF NOT EXISTS query_params            JSONB            NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS last_run_at             TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_status             TEXT,
    ADD COLUMN IF NOT EXISTS last_error              TEXT,
    ADD COLUMN IF NOT EXISTS last_duration_ms        INTEGER,
    ADD COLUMN IF NOT EXISTS last_rows_checked       INTEGER;

-- The single group_by becomes the first of up to three group-by columns.
UPDATE alert_rules
   SET group_by_columns = ARRAY[group_by]
 WHERE group_by IS NOT NULL AND group_by <> '' AND group_by_columns = '{}';

-- source_kind values: table | plugin_dataset | connection_table | plugin_query
ALTER TABLE alert_rules DROP CONSTRAINT IF EXISTS alert_rules_source_kind_check;
ALTER TABLE alert_rules ADD CONSTRAINT alert_rules_source_kind_check
    CHECK (source_kind IN ('table', 'plugin_dataset', 'connection_table', 'plugin_query'));
