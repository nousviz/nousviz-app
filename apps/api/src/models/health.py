"""B215 (v0.9.10.2): typed responses for /api/health/* routes.

The /health endpoint returns a deeply-nested status report. Models here
match the actual return shape from `apps/api/src/routes/health.py`.

Where fields are dicts of unknown shape (e.g. plugin-author-defined
service entries from utility plugins), we use `dict[str, Any]` and
document the contract in the field description rather than overspecifying.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── /health ───────────────────────────────────────────────────────────


class StatsBlock(BaseModel):
    """Aggregate counts surfaced in /health for the operator dashboard."""
    active_alerts: int = Field(..., description="Count of currently-firing alerts.")
    fusions: int = Field(..., description="Count of configured fusions.")
    annotations: int = Field(..., description="Count of operator annotations.")
    installed_plugins: int = Field(..., description="Count of plugins installed locally.")
    plugin_tables: int = Field(..., description="Count of plugin-managed tables in Postgres.")
    active_shares: int = Field(..., description="Count of non-revoked shared links.")


class SSLBlock(BaseModel):
    """SSL config status when NOUSVIZ_SSL is set. Absent on HTTP-only deployments.

    Shape mirrors `_get_ssl_status()` in routes/health.py — `enabled`
    and `type` are always present; `domain` and `expires` are present
    when applicable.
    """
    enabled: bool = Field(..., description="Always True when this block is present.")
    type: str = Field(..., description="SSL provisioning mode, e.g. 'letsencrypt'.")
    domain: Optional[str] = Field(default=None, description="Configured domain when set.")
    expires: Optional[str] = Field(
        default=None,
        description="Cert expiry as reported by `openssl x509 -enddate`. Present only when the cert is readable.",
    )


class HealthResponse(BaseModel):
    """Top-level /health payload.

    Status is degraded when Postgres reports degraded, the SDK is
    unavailable, or critical tables are missing. Frontend `evaluateChecks`
    drives banner display from this shape.
    """
    status: str = Field(
        ...,
        description="Overall instance status. 'healthy' | 'degraded'.",
        examples=["healthy"],
    )
    version: str = Field(..., description="Platform version (matches /VERSION).")
    startup_time: str = Field(..., description="When this API process started, ISO-8601.")
    timestamp: str = Field(..., description="When this response was generated, ISO-8601.")
    services: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Per-service health blocks. The 'postgres' key always exists with shape "
            "{status, version?, tables?, critical_tables_present?, critical_tables_total?, "
            "missing_critical_tables?, drift_hint?}. Utility-plugin entries have shape "
            "{status, version?}."
        ),
    )
    runtime: dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime check blocks. Currently contains 'sdk' with shape {status, version, import_error?}.",
    )
    stats: StatsBlock
    ssl: Optional[SSLBlock] = Field(
        default=None,
        description="SSL config status. Present iff NOUSVIZ_SSL is set in the environment.",
    )


# ── /health/config ────────────────────────────────────────────────────


class HealthConfigResponse(BaseModel):
    """Boolean status of security-sensitive config — never the values themselves."""
    encryption_key_set: bool = Field(..., description="True iff NOUSVIZ_ENCRYPTION_KEY is set.")
    auth_required: bool = Field(..., description="True iff AUTH_REQUIRED=true in .env.")
    superadmin_exists: bool = Field(..., description="True iff at least one superadmin user row exists.")
    postgres_password_is_default: bool = Field(
        ...,
        description="Always False since S108 (v0.8.1) — kept for response-shape back-compat.",
    )
    smtp_configured: bool = Field(..., description="True iff SMTP_HOST is set.")
    update_available: bool = Field(..., description="True iff a newer release is available on GitHub.")
    update_latest: Optional[str] = Field(default=None, description="Latest release tag if known.")
    update_current: Optional[str] = Field(default=None, description="Currently-running version.")


# ── /health/connections ───────────────────────────────────────────────


class ConnectionIssue(BaseModel):
    """A single banner-displayable connection health issue."""
    plugin_id: str
    severity: str = Field(..., description="'warning' | 'error'")
    message: str
    detail: Optional[dict[str, Any]] = None


class ConnectionHealthResponse(BaseModel):
    """List of banner-shaped connection health issues across plugins."""
    issues: list[ConnectionIssue] = Field(
        default_factory=list,
        description="May be empty when no plugin reports an issue.",
    )


# ── /health/log + /health/record + SSL setup ─────────────────────────


class HealthLogRow(BaseModel):
    """A single health_log entry — a snapshot of a periodic check."""
    model_config = ConfigDict(extra="allow")

    id: int
    level: str = Field(..., description="'healthy' | 'warning' | 'error'.")
    checks: Any = Field(
        default=None,
        description="JSONB array of check-result dicts (id, status, label, detail).",
    )
    postgres_ok: Optional[bool] = None
    tables: Optional[int] = None
    version: Optional[str] = None
    created_at: Optional[str] = None


class HealthLogResponse(BaseModel):
    """GET /api/health/log — recent health-check snapshots, newest-first."""
    log: list[HealthLogRow]
    count: int


class HealthRecordResponse(BaseModel):
    """POST /api/health/record — new snapshot persisted."""
    status: str = Field(default="recorded", description="Always 'recorded' on success.")
    level: str = Field(..., description="'healthy' | 'warning' | 'error'.")
    checks: int = Field(..., description="Count of checks in this snapshot.")


class SslSetupResponse(BaseModel):
    """POST /api/admin/ssl/setup — Let's Encrypt provisioning result.

    On success, `ssl` carries the new SSL config (mirrors `_get_ssl_status`).
    On failure, `reason` carries a machine-readable classification (e.g.
    'timeout', 'dns_no_match') and `error` carries the human-readable message.
    """
    model_config = ConfigDict(extra="allow")

    ok: bool
    output: Optional[str] = None
    ssl: Optional[SSLBlock] = None
    reason: Optional[str] = Field(
        default=None,
        description="Failure classification when ok=false (e.g. 'timeout', 'dns_no_match').",
    )
    error: Optional[str] = None
