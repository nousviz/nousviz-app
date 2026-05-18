-- Migration 065: B273 (v0.9.11.19) — system-health history snapshots.
--
-- Daily compact snapshot of /api/system/resources + /api/system/diagnostics
-- so trends become visible (sparklines, finding timelines, capacity
-- planning). Worker: apps/worker/src/snapshot_resources.py runs at
-- 03:30 UTC via PM2 cron and prunes rows older than 90 days.
--
-- Each row stores top-20-per-section JSONB; row size < 50 KB on
-- production-shape data. 90 days × 1 row/day ≈ 5 MB total.

CREATE TABLE IF NOT EXISTS system_resources_history (
    snapshot_at  TIMESTAMPTZ PRIMARY KEY,
    server       JSONB NOT NULL,
    postgres     JSONB NOT NULL,
    plugins      JSONB NOT NULL,
    syncs        JSONB NOT NULL,
    findings     JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_resources_history_snapshot_at
    ON system_resources_history (snapshot_at DESC);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, DELETE ON system_resources_history TO nousviz';
    END IF;
END $$;
