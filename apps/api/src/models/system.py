"""B215 (v0.9.10.2): typed responses for /api/system/* RBAC routes.

The full RBAC matrix is deeply nested with role_data, route metadata,
and audit summaries — most inner blocks are typed as dict[str, Any]
because their shape varies by role kind (built-in vs custom) and by
override state. The envelope and per-row shapes for the audit log are
modeled tightly.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionsMatrixResponse(BaseModel):
    """GET /api/system/permissions — full RBAC registry snapshot.

    Used by the audit matrix UI on /system/permissions. The deep
    blocks (role_data, routes, audit_summary) are typed as
    dict[str, Any] / list[dict[str, Any]] because they carry per-role
    and per-route metadata whose shape varies (built-in vs custom
    roles, overrides present vs absent, etc.).
    """
    model_config = ConfigDict(extra="allow")

    permissions: dict[str, Any] = Field(
        ...,
        description="Map of permission name -> {description, sensitive: bool}.",
    )
    roles: dict[str, list[str]] = Field(
        ...,
        description="Backward-compatible flat map of role -> resolved permissions.",
    )
    role_data: dict[str, Any] = Field(
        ...,
        description=(
            "Per-role metadata: kind (built_in|custom), display_name, "
            "default_permissions, resolved permissions, override deltas, "
            "and (for custom roles) created_by + created_at."
        ),
    )
    routes: list[dict[str, Any]] = Field(
        ...,
        description="Each registered route's permission + per-role last-accessed timestamps.",
    )
    public_routes: list[list[str]] = Field(
        ...,
        description="Routes that bypass auth — list of [method, path] pairs.",
    )
    audit_summary: dict[str, Any] = Field(
        ...,
        description="Allow/deny/shadow-mismatch counts + top-denial permissions over a window.",
    )
    shadow_mode: bool = Field(
        ...,
        description="True iff RBAC is running in shadow mode (decisions logged but not enforced).",
    )
    version: str = Field(..., description="Platform version string at the time of the snapshot.")


class RbacAuditEntry(BaseModel):
    """Single rbac_config_audit row — one RBAC config mutation."""
    id: int
    occurred_at: str
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str = Field(
        ...,
        description=(
            "One of 'grant', 'revoke', 'clear', 'create_role', 'delete_role', "
            "'impersonate_start', 'impersonate_end', 'password_reset_cli', "
            "'password_reset_request', 'password_reset_completed', "
            "'password_change_self', 'acl_grant', 'acl_revoke', 'set_default_policy'."
        ),
    )
    target_role: Optional[str] = None
    target_permission: Optional[str] = None
    target_resource_type: Optional[str] = Field(
        default=None,
        description="B248 (v0.9.10.7): present on acl_grant / acl_revoke / set_default_policy rows.",
    )
    target_resource_id: Optional[str] = Field(
        default=None,
        description="B248 (v0.9.10.7): present on acl_grant / acl_revoke rows.",
    )
    before_state: Optional[Any] = Field(default=None, description="JSONB before-state — shape depends on the action.")
    after_state: Optional[Any] = Field(default=None, description="JSONB after-state — shape depends on the action.")
    note: Optional[str] = None


class RbacAuditLogResponse(BaseModel):
    """GET /api/system/rbac-audit-log — paginated RBAC config mutations.

    Pagination is keyset on `id` descending. Pass `next_cursor` back as
    `?cursor=…` to fetch the next page.
    """
    entries: list[RbacAuditEntry]
    next_cursor: Optional[int] = None


# ── Users-with-permissions (B231) ────────────────────────────────────


class UserWithPermissions(BaseModel):
    """Per-user audit row in the matrix UI's Users tab."""
    id: str
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: bool
    permissions: list[str] = Field(
        default_factory=list,
        description="Resolved permission set for this user's role.",
    )
    last_activity_at: Optional[str] = None
    last_activity_route: Optional[str] = None


class UsersWithPermissionsResponse(BaseModel):
    """GET /api/system/users-with-permissions."""
    users: list[UserWithPermissions]


# ── Role overrides (B233) ────────────────────────────────────────────


class RoleOverrideResponse(BaseModel):
    """POST /api/system/role-overrides — newly written override row."""
    id: int
    role: str
    permission: str
    kind: str = Field(..., description="'grant' | 'revoke'.")
    created_by: str
    created_at: str
    note: Optional[str] = None


# ── Custom roles (B233) ──────────────────────────────────────────────


