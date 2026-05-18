-- B234 (v0.9.9.2): RBAC config audit log — every mutation through the
-- /api/system/role-overrides and /api/system/custom-roles endpoints
-- inserts a row here. Distinct from auth_audit (which logs permission
-- DECISIONS at request time) — this is who-changed-what-when of the
-- RBAC POLICY itself.
--
-- Fail-closed: callers wrap audit insert + data write in one
-- transaction. If the audit insert fails the operation rolls back.
-- Compliance scenarios require non-optional audit trail.

CREATE TABLE IF NOT EXISTS rbac_config_audit (
  id                BIGSERIAL PRIMARY KEY,
  occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_user_id     TEXT,
  actor_role        TEXT,
  action            TEXT NOT NULL,
  target_role       TEXT NOT NULL,
  target_permission TEXT,
  before_state      JSONB,
  after_state       JSONB,
  note              TEXT,
  CHECK (action IN ('grant', 'revoke', 'clear', 'create_role', 'delete_role'))
);

CREATE INDEX IF NOT EXISTS rbac_config_audit_occurred_at_idx
  ON rbac_config_audit (occurred_at DESC);

CREATE INDEX IF NOT EXISTS rbac_config_audit_actor_idx
  ON rbac_config_audit (actor_user_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS rbac_config_audit_target_idx
  ON rbac_config_audit (target_role, occurred_at DESC);
