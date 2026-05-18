-- 008: Backup system — destinations, jobs, history, table tracking
-- Core feature: every Nousviz instance gets backup management

-- ── Backup destinations ─────────────────────────────────────────────────
-- Where backups get sent (local disk, S3, DO Spaces, etc.)
CREATE TABLE IF NOT EXISTS backup_destinations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,          -- local | s3 | do_spaces | gcs | azure_blob
    config          JSONB NOT NULL DEFAULT '{}',  -- {path, bucket, region, endpoint, access_key (encrypted), ...}
    is_default      BOOLEAN DEFAULT false,
    is_enabled      BOOLEAN DEFAULT true,
    last_tested_at  TIMESTAMPTZ,
    last_test_ok    BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed a default local destination
INSERT INTO backup_destinations (name, type, config, is_default)
VALUES ('Local disk', 'local', '{"path": "/opt/nousviz/backups"}', true)
ON CONFLICT DO NOTHING;

-- ── Backup schedules ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backup_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    scope           TEXT NOT NULL DEFAULT 'full',  -- full | incremental | plugin:<slug> | table:<name>
    cron_expr       TEXT NOT NULL DEFAULT '0 3 * * *',  -- default: 3am daily
    destination_id  UUID REFERENCES backup_destinations(id) ON DELETE SET NULL,
    retention_days  INTEGER NOT NULL DEFAULT 7,
    is_enabled      BOOLEAN DEFAULT true,
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Backup history ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backup_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id     UUID REFERENCES backup_schedules(id) ON DELETE SET NULL,
    destination_id  UUID REFERENCES backup_destinations(id) ON DELETE SET NULL,
    scope           TEXT NOT NULL,                  -- what was backed up
    type            TEXT NOT NULL DEFAULT 'full',   -- full | incremental | snapshot
    status          TEXT NOT NULL DEFAULT 'running', -- running | complete | failed
    file_path       TEXT,                           -- where the backup file lives
    file_size_bytes BIGINT,
    tables_included TEXT[],                         -- which tables were dumped
    tables_changed  TEXT[],                         -- which tables had changes (incremental)
    rows_backed_up  BIGINT,
    duration_ms     INTEGER,
    error           TEXT,
    metadata        JSONB DEFAULT '{}',             -- {pg_version, ch_version, triggered_by, ...}
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_backup_history_status ON backup_history(status);
CREATE INDEX IF NOT EXISTS idx_backup_history_started ON backup_history(started_at DESC);

-- ── Table change tracking ───────────────────────────────────────────────
-- Tracks row counts + estimated size per table to detect what changed
-- This is how we avoid full dumps when 99% of data hasn't changed
CREATE TABLE IF NOT EXISTS backup_table_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    table_name      TEXT NOT NULL,
    database_type   TEXT NOT NULL DEFAULT 'postgres',  -- postgres | clickhouse
    row_count       BIGINT,
    size_bytes      BIGINT,
    checksum        TEXT,                              -- hash of table structure
    snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_backup_snapshots_table ON backup_table_snapshots(table_name, snapshot_at DESC);
