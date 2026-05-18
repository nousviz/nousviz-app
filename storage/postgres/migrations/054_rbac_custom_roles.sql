-- B233 (v0.9.9.1): rbac_custom_roles — operator-defined roles that
-- exist alongside the four built-in roles (viewer, analyst, admin,
-- superadmin). Custom roles use the same rbac_role_overrides table
-- for their permission deltas.
--
-- Slug rules: lowercase, starts with letter, alphanumerics + - and _,
-- 2-32 chars. Must not collide with built-in roles (enforced in API).
--
-- based_on is informational — it records which built-in role was the
-- starting template when the custom role was created. The actual
-- permission set lives in rbac_role_overrides as 'grant' deltas
-- relative to the empty set (custom roles have no static-catalog
-- default).

CREATE TABLE IF NOT EXISTS rbac_custom_roles (
  role         TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  description  TEXT,
  based_on     TEXT,
  created_by   TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (role ~ '^[a-z][a-z0-9_-]*$' AND length(role) BETWEEN 2 AND 32)
);
