"""
/api/health — Health check endpoints
"""

import logging
import os
from pathlib import Path
from datetime import datetime, timezone

_STARTUP_TIME = datetime.now(timezone.utc).isoformat()

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn
from ..models import ErrorDetail, RBACErrorDetail
from ..models.health import (
    ConnectionHealthResponse,
    HealthConfigResponse,
    HealthLogResponse,
    HealthRecordResponse,
    HealthResponse,
    SslSetupResponse,
)

logger = logging.getLogger("nousviz.api.health")

REPO_ROOT    = Path(__file__).resolve().parents[4]
VERSION_FILE = REPO_ROOT / "VERSION"
APP_VERSION  = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0.0.0"
MIGRATIONS_DIR = REPO_ROOT / "storage" / "postgres" / "migrations"
PLUGINS_INSTALLED = REPO_ROOT / "plugins" / "installed"
PLUGINS_COMMUNITY = REPO_ROOT / "plugins" / "community"

router = APIRouter(tags=["health"])

# B228: register the non-public health routes. /health and /health/config
# are in PUBLIC_ROUTES (load balancer needs them).
from ..rbac import requires, register_route
register_route("GET", "/api/health/connections", "system.logs")
register_route("GET", "/api/health/log", "system.logs")
register_route("POST", "/api/health/record", "system.logs")
register_route("POST", "/api/admin/ssl/setup", "system.admin")

# ── SSL status (cached) ──────────────────────────────────────────────

# Cert-expiry cache keyed on (cert_path, cert_mtime). The env-var read is not
# cached — that's what created B190's multi-worker drift. Expiry is safe to
# cache because cert files only change when certbot writes a new one, which
# bumps the mtime.
_cert_expiry_cache: dict[tuple[str, float], str] = {}


def _read_cert_expiry(cert_path: str) -> str | None:
    """Return the cert's expiry string, cached by (path, mtime) so repeated calls don't re-shell openssl."""
    try:
        mtime = os.path.getmtime(cert_path)
    except OSError:
        return None
    key = (cert_path, mtime)
    if key in _cert_expiry_cache:
        return _cert_expiry_cache[key]
    try:
        import subprocess
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        # Output: notAfter=Jul 13 00:00:00 2026 GMT
        expiry_str = result.stdout.strip().split("=", 1)[-1]
    except Exception:
        return None
    _cert_expiry_cache[key] = expiry_str
    return expiry_str


def _get_ssl_status() -> dict | None:
    """
    Read SSL config from env vars on every call (B190 — no cache on env reads).

    Returns None if SSL is not configured.
    Cert expiry is cached by (path, mtime) so the openssl subprocess only
    runs once per cert file — see `_read_cert_expiry`.
    """
    ssl_type = os.environ.get("NOUSVIZ_SSL", "").strip()
    domain = os.environ.get("NOUSVIZ_DOMAIN", "").strip()

    if not ssl_type:
        return None

    info: dict = {
        "enabled": True,
        "type": ssl_type,
    }
    if domain:
        info["domain"] = domain

    if ssl_type == "letsencrypt" and domain:
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        expiry = _read_cert_expiry(cert_path)
        if expiry:
            info["expires"] = expiry

    return info


