-- Alert events: records each time an alert is evaluated by the worker.
-- Used by the UI to show "Last run" timestamps and trigger history.
--
-- alert_id references the alert's UUID from the JSON alert store (storage/alerts.json).
-- No FK constraint — alerts are file-backed, not a DB table.

CREATE TABLE IF NOT EXISTS alert_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id     UUID NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status       TEXT NOT NULL DEFAULT 'evaluated',  -- evaluated | triggered | error
    result_count INTEGER,
    details      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_alert_id  ON alert_events(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_events_triggered ON alert_events(triggered_at DESC);
