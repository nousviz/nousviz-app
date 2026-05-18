"""
Admin CLI — curated command runner for superadmins.

POST /api/admin/cli { command: "users list" }
Returns { output: "...", ok: true/false }

No arbitrary shell execution. Commands are parsed and dispatched
to Python handlers that query the DB or read config.
"""

import json
import logging
import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..db import get_pg_conn, dict_cursor
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.admin import CliResponse, LogFiltersResponse, LogsListResponse
from .auth import get_me  # P209 (v0.9.11.25): was a dormant F821 since B212 — fixed by ruff gate.

logger = logging.getLogger("nousviz.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])

# B228: register routes in admin.py.
register_route("POST", "/api/admin/cli", "admin.cli")
register_route("GET", "/api/admin/logs", "system.logs")
register_route("GET", "/api/admin/logs/filters", "system.logs")

REPO_ROOT = Path(__file__).resolve().parents[4]


class CliRequest(BaseModel):
    command: str


@router.post(
    "/cli",
    operation_id="admin.cli",
    response_model=CliResponse,
    summary="Run a curated admin CLI command",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the admin.cli permission."},
    },
)
async def run_cli(
    body: CliRequest,
    request: Request,
    _: None = Depends(requires("admin.cli")),
):
    # B212 (v0.9.6.3): capture actor so handlers that write log entries
    # (currently only `plugins sync`) can attribute them to the operator
    # who ran the command. Most handlers absorb the kwarg via **_kwargs.
    admin = get_me(request)
    try:
        parts = shlex.split(body.command.strip())
    except ValueError as e:
        return {"output": f"Parse error: {e}", "ok": False}

    if not parts:
        return {"output": "No command provided. Type 'help' for available commands.", "ok": False}

    cmd = parts[0].lower()
    args = parts[1:]

    handler = COMMANDS.get(cmd)
    if not handler:
        return {"output": f"Unknown command: {cmd}\nType 'help' for available commands.", "ok": False}

    try:
        output = handler(args, actor=admin)
        return {"output": output, "ok": True}
    except Exception as e:
        return {"output": f"Error: {e}", "ok": False}


# ── Command handlers ─────────────────────────────────────────────────

def cmd_help(args: list[str], **_kwargs) -> str:
    return """Available commands:

  users list                     List all users
  users create <email> <role>    Create user with generated password
  users reset-password <email>   Reset password (returns new one)
  users set-role <email> <role>  Change user role
  users deactivate <email>       Disable user account
  users reactivate <email>       Re-enable user account

  health                         Run health check
  version                        Show current version
  config                         Show non-secret configuration
  migrations status              Show migration state
  migrations run                 Run pending migrations

  plugins list                   List installed plugins
  plugins sync <id> [--no-wait]  Trigger plugin sync (waits for completion by default)
  cache clear                    Clear caches

  jobs history [--limit N]       Recent job runs
  logs api [--lines N]           Tail API logs
  logs alerts [--lines N]        Tail alert logs
  env check                      Validate required env vars

  backup run                     Create a database backup
  backup list                    List existing backups
  backup restore <file>          Show restore instructions

  security audit                 Check security configuration
  security rotate-key            Show key rotation instructions

  update check                   Check for updates + show changelog

  clear                          Clear the terminal
  help                           Show this message"""