@router.get(
    "/health",
    operation_id="health.check",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    summary="Overall instance health",
)
async def health():
    """Overall health check for the NousViz instance.

    Public endpoint (no auth required) — this is the same shape used by
    load balancers and the operator dashboard. The response is intentionally
    nested: `services.postgres` reports DB connectivity and critical-table
    presence, `runtime.sdk` reports whether `nousviz_sdk` imported, and
    `stats` carries operator-dashboard counts.

    Top-level `status` flips to `degraded` when Postgres reports degraded,
    the SDK is unavailable, or critical tables are missing. Frontend
    `evaluateChecks` drives banner display from this shape — additive
    changes here are safe; renaming or removing fields will break the UI.
    """
    # ── Postgres ──────────────────────────────────────────────────────
    pg_health: dict = {"status": "disconnected"}
    pg_alerts = 0
    pg_fusions = 0
    pg_annotations = 0
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # Core connection check + table count
            cur.execute(
                "SELECT version(), count(*) "
                "FROM information_schema.tables WHERE table_schema = 'public'"
            )
            pg_version, pg_tables = cur.fetchone()
            pg_health = {
                "status": "connected",
                "version": pg_version.split(" on ")[0] if pg_version else None,
                "tables": pg_tables,
            }

            # B128 (v0.8.6.3): critical-tables check. These tables are
            # required for platform functions that operators expect to
            # Just Work (secret-credential storage, job runs, logs, users).
            # Missing any of them = schema drift; report unhealthy so it
            # shows red in the UI instead of green with a 500 hiding underneath.
            _CRITICAL_TABLES = [
                "credentials",         # encrypted plugin credentials (v0.8.6 + B128)
                "connections",         # credential parent rows
                "users",               # auth
                "job_runs",            # async jobs (v0.8.2)
                "app_logs",            # operator-visible logs (v0.8.4)
                "schema_migrations",   # migration tracker itself
            ]
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = ANY(%s)
                """,
                (_CRITICAL_TABLES,),
            )
            present = {row[0] for row in cur.fetchall()}
            missing = [t for t in _CRITICAL_TABLES if t not in present]
            pg_health["critical_tables_present"] = len(present)
            pg_health["critical_tables_total"] = len(_CRITICAL_TABLES)
            if missing:
                pg_health["status"] = "degraded"
                pg_health["missing_critical_tables"] = missing
                pg_health["drift_hint"] = (
                    "Core migrations have drifted from the tree. "
                    "Re-run scripts/deploy-local.sh to apply pending core migrations, "
                    "or inspect storage/postgres/migrations/ and schema_migrations table."
                )

            # Optional stat queries — each independent, fail silently
            def _count(sql: str) -> int:
                try:
                    cur.execute(sql)
                    return cur.fetchone()[0] or 0
                except Exception:
                    conn.rollback()
                    return 0

            pg_alerts     = _count("SELECT count(*) FROM alert_triggers")
            pg_fusions    = _count("SELECT count(*) FROM fusions")
            pg_annotations = _count("SELECT count(*) FROM annotations WHERE archived = false")

            # Count plugin tables vs core tables
            pg_plugin_tables = 0
            try:
                import yaml as _yaml
                for plugin_dir in [PLUGINS_INSTALLED, PLUGINS_COMMUNITY]:
                    if not plugin_dir.exists():
                        continue
                    for pdir in plugin_dir.iterdir():
                        manifest = pdir / "plugin.yaml"
                        if manifest.exists():
                            m = _yaml.safe_load(manifest.read_text())
                            for db in (m.get("databases") or {}).values():
                                pg_plugin_tables += len(db.get("tables") or [])
            except Exception:
                pass

    except Exception:
        pass

    # ── Active shares ────────────────────────────────────────────────
    active_shares = 0
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM shared_links WHERE revoked = false AND expires_at > now()")
            active_shares = cur.fetchone()[0] or 0
    except Exception:
        pass

    # ── Installed plugins ─────────────────────────────────────────────
    installed_count = sum(
        1 for d in [PLUGINS_INSTALLED, PLUGINS_COMMUNITY]
        if d.exists()
        for _ in d.iterdir()
        if _.is_dir()
    )

    # ── Migrations ───────────────────────────────────────────────────
    migration_count = len(list(MIGRATIONS_DIR.glob("*.sql"))) if MIGRATIONS_DIR.exists() else 0

    services: dict = {"postgres": pg_health}

    # P205 (v0.9.0) revisited in v0.9.2 (B137): SDK availability is an
    # internal runtime precondition — operators don't deploy or operate
    # the SDK directly, plugin authors do. Don't clutter the operator-
    # facing services dashboard with it. Surface it under a separate
    # `runtime` block that admin tooling and plugin debuggers can read,
    # and keep the overall status flip to "degraded" when SDK is missing
    # (because plugins won't work — operators DO care about that signal).
    runtime: dict = {}
    try:
        from ..main import SDK_AVAILABLE, SDK_VERSION, SDK_IMPORT_ERROR
        runtime["sdk"] = {
            "status": "available" if SDK_AVAILABLE else "unavailable",
            "version": SDK_VERSION,
        }
        if not SDK_AVAILABLE:
            runtime["sdk"]["import_error"] = (SDK_IMPORT_ERROR or "")[:200]
    except Exception:
        pass

    # ── Utility plugin services ──────────────────────────────────────
    # Check health of installed utility plugins that declare a health_check hook
    try:
        import subprocess as _sp
        import json as _json
        for util_dir in (PLUGINS_INSTALLED,):
            if not util_dir.exists():
                continue
            for d in util_dir.iterdir():
                if not d.is_dir():
                    continue
                manifest_path = d / "plugin.yaml"
                if not manifest_path.exists():
                    continue
                try:
                    import yaml as _yaml
                    data = _yaml.safe_load(manifest_path.read_text())
                    if data.get("type") != "utility":
                        continue
                    health_hook = data.get("health_check")
                    if not health_hook:
                        continue
                    hook_path = d / health_hook
                    if not hook_path.exists():
                        continue
                    result = _sp.run(
                        ["bash", str(hook_path)],
                        capture_output=True, text=True, timeout=5,
                        env=os.environ.copy(),
                    )
                    if result.stdout.strip():
                        h = _json.loads(result.stdout.strip())
                        if h.get("ok"):
                            status = "connected"
                        elif "not configured" in (h.get("error") or "").lower():
                            status = "not_configured"
                        else:
                            status = "disconnected"
                        services[d.name] = {
                            "status": status,
                            "version": h.get("version"),
                        }
                except Exception:
                    pass
    except Exception:
        pass

    # ── SSL status ────────────────────────────────────────────────────
    ssl_info = _get_ssl_status()

    # P205: overall health also degrades if SDK unavailable (plugins won't
    # load) or if critical tables are missing (B128). Both are "operational
    # degradation" — core DB is reachable so pg_health says connected, but
    # the plugin system is broken until fixed.
    overall_status = "healthy" if pg_health["status"] == "connected" else "degraded"
    sdk_block = runtime.get("sdk", {})
    if isinstance(sdk_block, dict) and sdk_block.get("status") == "unavailable":
        overall_status = "degraded"
    if isinstance(pg_health, dict) and pg_health.get("status") == "degraded":
        overall_status = "degraded"

    result = {
        "status": overall_status,
        "version": APP_VERSION,
        "startup_time": _STARTUP_TIME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "runtime": runtime,
        "stats": {
            "active_alerts": pg_alerts,
            "fusions": pg_fusions,
            "annotations": pg_annotations,
            "installed_plugins": installed_count,
            "plugin_tables": pg_plugin_tables,
            "active_shares": active_shares,
        },
    }
    if ssl_info:
        result["ssl"] = ssl_info
    return result


# ── Update check (cached, max once per hour) ─────────────────────────

_update_cache: dict = {"result": {}, "checked_at": 0}

def _check_update_cached() -> dict:
    import time as _t
    import urllib.request
    import json as _j
    now = _t.time()
    if now - _update_cache["checked_at"] < 3600:
        return _update_cache["result"]

    try:
        current = (Path(__file__).resolve().parents[4] / "VERSION").read_text().strip()
        req = urllib.request.Request(
            "https://api.github.com/repos/nousviz/nousviz-app/tags?per_page=1",
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        res = urllib.request.urlopen(req, timeout=5)
        tags = _j.loads(res.read())
        latest = tags[0]["name"] if tags else None
        if not latest:
            result = {"available": False, "current": current}
        else:
            current_clean = current.replace("-dev", "")
            latest_clean = latest.lstrip("v")
            result = {
                "available": latest_clean != current_clean,
                "current": current,
                "latest": latest,
            }
    except Exception:
        result = {"available": False, "current": current if "current" in dir() else "unknown"}

    _update_cache["result"] = result
    _update_cache["checked_at"] = now
    return result


@router.get(
    "/health/config",
    operation_id="health.config",
    response_model=HealthConfigResponse,
    response_model_exclude_none=True,
    summary="Boolean status of security-sensitive config",
)
async def config_status():
    """Return boolean status of security-sensitive config values.

    Public endpoint (no auth required) — this is what the dashboard
    config-banner reads to decide whether to nudge the operator about
    missing encryption keys, missing superadmin user, SMTP config, etc.

    **Never exposes actual values** — only whether they are set and
    non-default. The `update_*` fields surface a once-per-hour-cached
    GitHub release check so operators can see the "update available"
    banner without polling the GitHub API on every request.
    """
    encryption_key = os.environ.get("NOUSVIZ_ENCRYPTION_KEY", "").strip()
    auth_required  = os.environ.get("AUTH_REQUIRED", "false").strip().lower() == "true"
    smtp_host = os.environ.get("SMTP_HOST", "").strip()

    # B252 (v0.9.11.2): the wizard's "auth configured" gate now reads the
    # users table, not env vars. A real superadmin row is the single
    # source of truth that someone has been through the multi-user setup.
    superadmin_exists = False
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE role = 'superadmin' AND is_active = true LIMIT 1")
            superadmin_exists = cur.fetchone() is not None
    except Exception:
        pass

    update = _check_update_cached()

    return {
        "encryption_key_set": bool(encryption_key),
        "auth_required": auth_required,
        "superadmin_exists": superadmin_exists,
        # S108: postgres_password_is_default is now always False because the
        # app refuses to start without POSTGRES_PASSWORD set. Field kept for
        # backwards-compatible response shape; frontends treating it as
        # always-False are now correct.
        "postgres_password_is_default": False,
        "smtp_configured": bool(smtp_host),
        "update_available": update.get("available", False),
        "update_latest": update.get("latest"),
        "update_current": update.get("current"),
    }


@router.get(
    "/health/connections",
    operation_id="health.connections",
    response_model=ConnectionHealthResponse,
    summary="Plugin connection health issues",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.logs permission."},
    },
)
async def connection_health(_: None = Depends(requires("system.logs"))):
    """Banner-shaped list of plugin connection-health issues.

    Each entry carries a plugin id, severity, message, and optional
    structured detail — the UI renders each as a banner on the home
    dashboard. An empty list means all installed plugins report healthy
    connections.

    Plugins will register their own health checks via `plugin_registry`
    in a future release; the current implementation always returns no
    issues.
    """
    issues = []
    return {"issues": issues}


@router.get(
    "/health/log",
    operation_id="health.log",
    response_model=HealthLogResponse,
    response_model_exclude_none=True,
    summary="Recent health-check snapshots from health_log",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.logs permission."},
    },
)
async def health_log(
    days: int = 7,
    limit: int = 200,
    _: None = Depends(requires("system.logs")),
):
    """Return health check history from the health_log table."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, level, checks, postgres_ok, tables, version, created_at FROM health_log WHERE created_at >= %s ORDER BY created_at DESC LIMIT %s",
                (cutoff, limit),
            )
            from ..db import rows_as_dicts
            rows = rows_as_dicts(cur)
        for r in rows:
            if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
                r["created_at"] = r["created_at"].isoformat()
        return {"log": rows, "count": len(rows)}
    except Exception:
        return {"log": [], "count": 0}


