-- Migration 070 down: B283 (v0.9.11.24) — restore webhook_slug PK on
-- system_diagnostic_alert_subscriptions.
--
-- Idempotent: if the table is already on the slug PK (forward migration
-- never ran or was already rolled back), it's a no-op.

DO $$
DECLARE
    has_webhooks  BOOLEAN := to_regclass('public.webhook_endpoints') IS NOT NULL;
    has_new_col   BOOLEAN := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_diagnostic_alert_subscriptions'
          AND column_name = 'webhook_id'
    );
    has_old_col   BOOLEAN := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_diagnostic_alert_subscriptions'
          AND column_name = 'webhook_slug'
    );
BEGIN
    IF NOT has_new_col THEN
        RAISE NOTICE 'B283 down: webhook_id column missing — already rolled back';
        RETURN;
    END IF;

    IF NOT has_old_col THEN
        ALTER TABLE system_diagnostic_alert_subscriptions
            ADD COLUMN webhook_slug TEXT;
    END IF;

    IF has_webhooks THEN
        UPDATE system_diagnostic_alert_subscriptions s
        SET webhook_slug = COALESCE(we.slug, we.id::text)
        FROM webhook_endpoints we
        WHERE s.webhook_id = we.id
          AND s.webhook_slug IS NULL;
    END IF;

    -- Drop any orphans created during reverse migration (no matching webhook).
    DELETE FROM system_diagnostic_alert_subscriptions WHERE webhook_slug IS NULL;

    ALTER TABLE system_diagnostic_alert_subscriptions
        ALTER COLUMN webhook_slug SET NOT NULL;
    ALTER TABLE system_diagnostic_alert_subscriptions
        DROP CONSTRAINT IF EXISTS system_diagnostic_alert_subscriptions_pkey;
    ALTER TABLE system_diagnostic_alert_subscriptions
        ADD CONSTRAINT system_diagnostic_alert_subscriptions_pkey
            PRIMARY KEY (webhook_slug);
    ALTER TABLE system_diagnostic_alert_subscriptions
        DROP COLUMN webhook_id;
END $$;
