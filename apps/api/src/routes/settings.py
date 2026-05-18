"""
/api/settings — Runtime-configurable settings
"""

import os
import hashlib
import secrets
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import reset_pg_pool, get_pg_conn
from .._env import write_and_reload as _write_and_reload, ENV_FILE
from .activity import record_activity
from .auth import get_me
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.settings import (
    ApiKeyEntry,
    ApiKeySettingsCreateResponse,
    ApiKeySettingsRevokeResponse,
    DatabaseSaveResponse,
    DatabaseSettingsResponse,
    DeployKeyCheckResponse,
    DeployKeyCreateResponse,
    DeployKeyDeleteResponse,
    DeployKeyTestResponse,
    DeployKeysListResponse,
    EmailSaveResponse,
    EmailSettingsResponse,
    EmailTestResponse,
    GitSettingsGetResponse,
    GitSettingsSaveResponse,
)

logger = logging.getLogger("nousviz.api.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])

# B228: register settings routes. Reads use settings.read (viewer+),
# matching the existing _require_auth (any authenticated user).
# Writes use settings.write (admin+) matching _require_admin.
register_route("GET", "/api/settings/database", "settings.read")
register_route("POST", "/api/settings/database", "settings.write")
register_route("GET", "/api/settings/email", "settings.read")
register_route("POST", "/api/settings/email", "settings.write")
register_route("GET", "/api/settings/git", "settings.read")
register_route("POST", "/api/settings/git", "settings.write")
register_route("POST", "/api/settings/email/test", "settings.write")
register_route("GET", "/api/settings/api-keys", "settings.read")
register_route("POST", "/api/settings/api-keys", "settings.write")
register_route("DELETE", "/api/settings/api-keys/{key_id}", "settings.write")
register_route("GET", "/api/settings/deploy-keys", "settings.read")
register_route("POST", "/api/settings/deploy-keys", "settings.write")
register_route("GET", "/api/settings/deploy-keys/check", "settings.read")
register_route("DELETE", "/api/settings/deploy-keys/{key_id}", "settings.write")
register_route("POST", "/api/settings/deploy-keys/{key_id}/test", "settings.write")


def _require_auth(request: Request) -> None:
    """
    Reject the request if no authenticated identity is present.

    When AUTH_REQUIRED=false (local dev), settings are open — no auth needed.
    When AUTH_REQUIRED=true, a valid session, API key, or CF header is required.
    """
    auth_required = os.environ.get("AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
    if not auth_required:
        return  # Local dev — settings open

    identity = getattr(request.state, "user_identity", None)
    if identity:
        return  # middleware already validated

    from ..middleware.auth import get_authenticated_identity
    identity = get_authenticated_identity(request)
    if not identity:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

REPO_ROOT = Path(__file__).resolve().parents[4]

# Keys managed by the database settings form
_PG_ENV_KEYS = {
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_SSLMODE",
}


def _read_env_file() -> dict[str, str]:
    """Parse .env into a dict, preserving only key=value lines."""
    result: dict[str, str] = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            k, _, v = stripped.partition("=")
            result[k.strip()] = v.strip()
    return result


# ── GET /api/settings/database ────────────────────────────────────────

@router.get(
    "/database",
    operation_id="settings.database.get",
    response_model=DatabaseSettingsResponse,
    summary="Read Postgres connection config (no password)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def get_database_settings(
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    """Return current Postgres config (no passwords)."""
    _require_auth(request)
    env = _read_env_file()
    return {
        "host":    env.get("POSTGRES_HOST", os.environ.get("POSTGRES_HOST", "localhost")),
        "port":    env.get("POSTGRES_PORT", os.environ.get("POSTGRES_PORT", "5432")),
        "db":      env.get("POSTGRES_DB",   os.environ.get("POSTGRES_DB",   "nousviz")),
        "user":    env.get("POSTGRES_USER",  os.environ.get("POSTGRES_USER", "nousviz")),
        "sslmode": env.get("POSTGRES_SSLMODE", os.environ.get("POSTGRES_SSLMODE", "prefer")),
        # Password intentionally omitted
    }


# ── POST /api/settings/database ───────────────────────────────────────

class DatabaseSettings(BaseModel):
    host:     str
    port:     int
    db:       str
    user:     str
    password: str | None = None  # None = keep existing
    sslmode:  str = "prefer"


@router.post(
    "/database",
    operation_id="settings.database.set",
    response_model=DatabaseSaveResponse,
    response_model_exclude_none=True,
    summary="Save Postgres config + reconnect pool (no restart)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
    },
)
async def save_database_settings(
    body: DatabaseSettings,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """
    Update Postgres connection settings in .env and in the live process,
    then reconnect the pool — no API restart needed.

    On connect failure, the .env was still patched. The response carries
    `ok=false` + `error` so the operator can fix and retry. Reverting to
    the prior config requires editing .env on disk.
    """
    admin = get_me(request)
    # Build the updates dict
    updates: dict[str, str] = {
        "POSTGRES_HOST":    body.host,
        "POSTGRES_PORT":    str(body.port),
        "POSTGRES_DB":      body.db,
        "POSTGRES_USER":    body.user,
        "POSTGRES_SSLMODE": body.sslmode,
    }
    if body.password:
        updates["POSTGRES_PASSWORD"] = body.password

    # 1. Persist to .env + patch THIS worker's os.environ + schedule pm2 reload
    # for sibling workers. write_and_reload bundles these three steps (B190).
    # If .env is unwritable (read-only FS), fall back to env-only so the
    # handling worker at least reflects the change for the connection test.
    try:
        _write_and_reload(updates)
    except Exception as e:
        logger.warning(f"Could not write .env: {e} — updating live process only")
        for k, v in updates.items():
            os.environ[k] = v

    # 2. Drop the old pool — next request will reconnect with new settings
    reset_pg_pool()

    # 3. Test the new connection (in this worker — its os.environ is already patched)
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            pg_version = cur.fetchone()[0].split(" on ")[0]
        record_activity("settings_update", detail={"setting": "database"}, user_id=admin.get("id"))
        return {"ok": True, "version": pg_version}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Email / SMTP settings ────────────────────────────────────────────


@router.get(
    "/email",
    operation_id="settings.email.get",
    response_model=EmailSettingsResponse,
    summary="Read SMTP config (no password)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def get_email_settings(
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    """Return current SMTP config (no password — display only)."""
    _require_auth(request)
    env = _read_env_file()
    return {
        "host": env.get("SMTP_HOST", os.environ.get("SMTP_HOST", "")),
        "port": env.get("SMTP_PORT", os.environ.get("SMTP_PORT", "587")),
        "username": env.get("SMTP_USERNAME", os.environ.get("SMTP_USERNAME", "")),
        "from_address": env.get("SMTP_FROM_ADDRESS", os.environ.get("SMTP_FROM_ADDRESS", "")),
        "from_name": env.get("SMTP_FROM_NAME", os.environ.get("SMTP_FROM_NAME", "NousViz")),
        "use_tls": env.get("SMTP_USE_TLS", os.environ.get("SMTP_USE_TLS", "true")),
        "configured": bool(env.get("SMTP_HOST") or os.environ.get("SMTP_HOST", "").strip()),
    }


class EmailSettings(BaseModel):
    host: str
    port: int = 587
    username: str = ""
    password: str | None = None  # None = keep existing
    from_address: str
    from_name: str = "NousViz"
    use_tls: bool = True


@router.post(
    "/email",
    operation_id="settings.email.set",
    response_model=EmailSaveResponse,
    summary="Save SMTP config to .env",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
    },
)
async def save_email_settings(
    body: EmailSettings,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """Save SMTP configuration to .env and update live process."""
    admin = get_me(request)
    updates = {
        "SMTP_HOST": body.host,
        "SMTP_PORT": str(body.port),
        "SMTP_USERNAME": body.username,
        "SMTP_FROM_ADDRESS": body.from_address,
        "SMTP_FROM_NAME": body.from_name,
        "SMTP_USE_TLS": "true" if body.use_tls else "false",
    }
    if body.password:
        updates["SMTP_PASSWORD"] = body.password

    try:
        _write_and_reload(updates)
    except Exception as e:
        logger.warning(f"Could not write .env: {e}")
        for k, v in updates.items():
            os.environ[k] = v

    record_activity("settings_update", detail={"setting": "email", "host": body.host}, user_id=admin.get("id"))
    return {"ok": True}


# ── Git / Plugin Registry settings ───────────────────────────────────

@router.get(
    "/git",
    operation_id="settings.git.get",
    response_model=GitSettingsGetResponse,
    summary="Read GitHub-token status (masked)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def get_git_settings(
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    _require_auth(request)
    token = os.environ.get("GITHUB_TOKEN", "")
    return {
        "github_token_set": bool(token),
        "github_token_preview": f"{token[:8]}...{token[-4:]}" if len(token) > 12 else ("••••" if token else ""),
    }


class GitSettings(BaseModel):
    github_token: str | None = None


@router.post(
    "/git",
    operation_id="settings.git.set",
    response_model=GitSettingsSaveResponse,
    summary="Set the GITHUB_TOKEN env var",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
    },
)
async def save_git_settings(
    body: GitSettings,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    admin = get_me(request)
    updates: dict[str, str] = {}
    if body.github_token is not None:
        updates["GITHUB_TOKEN"] = body.github_token.strip()
    if updates:
        try:
            _write_and_reload(updates)
        except Exception as e:
            logger.warning(f"Could not write .env: {e}")
            for k, v in updates.items():
                os.environ[k] = v
    record_activity("settings_update", detail={"setting": "git"}, user_id=admin.get("id"))
    return {"ok": True}


# B252 (v0.9.11.2): the legacy POST /api/settings/auth-mode/upgrade
# endpoint was removed. Multi-user is the only auth model; there is
# nothing to upgrade from.


@router.post(
    "/email/test",
    operation_id="settings.email.test",
    response_model=EmailTestResponse,
    response_model_exclude_none=True,
    summary="Send a test email to the current user (or SMTP_FROM_ADDRESS fallback)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
    },
)
async def test_email(
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """Send a test email to the current authenticated user."""

    # Get current user's email from the session
    token = request.headers.get("X-Session-Token")
    to_email = None
    if token:
        import hashlib as _hl
        token_hash = _hl.sha256(token.encode()).hexdigest()
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.email FROM users u
                JOIN user_sessions s ON s.user_id = u.id
                WHERE s.token_hash = %s AND s.expires_at > now()
            """, (token_hash,))
            row = cur.fetchone()
            if row:
                to_email = row[0]

    if not to_email:
        to_email = os.environ.get("SMTP_FROM_ADDRESS", "")

    if not to_email:
        return {"ok": False, "error": "No email address found to send test to."}

    from ..services.email import send_test_email
    ok, err = send_test_email(to_email)
    return {"ok": ok, "error": err or None, "sent_to": to_email if ok else None}


# ── API keys ──────────────────────────────────────────────────────────


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _ensure_api_keys_table():
    """Create the api_keys table if the migration hasn't been run yet."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name        TEXT NOT NULL,
                key_prefix  TEXT NOT NULL,
                key_hash    TEXT NOT NULL UNIQUE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                last_used_at TIMESTAMPTZ,
                revoked_at  TIMESTAMPTZ
            )
        """)


@router.get(
    "/api-keys",
    operation_id="settings.api_keys.list",
    response_model=list[ApiKeyEntry],
    response_model_exclude_none=True,
    summary="List active API keys (no raw keys, ever)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def list_api_keys(
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    """List all active API keys (prefix + metadata only — never the raw key)."""
    _require_auth(request)
    _ensure_api_keys_table()
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, key_prefix, created_at, last_used_at
            FROM api_keys
            WHERE revoked_at IS NULL
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
    return [
        {
            "id": str(r[0]),
            "name": r[1],
            "key_prefix": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
            "last_used_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


class CreateKeyRequest(BaseModel):
    name: str


@router.post(
    "/api-keys",
    operation_id="settings.api_keys.create",
    response_model=ApiKeySettingsCreateResponse,
    response_model_exclude_none=True,
    summary="Generate a new API key (raw key returned exactly once)",
    responses={
        400: {"model": ErrorDetail, "description": "Name required."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
    },
)
async def create_api_key(
    body: CreateKeyRequest,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """Generate a new API key. The raw key is returned once and never stored."""
    admin = get_me(request)
    _ensure_api_keys_table()
    if not body.name.strip():
        raise HTTPException(400, "Name is required")

    raw = f"nv_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]  # "nv_" + 7 chars
    hashed = _hash_key(raw)

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO api_keys (name, key_prefix, key_hash) VALUES (%s, %s, %s) RETURNING id, created_at",
            (body.name.strip(), prefix, hashed),
        )
        row = cur.fetchone()

    record_activity("api_key_create", detail={"name": body.name.strip()}, user_id=admin.get("id"))
    return {
        "id": str(row[0]),
        "name": body.name.strip(),
        "key_prefix": prefix,
        "key": raw,
        "created_at": row[1].isoformat() if row[1] else None,
        "message": "Copy this key now — it won't be shown again.",
    }


@router.delete(
    "/api-keys/{key_id}",
    operation_id="settings.api_keys.revoke",
    response_model=ApiKeySettingsRevokeResponse,
    summary="Revoke an API key",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
        404: {"model": ErrorDetail, "description": "Key not found or already revoked."},
    },
)
async def revoke_api_key(
    key_id: str,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """Revoke an API key by ID."""
    admin = get_me(request)
    _ensure_api_keys_table()
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE api_keys SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL RETURNING id",
            (key_id,),
        )
        if not cur.fetchone():
            raise HTTPException(404, "Key not found or already revoked")
    record_activity("api_key_revoke", detail={"key_id": key_id}, user_id=admin.get("id"))
    return {"revoked": True}


# ── Deploy keys (SSH) ────────────────────────────────────────────────

@router.get(
    "/deploy-keys",
    operation_id="settings.deploy_keys.list",
    response_model=DeployKeysListResponse,
    response_model_exclude_none=True,
    summary="List registered SSH deploy keys",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def list_deploy_keys(
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    """List registered deploy keys.

    B206 (v0.9.6): response includes ``created_by`` (joined to ``users``)
    and ``repo_url``. Rows whose creator was deleted render with
    ``created_by=None`` rather than vanishing — the key still exists and
    must remain manageable.
    """
    _require_auth(request)
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    dk.id, dk.name, dk.host, dk.repo_url, dk.public_key,
                    dk.fingerprint, dk.created_at,
                    u.id   AS creator_id,
                    u.name AS creator_name,
                    u.email AS creator_email
                FROM deploy_keys dk
                LEFT JOIN users u ON u.id = dk.created_by
                ORDER BY dk.host ASC, dk.created_at DESC
                """
            )
            keys = []
            for row in cur.fetchall():
                (
                    id_, name, host, repo_url, public_key, fingerprint,
                    created_at, creator_id, creator_name, creator_email,
                ) = row
                keys.append({
                    "id": str(id_),
                    "name": name,
                    "host": host,
                    "repo_url": repo_url,
                    "public_key": public_key,
                    "fingerprint": fingerprint,
                    "created_at": (
                        created_at.isoformat()
                        if created_at and hasattr(created_at, "isoformat")
                        else created_at
                    ),
                    "created_by": (
                        {
                            "id": str(creator_id),
                            "name": creator_name,
                            "email": creator_email,
                        }
                        if creator_id is not None
                        else None
                    ),
                })
        return {"keys": keys}
    except Exception:
        return {"keys": []}


class DeployKeyCreate(BaseModel):
    name: str
    host: str = "github.com"
    repo_url: str | None = None


@router.post(
    "/deploy-keys",
    operation_id="settings.deploy_keys.create",
    response_model=DeployKeyCreateResponse,
    summary="Generate a new ed25519 SSH deploy key",
    responses={
        400: {"model": ErrorDetail, "description": "Name is required."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
        500: {"model": ErrorDetail, "description": "ssh-keygen failed or NOUSVIZ_ENCRYPTION_KEY is not set."},
    },
)
async def create_deploy_key(
    body: DeployKeyCreate,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    admin = get_me(request)
    import subprocess
    import tempfile
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")

    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, "id_ed25519")
        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-C", f"nousviz-deploy-{name}", "-f", key_path, "-N", ""],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise HTTPException(500, "Failed to generate SSH key")

        private_key = open(key_path).read()
        public_key = open(f"{key_path}.pub").read().strip()

        # Get fingerprint
        fp_result = subprocess.run(["ssh-keygen", "-lf", f"{key_path}.pub"], capture_output=True, text=True)
        fingerprint = fp_result.stdout.strip().split()[1] if fp_result.returncode == 0 else ""

    # Encrypt private key
    from cryptography.fernet import Fernet
    import base64
    enc_key = os.environ.get("NOUSVIZ_ENCRYPTION_KEY", "")
    if not enc_key:
        raise HTTPException(500, "NOUSVIZ_ENCRYPTION_KEY not set — cannot encrypt deploy key")
    fernet = Fernet(base64.urlsafe_b64encode(bytes.fromhex(enc_key)[:32]))
    encrypted = fernet.encrypt(private_key.encode()).decode()

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO deploy_keys (name, host, repo_url, public_key, private_key_encrypted, fingerprint, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (name, body.host, body.repo_url, public_key, encrypted, fingerprint, admin.get("id")),
        )
        key_id = cur.fetchone()[0]

    return {"id": str(key_id), "name": name, "host": body.host, "public_key": public_key, "fingerprint": fingerprint}


@router.get(
    "/deploy-keys/check",
    operation_id="settings.deploy_keys.check",
    response_model=DeployKeyCheckResponse,
    response_model_exclude_none=True,
    summary="Check whether a deploy key exists for a given repo URL",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.read permission."},
    },
)
async def check_deploy_key(
    repo_url: str,
    request: Request,
    _: None = Depends(requires("settings.read")),
):
    """Check if a deploy key exists for the given repo URL.

    B204: only exact repo_url matches return has_key=True. The previous
    host fallback returned a green indicator even when the actual key
    couldn't authenticate against this URL — the operator was misled
    into thinking install would succeed.
    """
    _require_auth(request)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM deploy_keys WHERE repo_url = %s", (repo_url,))
        row = cur.fetchone()
        if row:
            return {"has_key": True, "key_name": row[1], "match": "repo"}
    return {"has_key": False}


@router.delete(
    "/deploy-keys/{key_id}",
    operation_id="settings.deploy_keys.delete",
    response_model=DeployKeyDeleteResponse,
    summary="Delete a deploy key (writes an audit row)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
        404: {"model": ErrorDetail, "description": "Key not found."},
    },
)
async def delete_deploy_key(
    key_id: str,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    """Delete a deploy key.

    B206 (v0.9.6): writes an ``app_logs`` entry at source ``deploy_keys``
    so operators can see who deleted what in /system/logs.
    """
    admin = get_me(request)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # Fetch identifying fields BEFORE deleting so they're available
        # for the audit entry. RETURNING in the DELETE would also work but
        # this keeps the audit-log call out of the transaction's hot path.
        cur.execute(
            "SELECT name, host, repo_url FROM deploy_keys WHERE id = %s",
            (key_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Key not found")
        key_name, key_host, key_repo_url = row

        cur.execute("DELETE FROM deploy_keys WHERE id = %s", (key_id,))
        conn.commit()

    # Audit. Failure here must not block the delete (which already committed).
    try:
        from ..log_events import log_job_event
        log_job_event(
            level="info",
            source="deploy_keys",
            message=(
                f"Deploy key '{key_name}' deleted by "
                f"{admin.get('email') or admin.get('id') or 'unknown'}"
            ),
            detail={
                "action": "deploy_key_deleted",
                "key_id": str(key_id),
                "key_name": key_name,
                "key_host": key_host,
                "key_repo_url": key_repo_url,
                "actor_email": admin.get("email"),
            },
            actor_user_id=str(admin.get("id")) if admin.get("id") else None,
        )
    except Exception:
        # log_job_event already swallows DB errors; this catch is defensive
        # against the import failing.
        pass

    return {"deleted": True}


@router.post(
    "/deploy-keys/{key_id}/test",
    operation_id="settings.deploy_keys.test",
    response_model=DeployKeyTestResponse,
    summary="SSH-auth probe a deploy key against its host",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the settings.write permission."},
        404: {"model": ErrorDetail, "description": "Key not found."},
    },
)
async def test_deploy_key(
    key_id: str,
    request: Request,
    _: None = Depends(requires("settings.write")),
):
    import subprocess
    import tempfile
    from cryptography.fernet import Fernet
    import base64

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT host, private_key_encrypted FROM deploy_keys WHERE id = %s", (key_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Key not found")

    host, encrypted = row
    enc_key = os.environ.get("NOUSVIZ_ENCRYPTION_KEY", "")
    fernet = Fernet(base64.urlsafe_b64encode(bytes.fromhex(enc_key)[:32]))
    private_key = fernet.decrypt(encrypted.encode()).decode()

    with tempfile.NamedTemporaryFile(mode="w", suffix="_key", delete=False) as f:
        f.write(private_key)
        key_path = f.name
    os.chmod(key_path, 0o600)

    try:
        result = subprocess.run(
            ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", f"git@{host}", "-T"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stderr.strip()
        ok = "successfully authenticated" in output.lower() or result.returncode == 1
        return {"ok": ok, "detail": output[:200]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": f"SSH connection to {host} timed out"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
    finally:
        os.unlink(key_path)