class CustomRoleCreateResponse(BaseModel):
    """POST /api/system/custom-roles — newly created custom role."""
    role: str
    display_name: str
    description: Optional[str] = None
    based_on: Optional[str] = None
    permissions: list[str] = Field(
        default_factory=list,
        description="Sorted seed permission set after sensitive-permission filtering.",
    )
    created_by: str


# ── B271 (v0.9.11.13): /api/system/resources response models ─────────


class ServerResourcesCpu(BaseModel):
    cpu_count: int
    cpu_model: Optional[str] = None


class ServerResourcesMemory(BaseModel):
    total_mb: int
    used_mb: int
    free_mb: int
    available_mb: int
    buff_cache_mb: int


class ServerResourcesSwap(BaseModel):
    total_mb: int
    used_mb: int
    free_mb: int


class ServerResourcesDisk(BaseModel):
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_pct: int


class ServerResourcesLoad(BaseModel):
    load_1m: float
    load_5m: float
    load_15m: float


class ServerResources(BaseModel):
    """Server-level metrics. Fields are Optional because the API runs
    on Linux production but also on macOS dev (no /proc/meminfo etc.)."""
    cpu: Optional[ServerResourcesCpu] = None
    memory: Optional[ServerResourcesMemory] = None
    swap: Optional[ServerResourcesSwap] = None
    disk_root: Optional[ServerResourcesDisk] = None
    load: Optional[ServerResourcesLoad] = None
    uptime_seconds: Optional[int] = None


class PostgresSummary(BaseModel):
    db_size_mb: int
    cache_hit_pct: float = Field(..., description="0-100; target > 99 on a healthy install")
    active_connections: int
    idle_connections: int
    max_connections: int
    pg_stat_statements_installed: bool


class TableStat(BaseModel):
    schema_: str = Field(..., alias="schema")
    name: str
    plugin: Optional[str] = Field(None, description="Plugin slug, or null for host-owned tables")
    total_size_mb: float
    data_mb: float
    index_mb: float
    rows: int
    dead_rows: int
    dead_pct: float
    last_vacuum: Optional[str] = None
    last_analyze: Optional[str] = None
    seq_scan_count: int
    idx_scan_count: int
    seq_scan_pct: float

    model_config = ConfigDict(populate_by_name=True)


class PluginStat(BaseModel):
    id: str
    table_count: int
    total_size_mb: float
    total_rows: int
    last_sync_at: Optional[str] = None
    sync_schedule_cron: Optional[str] = None


class SyncStat(BaseModel):
    plugin_id: str
    schedule_cron: str
    schedule_interval_seconds: int
    runs_24h: int
    errors_24h: int
    avg_duration_ms: Optional[int] = None
    max_duration_ms: Optional[int] = None
    cpu_load_pct_estimate: float = Field(
        ...,
        description="(avg_duration_ms × runs_24h) / 86_400_000 × 100, capped at 100. "
        "% of one CPU continuously consumed by this sync.",
    )


class IndexStat(BaseModel):
    schema_: str = Field(..., alias="schema")
    table: str
    name: str
    size_mb: float
    scans_lifetime: int
    tuples_read: int
    is_primary: bool = Field(
        default=False,
        description=(
            "True for primary-key indexes. Surfaced so the unused_index "
            "diagnostic rule can exclude PKs (load-bearing for INSERT / "
            "UPDATE / DELETE + foreign-key lookups regardless of "
            "idx_scan count)."
        ),
    )
    is_unique: bool = Field(
        default=False,
        description=(
            "True for unique indexes (including PKs). Same exclusion "
            "rationale as is_primary — unique indexes enforce a "
            "constraint, not just speed up lookups."
        ),
    )

    model_config = ConfigDict(populate_by_name=True)


class ResourcesResponse(BaseModel):
    """GET /api/system/resources — all server + Postgres + per-plugin metrics in one snapshot."""
    collected_at: str = Field(..., description="ISO 8601; cached 30s")
    server: ServerResources
    postgres: PostgresSummary
    tables: list[TableStat] = Field(default_factory=list, description="Top 50 by total size")
    plugins: list[PluginStat] = Field(default_factory=list, description="Sorted by total size desc")
    syncs: list[SyncStat] = Field(default_factory=list, description="Sorted by cpu_load_pct_estimate desc")
    indexes_largest: list[IndexStat] = Field(default_factory=list, description="Top 20 by size")
