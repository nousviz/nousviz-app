-- B248 (v0.9.10.7): per-resource ACLs.
--
-- New tables:
--   resource_acls          — per-(type, id) grants to roles or users
--   rbac_resource_defaults — per-type allow/deny default policy
--
-- Resolution order in apps/api/src/rbac/resource_acls.py:
--   1. Owner implicit grant (resource's created_by → read + write)
--   2. Explicit user grant (resource_acls row, principal_kind='user')
--   3. Explicit role grant (resource_acls row, principal_kind='role')
--   4. Role permission (the existing rbac_role_overrides + static catalog)
--   5. Default policy (rbac_resource_defaults; allow on every type at install)
--
-- Idempotent: every CREATE uses IF NOT EXISTS, every INSERT uses ON CONFLICT.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resource_principal_kind') THEN
        CREATE TYPE resource_principal_kind AS ENUM ('role', 'user');
    END IF;
END$$;


CREATE TABLE IF NOT EXISTS resource_acls (
    id            BIGSERIAL PRIMARY KEY,
    -- Resource the grant applies to. resource_id is text so it can carry
    -- both UUIDs (uses) and slugs (dashboards, fusions, plugins).
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    -- Whom the grant is for.
    principal_kind resource_principal_kind NOT NULL,
    principal_id   TEXT NOT NULL,
    -- The permission string being granted (e.g. dashboards.read).
    -- Same vocabulary as the role-permission catalog so the resolver can
    -- consult ACLs and role permissions interchangeably.
    permission     TEXT NOT NULL,
    granted_by     TEXT,  -- actor user_id (text-cast); null for system grants
    note           TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (resource_type, resource_id, principal_kind, principal_id, permission)
);

CREATE INDEX IF NOT EXISTS idx_resource_acls_lookup
    ON resource_acls (resource_type, resource_id, principal_kind, principal_id);

CREATE INDEX IF NOT EXISTS idx_resource_acls_principal
    ON resource_acls (principal_kind, principal_id);

COMMENT ON TABLE resource_acls IS
    'B248: per-resource ACL grants. One row per (resource, principal, permission).';


CREATE TABLE IF NOT EXISTS rbac_resource_defaults (
    resource_type TEXT PRIMARY KEY,
    -- 'allow' = role permission alone is sufficient; ACLs only add.
    -- 'deny'  = role permission alone is NOT sufficient; an ACL row is required.
    policy        TEXT NOT NULL CHECK (policy IN ('allow', 'deny')),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by    TEXT
);

COMMENT ON TABLE rbac_resource_defaults IS
    'B248: per-resource-type default access policy. One row per resource_type.';


-- Seed default-allow on every known resource type. This keeps current
-- behaviour identical until the operator deliberately switches a type
-- to default-deny via the UI in v0.9.10.7 main.
INSERT INTO rbac_resource_defaults (resource_type, policy) VALUES
    ('dashboard',  'allow'),
    ('fusion',     'allow'),
    ('connection', 'allow'),
    ('share',      'allow'),
    ('plugin',     'allow')
ON CONFLICT (resource_type) DO NOTHING;
