-- B293 (v0.10.0.2): backfill is_primary=true on the first widget of every
-- fusion that has >1 widget and no widget marked is_primary. Pre-B293
-- the publish endpoint silently fell back to widgets[0]; this migration
-- captures that behaviour explicitly so the post-B293 422 guard doesn't
-- regress existing fusions on first deploy.
--
-- Single-widget fusions are out of scope — _get_primary_widget auto-picks
-- the lone widget at runtime without raising.
--
-- Idempotent: re-running this is a no-op once every multi-widget fusion
-- has at least one is_primary flag set.

UPDATE fusions
SET widgets = jsonb_set(widgets, '{0,is_primary}', 'true'::jsonb, true)
WHERE jsonb_typeof(widgets) = 'array'
  AND jsonb_array_length(widgets) > 1
  AND NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(widgets) w
    WHERE (w->>'is_primary')::boolean IS TRUE
  );
