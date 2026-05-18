-- 027_delete_stale_fusions.sql
-- Remove deprecated seed fusions that reference deleted seed-plugin tables.
-- See ticket B146.

DELETE FROM fusions WHERE slug IN ('morning-command-center', 'seo-war-room');