from ..rate_limit import RateLimiter
_health_record_limiter = RateLimiter(max_attempts=10, window_sec=60, max_keys=1000)


def _check_record_health_rate(ip: str) -> bool:
    """Return True if the caller IP has exceeded the health-record rate limit.
    Localhost is exempt — PM2 cron hits the endpoint every 5 min."""
    if ip in ("127.0.0.1", "::1", "localhost"):
        return False
    return _health_record_limiter.is_limited(ip)


@router.post(
    "/health/record",
    operation_id="health.record",
    response_model=HealthRecordResponse,
    summary="Run a health check + persist to health_log (PM2 cron + manual refresh)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": ErrorDetail, "description": "Health record requires localhost or authenticated access."},
        429: {"model": ErrorDetail, "description": "Rate-limited (10/min per IP, localhost exempt)."},
        500: {"model": ErrorDetail, "description": "Health record failed."},
    },
)
async def record_health(
    request: Request,
    _: None = Depends(requires("system.logs")),
):
    """
    Run a health check and store the result in health_log.

    Accepted from:
    - localhost (PM2 cron on the same box) — unlimited rate
    - authenticated requests (session token, API key, or Cloudflare) — lets
      an operator force a fresh check from the browser via the Refresh button
      on /health-overview. Rate-limited per-IP.
    """
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    direct_ip = request.client.host if request.client else "unknown"
    is_localhost = direct_ip in ("127.0.0.1", "::1", "localhost") and not request.headers.get("X-Forwarded-For")
    is_authenticated = bool(getattr(request.state, "user_identity", None))
    if not (is_localhost or is_authenticated):
        raise HTTPException(403, "Health record requires localhost or authenticated access")
    if not is_localhost and _check_record_health_rate(client_ip):
        raise HTTPException(429, "Too many manual health checks. Try again in a minute.")
    import json
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # Quick Postgres health check
            cur.execute("SELECT count(*) FROM pg_stat_user_tables")
            table_count = cur.fetchone()[0]

            checks = []
            level = "healthy"

            # Postgres check
            checks.append({"id": "postgres", "status": "pass", "label": "PostgreSQL", "detail": f"{table_count} tables"})

            # SSL check
            ssl = _get_ssl_status()
            if ssl:
                checks.append({"id": "https", "status": "pass", "label": "HTTPS", "detail": ssl.get("type", "enabled")})
            else:
                checks.append({"id": "https", "status": "warn", "label": "HTTPS", "detail": "Not configured"})
                level = "warning"

            # Auth check
            auth_required = os.environ.get("AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
            superadmin_exists = False
            try:
                with get_pg_conn() as inner_conn:
                    inner_cur = inner_conn.cursor()
                    inner_cur.execute("SELECT 1 FROM users WHERE role = 'superadmin' AND is_active = true LIMIT 1")
                    superadmin_exists = inner_cur.fetchone() is not None
            except Exception:
                pass
            if auth_required and superadmin_exists:
                checks.append({"id": "auth", "status": "pass", "label": "Authentication", "detail": "Enabled"})
            else:
                checks.append({
                    "id": "auth",
                    "status": "warn",
                    "label": "Authentication",
                    "detail": "Disabled" if not auth_required else "No superadmin user",
                })
                if not auth_required:
                    level = "warning"

            # Encryption key
            enc_set = bool(os.environ.get("NOUSVIZ_ENCRYPTION_KEY"))
            if enc_set:
                checks.append({"id": "encryption", "status": "pass", "label": "Encryption key", "detail": "Set"})
            else:
                checks.append({"id": "encryption", "status": "warn", "label": "Encryption key", "detail": "Not set"})
                level = "warning"

            # SMTP — not a warning-level issue (platform works without it), but surfaces in health
            smtp_set = bool(os.environ.get("SMTP_HOST", "").strip())
            checks.append({
                "id": "smtp",
                "status": "pass" if smtp_set else "warn",
                "label": "Email (SMTP)",
                "detail": "Configured" if smtp_set else "Not configured",
            })
            if not smtp_set:
                level = "warning"

            # Utility plugin checks (ClickHouse, MySQL, etc.)
            try:
                import subprocess as _sp
                for util_dir in (PLUGINS_INSTALLED,):
                    if not util_dir.exists():
                        continue
                    for d in util_dir.iterdir():
                        if not d.is_dir():
                            continue
                        mp = d / "plugin.yaml"
                        if not mp.exists():
                            continue
                        try:
                            import yaml as _yaml
                            mdata = _yaml.safe_load(mp.read_text())
                            if mdata.get("type") != "utility":
                                continue
                            hook = mdata.get("health_check")
                            if not hook:
                                continue
                            hook_path = d / hook
                            if not hook_path.exists():
                                continue
                            result = _sp.run(["bash", str(hook_path)], capture_output=True, text=True, timeout=5, env=os.environ.copy())
                            display = mdata.get("display_name", d.name).title()
                            detail = "Connected"
                            try:
                                hdata = json.loads(result.stdout.strip())
                                if hdata.get("version"):
                                    detail = f"Connected · {hdata['version']}"
                            except Exception:
                                pass
                            if result.returncode == 0:
                                checks.append({"id": d.name, "status": "pass", "label": display, "detail": detail})
                            else:
                                err_detail = "Not configured"
                                try:
                                    hdata = json.loads(result.stdout.strip())
                                    err_detail = hdata.get("error", "Disconnected")
                                except Exception:
                                    pass
                                # "Not configured" is info-level, not warning — don't degrade overall health
                                is_not_configured = "not configured" in err_detail.lower()
                                checks.append({"id": d.name, "status": "info" if is_not_configured else "warn", "label": display, "detail": err_detail})
                                if not is_not_configured:
                                    level = "warning"
                        except Exception:
                            pass
            except Exception:
                pass

            from pathlib import Path as _Path
            version = (_Path(__file__).resolve().parents[4] / "VERSION").read_text().strip()

            cur.execute(
                "INSERT INTO health_log (level, checks, postgres_ok, tables, version) VALUES (%s, %s, %s, %s, %s)",
                (level, json.dumps(checks), True, table_count, version),
            )

            # Cleanup: keep only 30 days
            from datetime import timedelta
            cur.execute("DELETE FROM health_log WHERE created_at < %s", (datetime.now(timezone.utc) - timedelta(days=30),))

        # Record job run + retention (separate transaction so it can't roll back health_log)
        try:
            with get_pg_conn() as conn2:
                cur2 = conn2.cursor()
                cur2.execute("""
                    INSERT INTO job_runs (job_id, started_at, completed_at, status, source, details)
                    VALUES ('health-monitor', now(), now(), 'success', 'health_monitor', %s)
                """, (json.dumps({"level": level, "checks": len(checks)}),))
                cur2.execute("DELETE FROM job_runs WHERE started_at < %s", (datetime.now(timezone.utc) - timedelta(days=90),))
        except Exception as job_err:
            logger.warning(f"Job run recording failed: {job_err}")

        # Health alerts — notify on state transitions
        if is_localhost:
            _check_health_alerts(checks, level)

        return {"status": "recorded", "level": level, "checks": len(checks)}
    except Exception as e:
        logger.error(f"Health record failed: {e}")
        raise HTTPException(500, f"Health record failed: {e}")


# ── Health alert notifications ────────────────────────────────────────

_prev_health_state: dict[str, str] = {}

def _check_health_alerts(checks: list[dict], level: str) -> None:
    """Send email when a health check transitions from pass to fail/warn."""
    try:
        from ..services.email import _send, is_configured
        if not is_configured():
            return

        newly_failed = []
        for check in checks:
            cid = check["id"]
            prev = _prev_health_state.get(cid, "pass")
            curr = check["status"]
            _prev_health_state[cid] = curr

            if prev == "pass" and curr in ("warn", "fail"):
                newly_failed.append(check)
            elif prev in ("warn", "fail") and curr == "pass":
                logger.info(f"Health alert recovered: {check['label']}")

        if not newly_failed:
            return

        to = os.environ.get("SMTP_FROM_ADDRESS", "")
        if not to:
            return

        labels = ", ".join(c["label"] for c in newly_failed)
        subject = f"[NousViz] Health alert: {labels}"
        details = "\n".join(f"  {c['label']}: {c['detail']} ({c['status']})" for c in newly_failed)
        plain = f"NousViz health check detected issues:\n\n{details}\n\nCheck your instance at /health-overview"
        html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#16161d;border-radius:12px;">
  <h2 style="color:#f0f0f5;font-size:18px;margin:0 0 12px;">Health Alert</h2>
  <p style="color:#999;font-size:13px;margin:0 0 16px;">The following checks are failing:</p>
  {"".join(f'<p style="color:#f59e0b;font-size:13px;margin:4px 0;"><strong>{c["label"]}</strong>: {c["detail"]}</p>' for c in newly_failed)}
  <p style="color:#555;font-size:11px;margin:16px 0 0;">Sent by NousViz &middot; Self-hosted data intelligence</p>
</div>"""
        ok, err = _send(to, subject, html, plain)
        if ok:
            logger.info(f"Health alert email sent: {labels}")
        else:
            logger.error(f"Health alert email failed: {err}")
    except Exception as e:
        logger.error(f"Health alert check error: {e}")


# ── SSL setup from UI ────────────────────────────────────────────────

class SslSetupRequest(BaseModel):
    mode: str = "letsencrypt"
    domain: str | None = None
    email: str | None = None


@router.post(
    "/admin/ssl/setup",
    operation_id="admin.ssl.setup",
    response_model=SslSetupResponse,
    response_model_exclude_none=True,
    summary="Provision Let's Encrypt SSL via the ssl-setup.sh script",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid mode/domain."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.admin permission."},
        500: {"model": ErrorDetail, "description": "ssl-setup.sh missing or invocation failed."},
    },
)
async def setup_ssl(
    req: SslSetupRequest,
    request: Request,
    _: None = Depends(requires("system.admin")),
):
    """
    Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
    Only Let's Encrypt is supported (requires a domain).
    """
    session_token = request.headers.get("x-session-token")
    api_key = request.headers.get("x-api-key")
    if not session_token and not api_key:
        raise HTTPException(401, "Authentication required")

    if req.mode != "letsencrypt":
        raise HTTPException(400, "Only Let's Encrypt is supported")

    if not req.domain:
        raise HTTPException(400, "domain is required for Let's Encrypt")

    import re as _re
    if not _re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]$', req.domain):
        raise HTTPException(400, "Invalid domain format")

    script = REPO_ROOT / "scripts" / "ssl-setup.sh"
    if not script.exists():
        raise HTTPException(500, "ssl-setup.sh not found")

    import subprocess
    cmd = ["bash", str(script), req.domain]
    if req.email:
        cmd.extend(["--email", req.email])

    try:
        # stdin=DEVNULL so the script can never block on a `read` prompt — the script
        # honours $NOUSVIZ_NON_INTERACTIVE=1 and will exit with a clear error instead.
        # 300s covers the worst case: fresh Ubuntu + apt-get update + certbot install + HTTP-01 challenge.
        #
        # PATH: PM2 runs the API with a minimal PATH missing /usr/sbin where nginx and other
        # admin binaries live. certbot --nginx calls `nginx -T` internally and fails if the
        # binary isn't in PATH. Prepend the admin dirs explicitly.
        # DEBIAN_FRONTEND=noninteractive silences debconf warnings when apt-get installs
        # certbot on a first run without a TTY.
        existing_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        env = {
            **os.environ,
            "NOUSVIZ_NON_INTERACTIVE": "1",
            "PATH": f"/usr/sbin:/sbin:{existing_path}",
            "DEBIAN_FRONTEND": "noninteractive",
        }
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(REPO_ROOT),
            stdin=subprocess.DEVNULL,
            env=env,
        )

        # ssl-setup.sh writes NOUSVIZ_SSL / NOUSVIZ_DOMAIN to .env on success.
        # Read those values back and hand them to write_and_reload, which:
        #   1) patches os.environ in THIS worker (so the response below reflects
        #      the new SSL state via _get_ssl_status())
        #   2) schedules `pm2 reload api --update-env` in a background thread
        #      so sibling gunicorn workers pick up the new env (B190)
        if result.returncode == 0:
            from .._env import write_and_reload
            ssl_updates: dict[str, str] = {}
            try:
                with open(REPO_ROOT / ".env") as f:
                    for line in f:
                        for key in ("NOUSVIZ_SSL", "NOUSVIZ_DOMAIN"):
                            if line.startswith(f"{key}="):
                                ssl_updates[key] = line.strip().split("=", 1)[1]
            except Exception:
                pass
            if ssl_updates:
                # write_and_reload will re-write the same values to .env — harmless,
                # ensures the current worker's os.environ is in sync even if the
                # script's .env-write raced a concurrent read.
                write_and_reload(ssl_updates)

        # Parse the script's machine-readable classification line if present. Emitted
        # by ssl-setup.sh when DNS doesn't match the server — lets the frontend render
        # scenario-specific guidance (Cloudflare proxy, DNS not propagated, etc.) instead
        # of a generic red error block.
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        reason = None
        for line in combined.splitlines():
            if "NOUSVIZ_CLASSIFICATION:" in line:
                reason = line.split("NOUSVIZ_CLASSIFICATION:", 1)[1].strip()
                break

        if result.returncode == 0:
            return {
                "ok": True,
                "output": result.stdout,
                "ssl": _get_ssl_status(),
            }
        else:
            return {
                "ok": False,
                "reason": reason,
                "error": result.stderr or result.stdout or "SSL setup failed",
            }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "reason": "timeout",
            "error": "SSL setup timed out (300s). Run manually from the server: sudo ./scripts/ssl-setup.sh <domain>",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
