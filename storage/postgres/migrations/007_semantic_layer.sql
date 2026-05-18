-- Nousviz: Semantic Layer
-- Adds meaning, scoring, undo history, alert context, and community annotations.

-- ── Semantic fields on annotations ───────────────────────────────────────
-- Existing annotations table gets semantic enrichment columns.

ALTER TABLE annotations
    ADD COLUMN IF NOT EXISTS semantic_meaning   TEXT,           -- what does this annotation mean?
    ADD COLUMN IF NOT EXISTS impact_scope       TEXT[],         -- which metrics are affected
    ADD COLUMN IF NOT EXISTS semantic_score     TEXT,           -- useful | neutral | useless
    ADD COLUMN IF NOT EXISTS semantic_note      TEXT;           -- why did you score it this way?

-- ── Semantic score on alert triggers ─────────────────────────────────────
-- Extends existing feedback vocabulary with explicit semantic scoring.

ALTER TABLE alert_triggers
    ADD COLUMN IF NOT EXISTS semantic_score     TEXT,           -- useful | neutral | useless
    ADD COLUMN IF NOT EXISTS semantic_note      TEXT;           -- why (e.g. "fired during planned maintenance")

-- ── Annotation history (undo support) ────────────────────────────────────
-- Every create/update/delete writes a snapshot. Undo = restore from here.

CREATE TABLE IF NOT EXISTS annotation_history (
    id              SERIAL PRIMARY KEY,
    annotation_id   UUID NOT NULL,
    action          TEXT NOT NULL,                              -- created | updated | deleted | restored
    snapshot        JSONB NOT NULL,                             -- full row snapshot before the change
    changed_by      TEXT NOT NULL DEFAULT 'user',
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ann_history_annotation ON annotation_history(annotation_id, changed_at DESC);

-- ── Alert semantic context ────────────────────────────────────────────────
-- Per-alert meaning, causes, and recommended actions.
-- Separate table so it can be updated independently of the alert definition.

CREATE TABLE IF NOT EXISTS alert_semantic (
    alert_id            TEXT PRIMARY KEY,                       -- matches alert UUID (alerts still in JSON)
    plugin_id           TEXT,
    meaning             TEXT,                                   -- what does this alert indicate?
    likely_causes       JSONB NOT NULL DEFAULT '[]',            -- array of strings
    recommended_actions JSONB NOT NULL DEFAULT '[]',            -- array of strings
    normal_range_note   TEXT,                                   -- e.g. "seasonal dip Q1 is expected"
    related_metrics     TEXT[] NOT NULL DEFAULT '{}',
    aggregate_score     TEXT,                                   -- computed from trigger feedback: useful|neutral|useless
    last_computed_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Community annotations ────────────────────────────────────────────────
-- User-submitted annotations scoped to a plugin + metric + date range.
-- Surfaced only when score exceeds threshold.

CREATE TABLE IF NOT EXISTS community_annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plugin_id       TEXT NOT NULL,
    dataset         TEXT,
    metric          TEXT,                                       -- specific metric name if applicable
    title           TEXT NOT NULL,
    body            TEXT,
    date_start      DATE,
    date_end        DATE,
    submitted_by    TEXT NOT NULL DEFAULT 'anonymous',
    is_approved     BOOLEAN NOT NULL DEFAULT false,             -- moderation gate
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_community_ann_plugin  ON community_annotations(plugin_id);
CREATE INDEX IF NOT EXISTS idx_community_ann_dates   ON community_annotations(date_start, date_end);
CREATE INDEX IF NOT EXISTS idx_community_ann_approved ON community_annotations(is_approved);

-- ── Community annotation votes ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS community_annotation_votes (
    annotation_id   UUID NOT NULL REFERENCES community_annotations(id) ON DELETE CASCADE,
    voter_id        TEXT NOT NULL,                              -- user identifier or session
    score           TEXT NOT NULL,                             -- useful | neutral | useless
    voted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (annotation_id, voter_id)
);

CREATE INDEX IF NOT EXISTS idx_comm_votes_annotation ON community_annotation_votes(annotation_id);

-- Computed score view — useful for surfacing threshold filtering
CREATE OR REPLACE VIEW community_annotation_scores AS
SELECT
    a.id,
    a.plugin_id,
    a.dataset,
    a.metric,
    a.title,
    a.body,
    a.date_start,
    a.date_end,
    a.submitted_by,
    a.is_approved,
    COUNT(v.voter_id)                                                           AS vote_count,
    COUNT(v.voter_id) FILTER (WHERE v.score = 'useful')                         AS useful_votes,
    COUNT(v.voter_id) FILTER (WHERE v.score = 'neutral')                        AS neutral_votes,
    COUNT(v.voter_id) FILTER (WHERE v.score = 'useless')                        AS useless_votes,
    ROUND(
        COUNT(v.voter_id) FILTER (WHERE v.score = 'useful')::numeric /
        NULLIF(COUNT(v.voter_id), 0) * 100, 1
    )                                                                            AS useful_pct
FROM community_annotations a
LEFT JOIN community_annotation_votes v ON v.annotation_id = a.id
GROUP BY a.id;
