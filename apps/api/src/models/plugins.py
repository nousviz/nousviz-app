"""B215 (v0.9.10.2): typed responses for /api/plugins/* routes.

Plugin manifests are open-ended by design — each plugin author declares
their own dashboards, datasets, actions, capabilities, frontend
components, and so on. We model the consistent envelope (id, version,
status, etc.) and use `ConfigDict(extra='allow')` for the long tail of
plugin-author-defined fields. The corresponding schema in /openapi.json
correctly documents the known shape without falsely promising a closed
field set.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared sub-shapes ─────────────────────────────────────────────────


class UpdateStatus(BaseModel):
    """plugin_update_status block attached to plugin entries (B144)."""
    source_class: str = Field(
        ...,
        description="'pending' | 'github' | 'community' | 'official' — where the update check looked.",
    )
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    update_available: bool = False
    last_error: Optional[str] = None


class FrontendComponent(BaseModel):
    """Single frontend component declared in plugin.yaml (B151)."""
    name: str
    path: str


class FrontendBlock(BaseModel):
    """Frontend trust + component declarations (B151)."""
    components: list[FrontendComponent] = Field(
        default_factory=list,
        description="React components declared in the plugin's frontend.components manifest block.",
    )
    trusted: bool
    needs_consent: bool
    admin_proxy: bool = Field(
        default=False,
        description=(
            "B304 (v0.10.0.5): plugin opts into the path-scoped admin-session "
            "cookie auth path. When true, the auth middleware accepts a "
            "nv_admin_<slug> cookie for requests under /api/plugins/<slug>/admin/* "
            "in addition to the existing X-Session-Token / X-API-Key headers. "
            "Cookies are minted by the plugin's own bridge endpoint via "
            "nousviz_sdk.auth.issue_admin_session_cookie(). Default false: "
            "middleware enforces header-based auth as today."
        ),
    )


class LoadStatus(BaseModel):
    """Plugin loader runtime state (P204).

    `routes_registered=true` means the plugin's api/routes.py imported
    cleanly at API startup. False means the loader caught an exception;
    `failure_reason` carries the class + message (the full traceback
    stays in app_logs for admin-visible debugging).
    """
    routes_registered: bool
    stage: Optional[str] = Field(default=None, description="Where the loader was when it failed.")
    failure_reason: Optional[str] = None


# ── Plugin entry / detail ─────────────────────────────────────────────


class PluginEntry(BaseModel):
    """Single plugin entry from /plugins or /plugins/{id}.

    Carries the consistent envelope (id, version, display_name, status)
    plus any number of plugin-author-defined fields (dashboards,
    datasets, actions, settings, capabilities, …). The `extra='allow'`
    config is intentional — plugin manifests are open-ended.
    """
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = Field(default=None, description="Plugin slug (matches the directory name).")
    display_name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    update_status: Optional[UpdateStatus] = None
    frontend: Optional[FrontendBlock] = None
    load_status: Optional[LoadStatus] = None


class PluginListResponse(BaseModel):
    """GET /api/plugins — installed plugins only."""
    plugins: list[PluginEntry]


# ── Install / uninstall ───────────────────────────────────────────────


class PluginInstallResponse(BaseModel):
    """POST /api/plugins/{id}/install — success path.

    Returns `status='already_installed'` when the plugin's directory
    already exists (idempotent). Otherwise `status='installed'` with
    the manifest plus migrations + route-load status.
    """
    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="'installed' | 'already_installed'.")
    plugin: PluginEntry
    migrations_applied: Optional[list[str]] = None
    routes_active: Optional[bool] = None


class UninstallDependent(BaseModel):
    """Single dependent plugin in the has_dependents response."""
    plugin: str
    display_name: str


class PluginUninstallResponse(BaseModel):
    """DELETE /api/plugins/{id}/install.

    Two response shapes:
    - `status='has_dependents'` (when other plugins depend on this one
      and `cascade=false`): the frontend should prompt the operator to
      confirm cascade or cancel. `dependents` lists the affected plugins.
    - `status='uninstalled'` (success): lists what was removed and
      whether data was kept or dropped.
    """
    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="'uninstalled' | 'has_dependents'.")
    dependents: Optional[list[UninstallDependent]] = None
    uninstalled: Optional[list[str]] = None
    uninstalled_names: Optional[list[str]] = None
    data_removed: Optional[bool] = Field(
        default=None,
        description="Operator's checkbox state at uninstall time. For the actual outcome, see data_tables_dropped + data_tables_drop_failed.",
    )
    # B278 (v0.9.11.14): actual outcome of data removal, distinct from intent.
    data_tables_dropped: Optional[list[str]] = Field(
        default=None,
        description="Tables actually dropped (via manifest's databases.postgres.tables[]). Empty when remove_data=False or plugin declared no tables. Idempotent — re-uninstall produces the same list.",
    )
    data_tables_drop_failed: Optional[list[dict]] = Field(
        default=None,
        description="Per-table DROP failures with reason strings. Empty on success. Operators use this to manually clean up tables the platform couldn't drop.",
    )
    migrations_run: Optional[list[str]] = Field(
        default=None,
        description="*_down.sql migration files executed (plugin author's intended cleanup). Defense-in-depth manifest-table drop in data_tables_dropped runs in addition.",
    )
    # B281 (v0.9.11.21): per-kind reference cleanup outcomes. Null when
    # the operator did not opt in (?remove_references=false).
    references_removed: Optional[bool] = Field(
        default=None,
        description="Operator's checkbox state at uninstall time. For the actual cleanup outcome, see references_cleanup.",
    )
    references_cleanup: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Per-kind cleanup outcomes when remove_references=true. Shape: "
            "{annotations_deleted: [{id, title}], shares_deleted: [{id, label}], "
            "fusions_repointed: [{id, name}], alerts_left_alone: [{id, name}], "
            "failed: [{kind, id, error}]}. Null when operator didn't opt in."
        ),
    )
    restart_required: Optional[bool] = None
    note: Optional[str] = None


# ── Sync status ───────────────────────────────────────────────────────


class SyncRunCurrent(BaseModel):
    """In-flight sync run — populated when status IN ('queued','running','cancelling')."""
    run_id: int
    status: str
    source: Optional[str] = Field(default=None, description="Who triggered this run (manual/scheduler/api).")
    started_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    progress: dict[str, Any] = Field(
        default_factory=dict,
        description="Live progress payload from the worker — shape is plugin-defined.",
    )
    elapsed_sec: int


class SyncRunSuccess(BaseModel):
    """Most recent successful run."""
    run_id: int
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    rows_written: Optional[int] = None
    source: Optional[str] = None


class SyncRunFailure(BaseModel):
    """Most recent failed run (status IN ('error','timeout','cancelled'))."""
    run_id: int
    completed_at: Optional[str] = None
    status: str = Field(..., description="'error' | 'timeout' | 'cancelled'.")
    error: Optional[str] = Field(default=None, description="Truncated to 500 chars if longer.")
    source: Optional[str] = None


class SyncStatusResponse(BaseModel):
    """GET /api/plugins/{id}/sync/status — composite snapshot for the Sync card.

    `current` is the in-flight run, or null when idle. `last_success` /
    `last_failure` are the most recent terminal runs. `last_sync` mirrors
    `last_success.completed_at` for backward compatibility with pre-v0.9.6
    frontend code.
    """
    current: Optional[SyncRunCurrent] = None
    last_success: Optional[SyncRunSuccess] = None
    last_failure: Optional[SyncRunFailure] = None
    last_sync: Optional[str] = None


# ── Sync schedule ─────────────────────────────────────────────────────


class SyncScheduleRegistry(BaseModel):
    """sync_schedule_registry row — what the scheduler is actively tracking."""
    cron_expression: Optional[str] = None
    cron_source: Optional[str] = Field(default=None, description="'manifest' | 'override'.")
    next_fire_at: Optional[str] = None
    last_enqueued_at: Optional[str] = None
    last_run_id: Optional[int] = None
    last_error: Optional[str] = None
    updated_at: Optional[str] = None


class SyncScheduleGetResponse(BaseModel):
    """GET /api/plugins/{id}/sync-schedule — composite read used by the Settings tab."""
    plugin_id: str
    manifest_cron: Optional[str] = Field(default=None, description="Cron from plugin.yaml (sync.schedule).")
    manifest_cron_display: Optional[str] = Field(default=None, description="Human label for manifest_cron, when expressible.")
    override_cron: Optional[str] = None
    override_cron_display: Optional[str] = None
    effective_cron: Optional[str] = Field(default=None, description="override_cron when set, else manifest_cron.")
    effective_cron_display: Optional[str] = None
    source: str = Field(..., description="'override' | 'manifest'.")
    registry: Optional[SyncScheduleRegistry] = None
    scheduler_alive: bool = Field(
        ...,
        description="True iff the scheduler row was updated within the last 5 minutes.",
    )


class SyncScheduleSetResponse(BaseModel):
    """POST /api/plugins/{id}/sync-schedule — write or clear an override."""
    saved: bool
    override_cron: Optional[str] = Field(
        default=None,
        description="The newly-stored override, or null when clearing.",
    )
    preview_next_fires: list[str] = Field(
        default_factory=list,
        description="Up to 5 ISO-8601 firing times from now under the new cron.",
    )
    note: Optional[str] = None


# ── Connections ───────────────────────────────────────────────────────


class ConnectionField(BaseModel):
    """Single field declaration from a plugin's connections.fields list.

    extra='allow' covers manifest-author-defined keys (placeholder, help
    text, validation hints). Stored in plugin.yaml verbatim.
    """
    model_config = ConfigDict(extra="allow")

    name: str
    label: Optional[str] = None
    type: Optional[str] = Field(default=None, description="'text' | 'password' | 'select' | etc.")
    default: Optional[Any] = None
    required: Optional[bool] = None


class ConnectionEntry(BaseModel):
    """Single connection block in the get-connections response."""
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    fields: list[ConnectionField] = Field(
        default_factory=list,
        description="Field declarations from plugin.yaml's connections.fields block.",
    )
    values: dict[str, Any] = Field(
        default_factory=dict,
        description="Field values keyed by field name. Secret fields are masked as '••••••••'.",
    )


class PluginConnectionsResponse(BaseModel):
    """GET /api/plugins/{id}/connections."""
    connections: list[ConnectionEntry] = Field(
        default_factory=list,
        description="One entry per connection block in the plugin's manifest (typically one).",
    )


class SaveConnectionsHealthBlock(BaseModel):
    """Health-check result attached to save-connections responses when
    the plugin declares a `health_check:` hook."""
    model_config = ConfigDict(extra="allow")

    ok: bool
    error: Optional[str] = None
    version: Optional[str] = None


class PluginConnectionsSaveResponse(BaseModel):
    """POST /api/plugins/{id}/connections — confirms write + post-save health check."""
    ok: bool = True
    health: Optional[SaveConnectionsHealthBlock] = Field(
        default=None,
        description="Result of the plugin's health_check hook, or null if none declared.",
    )


# ── Settings ──────────────────────────────────────────────────────────


class PluginSettingEntry(BaseModel):
    """Single setting key/value pair from plugin_settings."""
    key: str
    value: Any = Field(..., description="JSONB value — type depends on the plugin's setting declaration.")


class PluginSettingsResponse(BaseModel):
    """GET /api/plugins/{id}/settings — current saved settings.

    `_conn.*` keys are excluded (they belong to the /connections surface).
    """
    settings: list[PluginSettingEntry] = Field(
        default_factory=list,
        description="Saved settings, one entry per declared key in the manifest's settings block.",
    )


class PluginSettingsSaveResponse(BaseModel):
    """POST /api/plugins/{id}/settings — confirms upsert."""
    ok: bool = True


# ── Audit + capabilities + catalog ────────────────────────────────────


class PluginAuditEntry(BaseModel):
    """A single plugin_audit_log row."""
    model_config = ConfigDict(extra="allow")

    plugin_id: str
    action: str
    detail: Optional[Any] = None
    ip_address: Optional[str] = None
    created_at: Optional[str] = None
    user_name: Optional[str] = None


class PluginAuditLogResponse(BaseModel):
    """GET /api/plugins/audit-log — recent plugin lifecycle events."""
    entries: list[PluginAuditEntry]


class PluginCapabilitiesResponse(BaseModel):
    """GET /api/plugins/capabilities — capabilities registered by utility plugins."""
    capabilities: list[str]


class PluginCatalogResponse(BaseModel):
    """GET /api/plugins/catalog — full plugin catalog (Marketplace page).

    Combines official + installed + community + utilities. Each entry
    includes installed flag, install_count, featured flag, pricing_model.
    Sorted: featured first, then by install_count desc.
    """
    plugins: list[PluginEntry]


# ── Updates ───────────────────────────────────────────────────────────


class PluginUpdateInfo(BaseModel):
    """Cached plugin update status for one plugin (B144)."""
    plugin_id: str
    source_class: str = Field(
        ...,
        description="'first_party' | 'github' | 'pending' — origin of the update check.",
    )
    source_url: Optional[str] = None
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    update_available: bool = False
    last_error: Optional[str] = None


class PluginUpdatesListResponse(BaseModel):
    """GET /api/plugins/updates — bulk status across every installed plugin."""
    updates: list[PluginUpdateInfo]


class PluginUpdateResponse(BaseModel):
    """POST /api/plugins/{id}/update — atomic-swap update result (B145)."""
    model_config = ConfigDict(extra="allow")

    status: str = Field(default="updated", description="Always 'updated' on success.")
    plugin_id: str
    from_version: Optional[str] = None
    to_version: Optional[str] = None
    resolved_tag: Optional[str] = None
    source_class: Optional[str] = None
    source_url: Optional[str] = None
    migrations_applied: Optional[list[str]] = None
    note: Optional[str] = None


class InstallTestResponse(BaseModel):
    """POST /api/plugins/{id}/install/test — pre-install repo connectivity probe."""
    ok: bool = True
    message: str
    display_name: Optional[str] = None
    version: Optional[str] = None


# ── Uninstall check ───────────────────────────────────────────────────


class UninstallCheckTable(BaseModel):
    """Table that would be dropped if remove_data=true."""
    table: str
    engine: str = Field(..., description="'postgres' | 'clickhouse' | etc.")


class UninstallCheckTableWithSize(BaseModel):
    """B280 (v0.9.11.15): per-table data for the honest uninstall modal —
    name + current row count + size on disk. Drives the "exactly what will
    be dropped" disclosure block."""
    name: str
    size_mb: float
    rows: int


