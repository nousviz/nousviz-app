-- Plugin migration 003 down: B347 — drop the "Require timestamped
-- signature" flag. Inbound endpoints fall back to accepting V1-only.

ALTER TABLE webhook_endpoints
    DROP COLUMN IF EXISTS require_signature_v2;