def cmd_users(args: list[str], **_kwargs) -> str:
    if not args:
        return "Usage: users <list|create|reset-password|set-role|deactivate|reactivate>"

    sub = args[0].lower()

    if sub == "list":
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute("SELECT email, name, role, is_active, last_login, last_seen_at FROM users ORDER BY created_at")
            rows = cur.fetchall()
        if not rows:
            return "No users found."
        lines = [f"{'Email':<30} {'Name':<15} {'Role':<12} {'Active':<8} {'Last Seen'}"]
        lines.append("-" * 90)
        for r in rows:
            seen = ""
            if r["last_seen_at"]:
                seen = r["last_seen_at"].strftime("%Y-%m-%d %H:%M") if hasattr(r["last_seen_at"], "strftime") else str(r["last_seen_at"])[:16]
            lines.append(f"{r['email']:<30} {(r['name'] or '-'):<15} {r['role']:<12} {'yes' if r['is_active'] else 'no':<8} {seen}")
        return "\n".join(lines)

    elif sub == "create":
        if len(args) < 3:
            return "Usage: users create <email> <role>\nRoles: admin, analyst, viewer"
        email, role = args[1], args[2].lower()
        if role not in ("admin", "analyst", "viewer"):
            return f"Invalid role: {role}. Use admin, analyst, or viewer."
        import secrets
        from .auth import _hash_password
        password = secrets.token_urlsafe(12)
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return f"User {email} already exists."
            cur.execute(
                "INSERT INTO users (email, role, password_hash, is_active) VALUES (%s, %s, %s, true)",
                (email, role, _hash_password(password)),
            )
        return f"Created user {email} with role {role}\nTemporary password: {password}\n\nUser should change this after first login."

    elif sub == "reset-password":
        if len(args) < 2:
            return "Usage: users reset-password <email>"
        email = args[1]
        import secrets
        from .auth import _hash_password
        password = secrets.token_urlsafe(12)
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash = %s, updated_at = now() WHERE email = %s RETURNING id", (_hash_password(password), email))
            if not cur.fetchone():
                return f"User {email} not found."
        return f"Password reset for {email}\nNew password: {password}\n\nUser should change this after login."

    elif sub == "set-role":
        if len(args) < 3:
            return "Usage: users set-role <email> <role>"
        email, role = args[1], args[2].lower()
        if role not in ("superadmin", "admin", "analyst", "viewer"):
            return f"Invalid role: {role}."
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET role = %s, updated_at = now() WHERE email = %s RETURNING id", (role, email))
            if not cur.fetchone():
                return f"User {email} not found."
        return f"Set {email} role to {role}."

    elif sub == "deactivate":
        if len(args) < 2:
            return "Usage: users deactivate <email>"
        email = args[1]
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_active = false, updated_at = now() WHERE email = %s RETURNING id", (email,))
            if not cur.fetchone():
                return f"User {email} not found."
        return f"Deactivated {email}."

    elif sub == "reactivate":
        if len(args) < 2:
            return "Usage: users reactivate <email>"
        email = args[1]
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_active = true, updated_at = now() WHERE email = %s RETURNING id", (email,))
            if not cur.fetchone():
                return f"User {email} not found."
        return f"Reactivated {email}."

    return f"Unknown subcommand: {sub}"


def cmd_health(args: list[str], **_kwargs) -> str:
    import urllib.request
    try:
        res = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=5)
        data = json.loads(res.read())
        lines = [f"Status: {data.get('status', 'unknown')}  Version: {data.get('version', '?')}"]
        for svc, info in (data.get("services") or {}).items():
            status = info.get("status", "unknown")
            version = info.get("version", "")
            tables = info.get("tables")
            detail = f" · {version}" if version else ""
            if tables:
                detail += f" · {tables} tables"
            lines.append(f"  {svc}: {status}{detail}")
        return "\n".join(lines)
    except Exception as e:
        return f"Health check failed: {e}"


def cmd_version(args: list[str], **_kwargs) -> str:
    try:
        return (REPO_ROOT / "VERSION").read_text().strip()
    except Exception:
        return "Unknown"


def cmd_config(args: list[str], **_kwargs) -> str:
    SAFE_KEYS = [
        "AUTH_REQUIRED", "MULTI_USER_ACCOUNTS", "POSTGRES_HOST", "POSTGRES_PORT",
        "POSTGRES_DB", "POSTGRES_USER", "SMTP_HOST", "SMTP_PORT", "SMTP_FROM_ADDRESS",
        "SMTP_FROM_NAME", "SMTP_USE_TLS",
    ]
    lines = []
    for k in SAFE_KEYS:
        v = os.environ.get(k, "(not set)")
        lines.append(f"  {k}={v}")
    return "Configuration (secrets hidden):\n" + "\n".join(lines)