class UninstallCheckDataDir(BaseModel):
    """Filesystem data directory under data/{slug}/."""
    path: str
    size_mb: float


class UninstallCheckDependent(BaseModel):
    """Plugin that depends on the one being uninstalled."""
    model_config = ConfigDict(extra="allow")

    plugin: str
    display_name: str


class UninstallCheckResponse(BaseModel):
    """GET /api/plugins/{id}/uninstall-check — info for the confirmation modal."""
    plugin_id: str
    display_name: str
    type: Optional[str] = None
    dependents: list[UninstallCheckDependent] = Field(
        default_factory=list,
        description="Other installed plugins that depend on this one — uninstalling without cascade is blocked.",
    )
    references: list[Any] = Field(
        default_factory=list,
        description="External references to this plugin (fusions, dashboards, etc.).",
    )
    tables: list[UninstallCheckTable] = Field(
        default_factory=list,
        description="DB tables that would be dropped if remove_data=true.",
    )
    data_dirs: list[UninstallCheckDataDir] = Field(
        default_factory=list,
        description="Filesystem data dirs under data/{slug}/ (utility plugins).",
    )
    has_dependents: bool
    has_references: bool
    has_data: bool
    # B280 (v0.9.11.15): per-table size + row count for the honest
    # uninstall modal. Empty when the plugin declares no Postgres tables
    # or all declared tables are missing from pg_class.
    tables_to_drop_if_data_removed: list[UninstallCheckTableWithSize] = Field(
        default_factory=list,
        description="Each Postgres table the plugin declares with its current size + row count. Drives the 'exactly what will be dropped' disclosure on the uninstall modal.",
    )
    tables_to_drop_total_size_mb: float = Field(
        default=0.0,
        description="Sum of size_mb across tables_to_drop_if_data_removed.",
    )
    tables_to_drop_total_count: int = Field(
        default=0,
        description="len(tables_to_drop_if_data_removed). Frontend uses this to decide whether to render the DELETE button at all.",
    )


