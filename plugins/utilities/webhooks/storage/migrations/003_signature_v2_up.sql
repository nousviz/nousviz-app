-- Plugin migration 003: B347 — inbound timestamped signatures (V2).
--
-- Adds a per-endpoint opt-in that makes an inbound endpoint reject any
-- request without valid X-Webhook-Timestamp + X-Webhook-Signature-V2
-- headers. Without it, an attacker could strip the V2 headers from a
-- captured delivery and replay it with the never-expiring V1 signature.
--
-- Defaults to false, so every existing endpoint keeps accepting V1-only
-- senders. No new table (duplicate detection reuses webhook_events and
-- its existing endpoint_id / received_at indexes).

ALTER TABLE webhook_endpoints
    ADD COLUMN IF NOT EXISTS require_signature_v2 BOOLEAN NOT NULL DEFAULT false;
