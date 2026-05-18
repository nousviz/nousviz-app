ALTER TABLE connections DROP COLUMN IF EXISTS description;
ALTER TABLE connections DROP COLUMN IF EXISTS tags;
ALTER TABLE connections DROP COLUMN IF EXISTS last_health_check;
ALTER TABLE connections DROP COLUMN IF EXISTS health_status;
ALTER TABLE connections DROP COLUMN IF EXISTS health_history;

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'credentials') THEN
        ALTER TABLE credentials DROP COLUMN IF EXISTS expires_at;
        ALTER TABLE credentials DROP COLUMN IF EXISTS rotation_status;
    END IF;
END $$;

ALTER TABLE plugin_settings DROP COLUMN IF EXISTS connection_id;
