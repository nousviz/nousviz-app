-- B208 (v0.9.6.1): promote frequently-queried detail JSONB keys to indexed
-- columns. The shape of `detail` has stabilized over five minor releases —
-- plugin_id appears in nearly every plugin event, run_id in every sync/hook,
-- actor_user_id in admin actions. Time to treat them as first-class.
--
-- Migration is purely additive. Existing readers (the old API endpoint, any
-- external psql queries) are unaffected. Backfill is best-effort: rows whose
-- detail doesn't have the key end up with NULL columns; the API falls back
-- to detail->>'key' for legacy rows during the rollout window.

ALTER TABLE app_logs
    ADD COLUMN IF NOT EXISTS plugin_id      TEXT,
    ADD COLUMN IF NOT EXISTS actor_user_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS run_id         BIGINT;

-- Backfill from existing detail JSONB. Idempotent — re-runs are no-ops on
-- already-populated rows because of the WHERE col IS NULL gate.

UPDATE app_logs
SET plugin_id = detail->>'plugin_id'
WHERE plugin_id IS NULL
  AND detail ? 'plugin_id'
  AND detail->>'plugin_id' IS NOT NULL
  AND detail->>'plugin_id' <> '';

UPDATE app_logs
SET run_id = (detail->>'run_id')::bigint
WHERE run_id IS NULL
  AND detail ? 'run_id'
  AND detail->>'run_id' ~ '^[0-9]+$';

-- actor_user_id is the most recent addition (B206 v0.9.6.0). Most rows
-- won't have it. Validate UUID shape strictly to avoid backfill errors on
-- malformed values.
UPDATE app_logs
SET actor_user_id = (detail->>'actor_user_id')::uuid
WHERE actor_user_id IS NULL
  AND detail ? 'actor_user_id'
  AND detail->>'actor_user_id' ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';

-- Indexes — partial (WHERE col IS NOT NULL) to keep them small while a
-- large fraction of legacy rows still have NULL columns. After 30 days of
-- new writes, the partial indexes cover ~all rows.
CREATE INDEX IF NOT EXISTS idx_app_logs_plugin_id
    ON app_logs (plugin_id) WHERE plugin_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_app_logs_actor_user_id
    ON app_logs (actor_user_id) WHERE actor_user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_app_logs_run_id
    ON app_logs (run_id) WHERE run_id IS NOT NULL;

-- GIN on detail for residual JSONB queries (legacy fallback path in API).
-- Existing queries like `detail @> '{"key":"v"}'` benefit from this too.
CREATE INDEX IF NOT EXISTS idx_app_logs_detail_gin
    ON app_logs USING GIN (detail);

-- Refresh stats so the planner picks up the new columns + indexes.
ANALYZE app_logs;
