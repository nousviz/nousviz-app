-- B232 (v0.9.9.0): RBAC override table — operator-controlled deltas on
-- top of the static catalog in apps/api/src/rbac/permissions.py.
--
-- kind = 'grant'  → role gains this permission (added to default set)
-- kind = 'revoke' → role loses this permission (removed from default set)
--
-- A single (role, permission) pair has at most one override. The
-- application enforces "last write wins" by deleting any prior row
-- before inserting a new one (B233's write path will handle this).
--
-- v0.9.9.0 only reads from this table. v0.9.9.1 (B233) ships the
-- editable matrix UI that writes to it.

CREATE TABLE IF NOT EXISTS rbac_role_overrides (
  id          BIGSERIAL PRIMARY KEY,
  role        TEXT NOT NULL,
  permission  TEXT NOT NULL,
  kind        TEXT NOT NULL,
  created_by  TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  note        TEXT,
  CHECK (kind IN ('grant', 'revoke')),
  UNIQUE (role, permission)
);

CREATE INDEX IF NOT EXISTS rbac_role_overrides_role_idx
  ON rbac_role_overrides (role);