# ── Modules ───────────────────────────────────────────────────────────


class PluginModuleNavigation(BaseModel):
    label: str
    path: str


class PluginModuleDashboard(BaseModel):
    name: str
    label: str


class PluginModuleEntry(BaseModel):
    """A single plugin module (sub-package within a plugin)."""
    model_config = ConfigDict(extra="allow")

    name: str
    display_name: str
    description: Optional[str] = None
    version: Optional[str] = None
    enabled: bool
    enabled_by_default: bool
    dashboards: list[PluginModuleDashboard] = Field(
        default_factory=list,
        description="Dashboards declared in module.yaml.",
    )
    navigation: list[PluginModuleNavigation] = Field(
        default_factory=list,
        description="Navigation entries declared in module.yaml.",
    )
    tables: list[str] = Field(
        default_factory=list,
        description="Postgres tables owned by this module (from module.yaml databases.postgres.tables).",
    )
    has_routes: bool
    has_settings: bool
    settings: list[Any] = Field(
        default_factory=list,
        description="Setting declarations from module.yaml — shape varies.",
    )


class PluginModulesListResponse(BaseModel):
    """GET /api/plugins/{id}/modules."""
    modules: list[PluginModuleEntry]


class PluginModuleToggleResponse(BaseModel):
    """POST /api/plugins/{id}/modules/{module_name}/{enable|disable}."""
    ok: bool = True
    message: str


