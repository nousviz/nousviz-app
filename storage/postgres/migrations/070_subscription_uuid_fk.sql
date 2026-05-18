-- Migration 070: B283 (v0.9.11.24) — consolidate subscription PK to
-- UUID FK on webhook_endpoints.id.
--
-- v0.9.11.22.9 papered over the slug→UUID gap with a COALESCE in the
-- subscription query (so slug-less outbound webhooks were reachable).
-- B283 closes the gap properly: the subscription table now keys on
-- webhook_endpoints.id directly, removing the COALESCE shim and giving
-- us a real referential link from subscription back to webhook.
--
-- Backfill maps every existing row's webhook_slug to the corresponding
-- webhook id via the same COALESCE shape .22.9 used. Subscriptions
-- whose webhook was deleted post-.22.9 (orphans) are deleted with a
-- NOTICE — they couldn't deliver anyway.
--
-- This migration is gated on `webhook_endpoints` existing because that
-- table is plugin-owned (the webhooks plugin can be uninstalled). On a
-- fresh install where the plugin isn't installed yet, the
-- system_diagnostic_alert_subscriptions table simply stays empty and
-- the migration is a no-op-with-rename.
--
-- job_alert_subscriptions (v0.9.11.23 / B284) already keys on
-- webhook_id UUID — no change needed there.

DO $$
DECLARE
    has_webhooks  BOOLEAN := to_regclass('public.webhook_endpoints') IS NOT NULL;
    has_old_pk    BOOLEAN := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_diagnostic_alert_subscriptions'
          AND column_name = 'webhook_slug'
    );
    has_new_col   BOOLEAN := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_diagnostic_alert_subscriptions'
          AND column_name = 'webhook_id'
    );
    orphans       INT := 0;
BEGIN
    -- Already migrated? Bail.
    IF has_new_col AND NOT has_old_pk THEN
        RAISE NOTICE 'B283: system_diagnostic_alert_subscriptions already on webhook_id — skipping';
        RETURN;
    END IF;

    -- Add the new column if it's missing.
    IF NOT has_new_col THEN
        ALTER TABLE system_diagnostic_alert_subscriptions
            ADD COLUMN webhook_id UUID;
    END IF;

    -- Backfill webhook_id from the slug join (only if webhook_endpoints exists).
    IF has_webhooks AND has_old_pk THEN
        UPDATE system_diagnostic_alert_subscriptions s
        SET webhook_id = we.id
        FROM webhook_endpoints we
        WHERE s.webhook_id IS NULL
          AND s.webhook_slug = COALESCE(we.slug, we.id::text);
    END IF;

    -- Orphan check: any rows that didn't backfill = subscription whose
    -- webhook was deleted between .22.9 and .24. Drop them with a notice.
    IF has_old_pk THEN
        SELECT count(*) INTO orphans
        FROM system_diagnostic_alert_subscriptions
        WHERE webhook_id IS NULL;
        IF orphans > 0 THEN
            RAISE NOTICE 'B283: deleting % orphan diagnostic-alert subscription(s) (webhook deleted post-.22.9)', orphans;
            DELETE FROM system_diagnostic_alert_subscriptions WHERE webhook_id IS NULL;
        END IF;
    END IF;

    -- Promote webhook_id to the PK; drop the slug column.
    IF has_old_pk THEN
        ALTER TABLE system_diagnostic_alert_subscriptions
            ALTER COLUMN webhook_id SET NOT NULL;
        ALTER TABLE system_diagnostic_alert_subscriptions
            DROP CONSTRAINT IF EXISTS system_diagnostic_alert_subscriptions_pkey;
        ALTER TABLE system_diagnostic_alert_subscriptions
            ADD CONSTRAINT system_diagnostic_alert_subscriptions_pkey
                PRIMARY KEY (webhook_id);
        ALTER TABLE system_diagnostic_alert_subscriptions
            DROP COLUMN webhook_slug;
    END IF;
END $$;
