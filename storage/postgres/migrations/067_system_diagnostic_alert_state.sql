-- Migration 067: B274 (v0.9.11.20) — diagnostic-alert dedup state +
-- subscription registry.
--
-- system_diagnostic_alert_state holds one row per (finding_id,
-- affected_key) currently active. The bridge in
-- apps/api/src/services/diagnostic_alerts.py uses it to dedup: a
-- finding present on consecutive snapshots fires once, not every
-- snapshot.
--
-- system_diagnostic_alert_subscriptions opts each webhook_slug in
-- (or out) of receiving diagnostic alerts. Default-empty so no
-- alerts fire on a fresh deploy until the operator subscribes at
-- least one webhook from /settings/maintenance.

CREATE TABLE IF NOT EXISTS system_diagnostic_alert_state (
    finding_id          TEXT NOT NULL,
    affected_key        TEXT NOT NULL,
    severity            TEXT NOT NULL,
    title               TEXT NOT NULL,
    first_detected_at   TIMESTAMPTZ NOT NULL,
    last_seen_at        TIMESTAMPTZ NOT NULL,
    last_alerted_at     TIMESTAMPTZ,
    alerts_fired        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (finding_id, affected_key)
);

CREATE INDEX IF NOT EXISTS idx_system_diagnostic_alert_state_last_seen
    ON system_diagnostic_alert_state (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS system_diagnostic_alert_subscriptions (
    webhook_slug TEXT PRIMARY KEY,
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_by   UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nousviz') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON system_diagnostic_alert_state TO nousviz';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON system_diagnostic_alert_subscriptions TO nousviz';
    END IF;
END $$;