# ── Frontend components (B151) ────────────────────────────────────────


class FrontendComponentEntry(BaseModel):
    """Augmented component entry — manifest declaration + on-disk presence."""
    name: str
    path: str
    filename: str
    exists_on_disk: bool


class PluginFrontendComponentsResponse(BaseModel):
    """GET /api/plugins/{id}/frontend-components."""
    plugin_id: str
    components: list[FrontendComponentEntry]
    trusted: bool
    needs_consent: bool
    admin_proxy: bool = Field(
        default=False,
        description="B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path. Surfaced here so the trust banner can render the admin-proxy consent line.",
    )


class TrustFrontendResponse(BaseModel):
    """POST /api/plugins/{id}/trust-frontend."""
    plugin_id: str
    trusted: bool = True
    components: list[FrontendComponent] = Field(
        default_factory=list,
        description="Components now permitted to render after operator trust grant.",
    )


class RevokeFrontendTrustResponse(BaseModel):
    """POST /api/plugins/{id}/revoke-frontend-trust."""
    plugin_id: str
    trusted: bool = False


# ── By-name resources (alerts/dashboards/datasets) ────────────────────


class PluginYamlResource(BaseModel):
    """A YAML-defined resource (alert, dashboard, dataset) returned verbatim.

    Schema is plugin-author-defined; we return whatever the YAML deserialises to.
    """
    model_config = ConfigDict(extra="allow")
