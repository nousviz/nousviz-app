-- Down for migration 081 (P230). Manual only. Pre-P230 code ignores these
-- columns, so dropping them is only needed to fully restore the schema.
ALTER TABLE alert_rules DROP CONSTRAINT IF EXISTS alert_rules_source_kind_check;
ALTER TABLE alert_rules
    DROP COLUMN IF EXISTS source_kind,
    DROP COLUMN IF EXISTS connection_id,
    DROP COLUMN IF EXISTS date_column,
    DROP COLUMN IF EXISTS value_kind,
    DROP COLUMN IF EXISTS denominator,
    DROP COLUMN IF EXISTS denominator_aggregation,
    DROP COLUMN IF EXISTS group_by_columns,
    DROP COLUMN IF EXISTS filters,
    DROP COLUMN IF EXISTS min_volume_column,
    DROP COLUMN IF EXISTS min_volume,
    DROP COLUMN IF EXISTS currency_column,
    DROP COLUMN IF EXISTS query_id,
    DROP COLUMN IF EXISTS query_params,
    DROP COLUMN IF EXISTS last_run_at,
    DROP COLUMN IF EXISTS last_status,
    DROP COLUMN IF EXISTS last_error,
    DROP COLUMN IF EXISTS last_duration_ms,
    DROP COLUMN IF EXISTS last_rows_checked;
