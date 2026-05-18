-- Nousviz: Add requires[] to fusions
-- Tracks which plugins a fusion depends on for dependency validation at render time.

ALTER TABLE fusions ADD COLUMN IF NOT EXISTS requires JSONB NOT NULL DEFAULT '[]';