def cmd_migrations(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "status"
    migrations_dir = REPO_ROOT / "storage" / "postgres" / "migrations"

    if sub == "status":
        files = sorted(migrations_dir.glob("*.sql"))
        up_files = [f for f in files if not f.name.endswith("_down.sql")]
        return f"Migration directory: {migrations_dir}\nFound {len(up_files)} migration files.\n\n" + "\n".join(f"  {f.name}" for f in up_files)

    elif sub == "run":
        files = sorted(migrations_dir.glob("*.sql"))
        up_files = [f for f in files if not f.name.endswith("_down.sql")]
        results = []
        with get_pg_conn() as conn:
            cur = conn.cursor()
            for f in up_files:
                try:
                    cur.execute(f.read_text())
                    results.append(f"  ✓ {f.name}")
                except Exception as e:
                    conn.rollback()
                    results.append(f"  ✗ {f.name}: {e}")
        return "Running migrations:\n" + "\n".join(results)

    return "Usage: migrations <status|run>"


def cmd_plugins(args: list[str], *, actor: dict | None = None, **_kwargs) -> str:
    # B212 (v0.9.6.3): actor is the superadmin dict from run_cli's
    # _require_superadmin call. Passed through to enqueue helpers so the
    # eventual sync log entry is attributed to the right operator.
    actor_user_id = str(actor.get("id")) if actor and actor.get("id") else None
    sub = args[0] if args else "list"
    installed_dir = REPO_ROOT / "plugins" / "installed"

    if sub == "list":
        if not installed_dir.exists():
            return "No plugins installed."
        plugins = []
        for d in sorted(installed_dir.iterdir()):
            manifest = d / "plugin.yaml"
            if manifest.exists():
                import yaml
                data = yaml.safe_load(manifest.read_text())
                name = data.get("display_name") or data.get("name") or d.name
                version = data.get("version", "?")
                ptype = data.get("type", "plugin")
                plugins.append(f"  {d.name:<25} {name:<20} v{version:<10} {ptype}")
        if not plugins:
            return "No plugins installed."
        return "Installed plugins:\n" + "\n".join(plugins)

    elif sub == "sync":
        if len(args) < 2:
            return "Usage: plugins sync <plugin-id> [--no-wait]"
        plugin_id = args[1]
        no_wait = "--no-wait" in args[2:]

        # B205 (v0.9.6): manual triggers always async. Skip the HTTP loopback
        # (which had no session cookie and got 403'd) and call the same
        # internal helpers /api/plugins/:id/sync uses, then poll job_runs
        # until the run reaches a terminal status.
        from .sync import _enforce_concurrency, _enqueue_async_run, _load_sync_config
        from ..plugin_sync import resolve_sync_script

        plugin_dir = REPO_ROOT / "plugins" / "installed" / plugin_id
        if not (plugin_dir / "plugin.yaml").exists():
            return f"Plugin '{plugin_id}' is not installed"
        sync_script, sync_script_rel = resolve_sync_script(plugin_dir)
        if not sync_script.exists():
            return f"Sync script not found for {plugin_id} at {sync_script_rel}"

        cfg = _load_sync_config(plugin_id)
        skip = _enforce_concurrency(
            plugin_id, cfg["concurrency_policy"], actor_user_id=actor_user_id,
        )
        if skip and skip.get("skipped"):
            return (
                f"Sync already running for {plugin_id} "
                f"(run_id={skip['active_run_id']}, status={skip['active_status']}).\n"
                f"  View live progress at /plugin/{plugin_id}/overview Settings tab."
            )

        run_id = _enqueue_async_run(
            plugin_id, "incremental", actor_user_id=actor_user_id,
        )
        if run_id is None:
            return f"Failed to enqueue sync for {plugin_id}"

        if no_wait:
            return f"Sync enqueued for {plugin_id} (run_id={run_id})."

        # Poll until terminal. Time-cap at 10 minutes so the CLI HTTP request
        # doesn't hang forever; longer syncs return "still running" and
        # the operator can check /system/jobs.
        import time as _time
        deadline = _time.monotonic() + 600
        last_progress: dict = {}
        terminal_status = None
        rows_written = None
        duration_ms = None
        error_text = None
        while _time.monotonic() < deadline:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT status, progress, rows_written, duration_ms, error
                    FROM job_runs WHERE id = %s
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
            if not row:
                return f"Run {run_id} disappeared from job_runs unexpectedly"
            status, progress, rows_written, duration_ms, error_text = row
            if isinstance(progress, dict):
                last_progress = progress
            if status in ("success", "error", "timeout", "cancelled", "skipped"):
                terminal_status = status
                break
            _time.sleep(2)

        if terminal_status is None:
            return (
                f"Sync still running after 10 minutes for {plugin_id} "
                f"(run_id={run_id}). Returning to CLI; sync continues in background.\n"
                f"  Last progress: {last_progress.get('message', '(no message)')}\n"
                f"  Use 'plugins sync {plugin_id} --no-wait' next time, or watch "
                f"/plugin/{plugin_id}/overview for live progress."
            )

        pct = last_progress.get("pct")
        msg = last_progress.get("message")
        progress_line = f"  Final progress: {msg or '(none)'}"
        if isinstance(pct, (int, float)):
            progress_line += f" ({pct:.0f}%)"

        if terminal_status == "success":
            return (
                f"Sync succeeded for {plugin_id} (run_id={run_id})\n"
                f"  Duration: {duration_ms}ms · Rows written: {rows_written or 0}\n"
                f"{progress_line}"
            )
        return (
            f"Sync {terminal_status} for {plugin_id} (run_id={run_id})\n"
            f"  Error: {(error_text or '')[:300]}\n"
            f"{progress_line}"
        )

    return "Usage: plugins <list|sync>"


def cmd_cache(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else ""
    if sub == "clear":
        from .auth import _login_limiter
        from .share import _share_limiter
        _login_limiter._store.clear()
        _share_limiter._store.clear()
        return "Cleared rate limiter caches."
    return "Usage: cache clear"


def cmd_jobs(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "history"
    if sub == "history":
        limit = 10
        for i, a in enumerate(args):
            if a == "--limit" and i + 1 < len(args):
                limit = int(args[i + 1])
        try:
            with get_pg_conn() as conn:
                cur = dict_cursor(conn)
                cur.execute("SELECT job_id, started_at, status, duration_ms, source FROM job_runs ORDER BY started_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
            if not rows:
                return "No job runs recorded."
            lines = [f"{'Job':<20} {'Started':<20} {'Status':<10} {'Duration':<10} {'Source'}"]
            lines.append("-" * 75)
            for r in rows:
                started = r["started_at"].strftime("%Y-%m-%d %H:%M") if hasattr(r["started_at"], "strftime") else str(r["started_at"])[:16]
                dur = f"{r['duration_ms']}ms" if r.get("duration_ms") else "-"
                lines.append(f"{r['job_id']:<20} {started:<20} {r['status']:<10} {dur:<10} {r.get('source', '')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"
    return "Usage: jobs history [--limit N]"


def cmd_logs(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "api"
    lines = 20
    for i, a in enumerate(args):
        if a in ("--lines", "--limit", "-n") and i + 1 < len(args):
            lines = min(int(args[i + 1]), 200)

    log_files = {
        "api": [REPO_ROOT / "logs" / "api-error.log", REPO_ROOT / "logs" / "api-out.log"],
        "alerts": [REPO_ROOT / "logs" / "alerts-error.log", REPO_ROOT / "logs" / "alerts-out.log"],
        "health": [REPO_ROOT / "logs" / "health-monitor-error.log", REPO_ROOT / "logs" / "health-monitor-out.log"],
    }
    candidates = log_files.get(sub)
    if not candidates:
        return f"Unknown log: {sub}. Available: {', '.join(log_files.keys())}"
    all_lines: list[str] = []
    for lf in candidates:
        if lf.exists():
            all_lines.extend(lf.read_text().splitlines())
    if not all_lines:
        return f"No log entries found for {sub}."
    all_lines.sort()
    tail = all_lines[-lines:]
    return "\n".join(tail)


def cmd_env(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "check"
    if sub == "check":
        required = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "AUTH_REQUIRED", "NOUSVIZ_ENCRYPTION_KEY"]
        recommended = ["SMTP_HOST", "MULTI_USER_ACCOUNTS"]
        lines = ["Required:"]
        for k in required:
            v = os.environ.get(k)
            lines.append(f"  {k}: {'✓ set' if v else '✗ NOT SET'}")
        lines.append("\nRecommended:")
        for k in recommended:
            v = os.environ.get(k)
            lines.append(f"  {k}: {'✓ set' if v else '— not set'}")
        return "\n".join(lines)
    return "Usage: env check"


def cmd_backup(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "run"

    backup_dir = Path(os.environ.get("BACKUP_DIR", str(REPO_ROOT / "backups")))

    if sub == "run":
        import subprocess
        script = REPO_ROOT / "scripts" / "backup.sh"
        if not script.exists():
            return "Backup script not found at scripts/backup.sh"
        try:
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True, text=True, timeout=120,
                cwd=str(REPO_ROOT),
            )
            output = result.stdout + result.stderr
            return output.strip() or "Backup completed."
        except subprocess.TimeoutExpired:
            return "Backup timed out (120s limit)."
        except Exception as e:
            return f"Backup failed: {e}"

    elif sub == "list":
        if not backup_dir.exists():
            return f"No backup directory at {backup_dir}"
        files = sorted(backup_dir.glob("nousviz_*.sql.gz"), reverse=True)
        if not files:
            return "No backups found."
        lines = [f"{'Filename':<40} {'Size':<10} {'Date'}"]
        lines.append("-" * 65)
        for f in files[:20]:
            size = f.stat().st_size
            size_str = f"{size / 1024 / 1024:.1f}MB" if size > 1024 * 1024 else f"{size / 1024:.0f}KB"
            date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(f"{f.name:<40} {size_str:<10} {date}")
        return "\n".join(lines)

    elif sub == "restore":
        if len(args) < 2:
            return "Usage: backup restore <filename>\nList backups with: backup list"
        filename = args[1]
        filepath = backup_dir / filename
        if not filepath.exists():
            return f"Backup file not found: {filename}"
        return f"To restore, run on the server:\n  gunzip -c {filepath} | psql -U {os.environ.get('POSTGRES_USER', 'nousviz')} {os.environ.get('POSTGRES_DB', 'nousviz')}\n\nWARNING: This will overwrite the current database."

    return "Usage: backup <run|list|restore>"


def cmd_security(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "audit"

    if sub == "audit":
        lines = ["Security audit:"]
        enc_key = os.environ.get("NOUSVIZ_ENCRYPTION_KEY")
        lines.append(f"  Encryption key: {'✓ set ({len(enc_key)} chars)' if enc_key else '✗ NOT SET — credentials stored unencrypted'}")
        auth = os.environ.get("AUTH_REQUIRED", "false")
        lines.append(f"  Auth required: {'✓ enabled' if auth.lower() in ('true', '1') else '✗ DISABLED — API is open'}")
        multi = os.environ.get("MULTI_USER_ACCOUNTS", "false")
        lines.append(f"  Multi-user: {'✓ enabled' if multi.lower() in ('true', '1') else '— disabled (shared password mode)'}")
        smtp = os.environ.get("SMTP_HOST", "")
        lines.append(f"  SMTP: {'✓ configured' if smtp.strip() else '— not configured'}")

        ssl_domain = os.environ.get("NOUSVIZ_DOMAIN", "")
        ssl_type = os.environ.get("NOUSVIZ_SSL", "")
        if ssl_type:
            lines.append(f"  SSL: ✓ {ssl_type} ({ssl_domain})")
        else:
            lines.append("  SSL: ✗ NOT CONFIGURED — traffic is unencrypted")

        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM users WHERE role = 'superadmin' AND is_active = true")
            sa_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM users WHERE is_active = true")
            user_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM user_sessions WHERE expires_at > now()")
            session_count = cur.fetchone()[0]

        lines.append(f"  Active users: {user_count} ({sa_count} superadmin)")
        lines.append(f"  Active sessions: {session_count}")

        issues = []
        if not enc_key:
            issues.append("Set NOUSVIZ_ENCRYPTION_KEY in .env")
        if auth.lower() not in ("true", "1"):
            issues.append("Set AUTH_REQUIRED=true in .env")
        if not ssl_type:
            issues.append("Configure SSL with scripts/ssl-setup.sh")
        if sa_count == 0:
            issues.append("No active superadmin — create one via 'users create'")

        if issues:
            lines.append("\n  Issues:")
            for i in issues:
                lines.append(f"    ✗ {i}")
        else:
            lines.append("\n  ✓ No critical issues found.")

        return "\n".join(lines)

    elif sub == "rotate-key":
        return "Key rotation re-encrypts all stored credentials with a new key.\n\nTo rotate:\n  1. Generate a new key: python3 -c \"import secrets; print(secrets.token_hex(32))\"\n  2. Set NOUSVIZ_ENCRYPTION_KEY_NEW=<new-key> in .env\n  3. Run: python3 -c \"from apps.api.src.services.credentials import rotate_key; rotate_key()\"\n  4. Replace NOUSVIZ_ENCRYPTION_KEY with the new key in .env\n  5. Remove NOUSVIZ_ENCRYPTION_KEY_NEW\n  6. Restart: pm2 reload api --update-env"

    return "Usage: security <audit|rotate-key>"


def cmd_update(args: list[str], **_kwargs) -> str:
    sub = args[0] if args else "check"

    if sub == "check":
        try:
            current = (REPO_ROOT / "VERSION").read_text().strip()
            import urllib.request

            # Fetch latest release
            req = urllib.request.Request(
                "https://api.github.com/repos/nousviz/nousviz-app/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            try:
                res = urllib.request.urlopen(req, timeout=10)
                release = json.loads(res.read())
                latest = release.get("tag_name", "unknown")
                changelog = release.get("body", "")
            except Exception:
                # Fallback to tags if no releases published
                req2 = urllib.request.Request(
                    "https://api.github.com/repos/nousviz/nousviz-app/tags",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                res2 = urllib.request.urlopen(req2, timeout=10)
                tags = json.loads(res2.read())
                latest = tags[0]["name"] if tags else "unknown"
                changelog = ""

            current_clean = current.replace("-dev", "")
            latest_clean = latest.lstrip("v")

            if latest_clean == current_clean:
                return f"✓ Up to date: {current}"

            lines = [
                "Update available!",
                "",
                f"  Current: {current}",
                f"  Latest:  {latest}",
            ]

            if changelog:
                lines.append("")
                lines.append("What's new:")
                lines.append("─" * 40)
                # Trim changelog to first 20 lines
                cl_lines = changelog.strip().split("\n")[:20]
                for cl in cl_lines:
                    lines.append(f"  {cl}")
                if len(changelog.strip().split("\n")) > 20:
                    lines.append("  ...")
                lines.append("─" * 40)

            lines.append("")
            lines.append("To update, run on the server:")
            lines.append("  ./scripts/update.sh")
            lines.append("")
            lines.append("Or from your laptop:")
            lines.append("  ./scripts/deploy-local.sh")

            return "\n".join(lines)
        except Exception as e:
            return f"Could not check for updates: {e}"

    return "Usage: update check"


# ── Command registry ─────────────────────────────────────────────────

COMMANDS = {
    "help": cmd_help,
    "users": cmd_users,
    "health": cmd_health,
    "version": cmd_version,
    "config": cmd_config,
    "migrations": cmd_migrations,
    "plugins": cmd_plugins,
    "cache": cmd_cache,
    "jobs": cmd_jobs,
    "logs": cmd_logs,
    "env": cmd_env,
    "backup": cmd_backup,
    "security": cmd_security,
    "update": cmd_update,
}


# ── Operator-visible logs (P104) ────────────────────────────────────


def _normalize_since(s: str | None) -> str | None:
    """B212 (v0.9.6.3): pad date-only inputs ('YYYY-MM-DD' from the new
    LogsPanel date pickers) to start-of-day UTC for since-bound semantics.
    Full ISO timestamps from old (v0.9.6.1) deep-links pass through
    unchanged — PostgreSQL's timestamptz accepts both shapes."""
    if not s:
        return None
    if len(s) == 10 and s.count("-") == 2:
        return f"{s}T00:00:00Z"
    return s


def _normalize_until(s: str | None) -> str | None:
    """B212: pad date-only inputs to end-of-day UTC. Without this,
    `until=2026-04-29` only matches events written exactly at midnight
    rather than including all of the 29th."""
    if not s:
        return None
    if len(s) == 10 and s.count("-") == 2:
        return f"{s}T23:59:59.999999Z"
    return s


@router.get(
    "/logs",
    operation_id="admin.logs.list",
    response_model=LogsListResponse,
    response_model_exclude_none=True,
    summary="Paginated app_logs feed with filters",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.logs permission."},
    },
)
async def get_logs(
    request: Request,
    source: str | None = None,
    level: str | None = None,
    since: str | None = None,
    until: str | None = None,
    plugin_id: str | None = None,
    actor_user_id: str | None = None,
    run_id: int | None = None,
    q: str | None = None,
    cursor: int | None = None,
    limit: int = 100,
    _: None = Depends(requires("system.logs")),
):
    """Return application logs. Admin only.

    B208 (v0.9.6.1): supports filtering on the promoted columns
    (plugin_id, actor_user_id, run_id) plus free-text search and date
    range. Falls back to detail->>'key' for legacy rows where the
    promoted column is NULL, so events written before the migration
    are still discoverable.

    Pagination: keyset on `id` descending. Pass the response's
    `next_cursor` back as `cursor` for the next page.

    B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
    or full ISO timestamps. Date-only inputs are normalized to start /
    end of UTC day server-side.
    """
    from ..db import get_pg_conn

    since = _normalize_since(since)
    until = _normalize_until(until)

    clauses = ["1=1"]
    params: list = []

    if source and source != "all":
        clauses.append("al.source = %s")
        params.append(source)
    if level and level != "all":
        clauses.append("al.level = %s")
        params.append(level)
    if since:
        clauses.append("al.created_at >= %s")
        params.append(since)
    if until:
        clauses.append("al.created_at <= %s")
        params.append(until)

    # B208: column + JSONB-fallback predicates so legacy rows remain
    # filterable until the column is fully populated by new writes.
    if plugin_id:
        clauses.append(
            "(al.plugin_id = %s "
            "OR (al.plugin_id IS NULL AND al.detail->>'plugin_id' = %s))"
        )
        params.extend([plugin_id, plugin_id])
    if actor_user_id:
        clauses.append(
            "(al.actor_user_id::text = %s "
            "OR (al.actor_user_id IS NULL AND al.detail->>'actor_user_id' = %s))"
        )
        params.extend([actor_user_id, actor_user_id])
    if run_id is not None:
        clauses.append(
            "(al.run_id = %s "
            "OR (al.run_id IS NULL AND al.detail->>'run_id' = %s))"
        )
        params.extend([run_id, str(run_id)])
    if q:
        clauses.append("al.message ILIKE %s")
        params.append(f"%{q}%")
    if cursor is not None:
        clauses.append("al.id < %s")
        params.append(cursor)

    where = " AND ".join(clauses)
    limit = max(1, min(limit, 500))

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT al.id, al.level, al.source, al.message, al.detail,
                   al.created_at, al.plugin_id, al.actor_user_id, al.run_id,
                   u.email AS actor_email,
                   jr.status AS run_status
            FROM app_logs al
            LEFT JOIN users u ON u.id = al.actor_user_id
            LEFT JOIN job_runs jr ON jr.id = al.run_id
            WHERE {where}
            ORDER BY al.id DESC
            LIMIT %s
            """,
            params + [limit],
        )
        logs = []
        # B313 (v0.10.4): if a log entry carries `stderr_tail` in its
        # detail JSON (sync/hook failures), extract a clean headline so
        # the surface can render "<ExceptionType>: <message>" up front
        # instead of the raw, head-chopped traceback dump.
        from ..services.error_summary import extract_error_summary

        for row in cur.fetchall():
            (
                id_, lvl, src, msg, detail, created_at,
                p_id, a_uid, r_id, a_email, r_status,
            ) = row

            error_summary: Optional[str] = None
            if isinstance(detail, dict):
                stderr_tail = detail.get("stderr_tail")
                if stderr_tail:
                    parsed = extract_error_summary(stderr_tail)
                    error_summary = parsed["summary"]

            logs.append({
                "id": id_,
                "level": lvl,
                "source": src,
                "message": msg,
                "detail": detail,
                "error_summary": error_summary,
                "created_at": (
                    created_at.isoformat()
                    if created_at and hasattr(created_at, "isoformat")
                    else created_at
                ),
                "plugin_id": p_id,
                "actor_user_id": str(a_uid) if a_uid else None,
                "run_id": r_id,
                "actor_email": a_email,
                "run_status": r_status,
            })

    next_cursor = logs[-1]["id"] if len(logs) == limit else None
    return {"logs": logs, "next_cursor": next_cursor}


@router.get(
    "/logs/filters",
    operation_id="admin.logs.filters",
    response_model=LogFiltersResponse,
    summary="Distinct values for the /system/logs filter dropdowns",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.logs permission."},
    },
)
async def get_log_filters(
    request: Request,
    _: None = Depends(requires("system.logs")),
):
    """B208 (v0.9.6.1): distinct values for the dropdown filters on
    /system/logs. Limited to events written in the last 30 days so the
    dropdowns don't accumulate stale plugin slugs or deleted users.

    Returns:
        plugins: list of distinct plugin_id values.
        users: list of {id, email} tuples for distinct actors.
    """
    from ..db import get_pg_conn

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT plugin_id FROM app_logs
            WHERE plugin_id IS NOT NULL
              AND created_at >= now() - interval '30 days'
            ORDER BY plugin_id
            """
        )
        plugins = [r[0] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT al.actor_user_id, u.email
            FROM app_logs al
            LEFT JOIN users u ON u.id = al.actor_user_id
            WHERE al.actor_user_id IS NOT NULL
              AND al.created_at >= now() - interval '30 days'
            ORDER BY u.email NULLS LAST
            """
        )
        users = [{"id": str(r[0]), "email": r[1]} for r in cur.fetchall()]

    return {"plugins": plugins, "users": users}
