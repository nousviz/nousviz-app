"""B215 (v0.9.10.2): typed responses for /api/settings/* and /api/connections/*.

Covers deploy keys (5 routes), connections CRUD (4 routes), and the
settings.git.set endpoint (1 route) — 10 total per the B215 plan.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Deploy keys ───────────────────────────────────────────────────────


class DeployKeyCreator(BaseModel):
    """Joined creator info on deploy_keys rows."""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None


class DeployKeyEntry(BaseModel):
    """A single deploy_keys row as returned by GET /api/settings/deploy-keys."""
    id: str
    name: str
    host: str
    repo_url: Optional[str] = None
    public_key: str
    fingerprint: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[DeployKeyCreator] = Field(
        default=None,
        description="The actor who created this key. Null if the user has been deleted.",
    )


class DeployKeysListResponse(BaseModel):
    """GET /api/settings/deploy-keys."""
    keys: list[DeployKeyEntry]


class DeployKeyCreateResponse(BaseModel):
    """POST /api/settings/deploy-keys — returns the new key's identity + public material.

    The private key is encrypted with NOUSVIZ_ENCRYPTION_KEY and stored;
    the response intentionally omits it.
    """
    id: str
    name: str
    host: str
    public_key: str
    fingerprint: str


class DeployKeyCheckResponse(BaseModel):
    """GET /api/settings/deploy-keys/check — does a key exist for `repo_url`?

    `match='repo'` indicates an exact-URL match (B204). The legacy
    host-fallback was removed; only exact URL hits return has_key=True.
    """
    has_key: bool
    key_name: Optional[str] = None
    match: Optional[str] = Field(default=None, description="'repo' for exact URL match.")


class DeployKeyDeleteResponse(BaseModel):
    """DELETE /api/settings/deploy-keys/{key_id}."""
    deleted: bool = True


class DeployKeyTestResponse(BaseModel):
    """POST /api/settings/deploy-keys/{key_id}/test — SSH-auth probe.

    `ok=True` means GitHub responded 'successfully authenticated'. The
    `detail` carries either the short SSH stderr or a timeout / failure
    description.
    """
    ok: bool
    detail: str = Field(..., description="Truncated SSH output (200 chars) or error description.")


# ── Connections ───────────────────────────────────────────────────────


class ConnectionRow(BaseModel):
    """A single connections row.

    `config` is the JSONB blob with the password masked as '••••••••'.
    Plugin-managed connections have name='plugin:<slug>' and store
    credentials in the credentials table instead of in config.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    type: str = Field(..., description="'postgres' | 'mysql' | 'clickhouse'.")
    config: dict[str, Any] = Field(
        ...,
        description="Connection config. The 'password' field is replaced with '••••••••' when set.",
    )
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_health_check: Optional[str] = None
    health_history: Optional[list[dict[str, Any]]] = None


class ConnectionsListResponse(BaseModel):
    """GET /api/connections — all connections."""
    connections: list[ConnectionRow]


class ConnectionDeleteResponse(BaseModel):
    """DELETE /api/connections/{conn_id}."""
    deleted: bool = True


# ── Settings.git ──────────────────────────────────────────────────────


class GitSettingsGetResponse(BaseModel):
    """GET /api/settings/git — boolean status + masked token preview.

    Never exposes the full token. The `github_token_preview` field is
    `<first8>...<last4>` for tokens longer than 12 chars, or '••••'
    when only short/redacted tokens are stored.
    """
    github_token_set: bool = Field(..., description="True iff GITHUB_TOKEN is set in the environment.")
    github_token_preview: str = Field(
        ...,
        description="Masked preview of the token. Empty string when no token is set.",
    )


class GitSettingsSaveResponse(BaseModel):
    """POST /api/settings/git — confirms env update."""
    ok: bool = True


# ── Database settings ────────────────────────────────────────────────


class DatabaseSettingsResponse(BaseModel):
    """GET /api/settings/database — current Postgres config without password."""
    host: str
    port: str
    db: str
    user: str
    sslmode: str


class DatabaseSaveResponse(BaseModel):
    """POST /api/settings/database — confirms write + post-write probe.

    `version` is the live Postgres version when the new connection
    succeeds. `error` carries the failure message when the new config
    can't connect (the .env was still patched — operator can fix and
    retry).
    """
    ok: bool
    version: Optional[str] = None
    error: Optional[str] = None


# ── Email / SMTP settings ────────────────────────────────────────────


class EmailSettingsResponse(BaseModel):
    """GET /api/settings/email — SMTP config without password."""
    host: str
    port: str
    username: str
    from_address: str
    from_name: str
    use_tls: str
    configured: bool


class EmailSaveResponse(BaseModel):
    """POST /api/settings/email — confirms SMTP env write."""
    ok: bool = True


class EmailTestResponse(BaseModel):
    """POST /api/settings/email/test — send a test email + report outcome."""
    ok: bool
    error: Optional[str] = None
    sent_to: Optional[str] = None


# ── API keys (settings) ──────────────────────────────────────────────


class ApiKeyEntry(BaseModel):
    """A single api_keys row (prefix + metadata only — never the raw key)."""
    id: str
    name: str
    key_prefix: str
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None


class ApiKeySettingsCreateResponse(BaseModel):
    """POST /api/settings/api-keys — newly created key (raw key included once)."""
    id: str
    name: str
    key_prefix: str
    key: str = Field(..., description="Raw API key — shown exactly once at creation.")
    created_at: Optional[str] = None
    message: str


class ApiKeySettingsRevokeResponse(BaseModel):
    """DELETE /api/settings/api-keys/{key_id}."""
    revoked: bool = True


# ── Connections remainder (B216 phase 6) ─────────────────────────────


class ConnectionTestResponse(BaseModel):
    """POST /api/connections/{conn_id}/test — connectivity probe.

    `ok` reflects whether the engine accepted the credentials and
    responded to a version query. `detail` carries the engine version
    string on success or a short failure description.
    """
    ok: bool
    detail: Optional[str] = None
    error: Optional[str] = None


class ConnectionHealthCheckResponse(BaseModel):
    """POST /api/connections/{conn_id}/health-check — probe + persist."""
    status: str = Field(..., description="'connected' | 'error'.")
    detail: str
    checked_at: str = Field(..., description="ISO-8601 timestamp of the check.")


class ConnectionHealthHistoryEntry(BaseModel):
    """A single entry in the connection's health_history JSONB."""
    model_config = ConfigDict(extra="allow")

    status: str
    detail: Optional[str] = None
    checked_at: Optional[str] = None


class ConnectionHealthHistoryResponse(BaseModel):
    """GET /api/connections/{conn_id}/health-history — last 20 health checks."""
    status: Optional[str] = Field(default=None, description="Most recent health_status value.")
    last_check: Optional[str] = None
    history: list[ConnectionHealthHistoryEntry] = Field(
        default_factory=list,
        description="Newest-first; capped at 20 entries.",
    )


class MysqlInitDefaultResponse(BaseModel):
    """POST /api/connections/mysql/init-default — create + set default DB."""
    ok: bool = True
    detail: str
