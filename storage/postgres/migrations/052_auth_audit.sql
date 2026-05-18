-- B227 (v0.9.8.0): RBAC audit log. Every permission decision lands here —
-- shadow-mode in v0.9.8.0 (logs but doesn't enforce), enforced from v0.9.8.2 (B229).
--
-- mode: 'shadow' (the registry-based dependency runs but doesn't gate; inline
--                 _require_* still rules)
--     | 'enforced' (registry verdict is authoritative; v0.9.8.2+)
--
-- decision: 'allow'              — request was permitted
--         | 'deny'               — request was denied (shadow logs the would-be deny)
--         | 'shadow_mismatch'    — registry verdict != inline _require_* verdict;
--                                  flagged so we can fix the registry before B229's flip

CREATE TABLE IF NOT EXISTS auth_audit (
  id            BIGSERIAL PRIMARY KEY,
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id       TEXT NULL,                 -- null for unauthenticated requests
  user_role     TEXT NULL,
  permission    TEXT NOT NULL,
  route_method  TEXT NOT NULL,
  route_path    TEXT NOT NULL,
  decision      TEXT NOT NULL,
  mode          TEXT NOT NULL,
  reason        TEXT NULL,
  request_id    TEXT NULL,
  CHECK (decision IN ('allow', 'deny', 'shadow_mismatch')),
  CHECK (mode IN ('shadow', 'enforced'))
);

-- Time-ordered scan (matrix UI in B230 will query "recent decisions")
CREATE INDEX IF NOT EXISTS auth_audit_occurred_at_idx
  ON auth_audit (occurred_at DESC);

-- Per-user history (B230 audit log surface; v0.9.9 step-up auth + change history)
CREATE INDEX IF NOT EXISTS auth_audit_user_idx
  ON auth_audit (user_id, occurred_at DESC);

-- Partial index: shadow_mismatch is the rare, alarming case — the gate query
-- before B229 deploys is "any mismatches in the last 24h?" — must be fast.
CREATE INDEX IF NOT EXISTS auth_audit_mismatch_idx
  ON auth_audit (occurred_at DESC)
  WHERE decision = 'shadow_mismatch';
