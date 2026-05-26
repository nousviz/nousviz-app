"""
/api/plugins — Plugin metadata endpoints

Reads plugin.yaml files and serves dashboard/dataset/alert specs to the frontend.
"""

import ipaddress
import os
import re
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .auth import get_me
from ..db import get_pg_conn
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.plugins import (
    InstallTestResponse,
    PluginAuditLogResponse,
    PluginCapabilitiesResponse,
    PluginCatalogResponse,
    PluginConnectionsResponse,
    PluginConnectionsSaveResponse,
    PluginEntry,
    PluginFrontendComponentsResponse,
    PluginInstallResponse,
    PluginListResponse,
    PluginModulesListResponse,
    PluginModuleToggleResponse,
    PluginSettingsResponse,
    PluginSettingsSaveResponse,
    PluginUninstallResponse,
    PluginUpdateInfo,
    PluginUpdateResponse,
    PluginUpdatesListResponse,
    PluginYamlResource,
    RevokeFrontendTrustResponse,
    SyncScheduleGetResponse,
    SyncScheduleSetResponse,
    SyncStatusResponse,
    TrustFrontendResponse,
    UninstallCheckResponse,
)

logger = logging.getLogger("nousviz.api.plugins")


def _get_deploy_key_path(host: str, repo_url: str | None = None) -> str | None:
    """Get the path to a temporary deploy key file.

    B204: only exact `repo_url` matches return a key. The previous host
    fallback (`WHERE host = %s LIMIT 1`) silently picked an arbitrary
    sibling key when multiple existed for the same host, causing a
    confusing `Permission denied (publickey)` even when the right key
    was registered for a different repo.

    Returns None if no per-repo key is registered. Callers should
    surface a clear "register a deploy key for this URL" error to the
    operator (see B203 logging).
    """
    if not repo_url:
        return None
    try:
        import tempfile
        from cryptography.fernet import Fernet
        import base64
        enc_key = os.environ.get("NOUSVIZ_ENCRYPTION_KEY", "")
        if not enc_key:
            return None
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT private_key_encrypted FROM deploy_keys WHERE repo_url = %s LIMIT 1",
                (repo_url,),
            )
            row = cur.fetchone()
        if not row:
            return None
        fernet = Fernet(base64.urlsafe_b64encode(bytes.fromhex(enc_key)[:32]))
        private_key = fernet.decrypt(row[0].encode()).decode()
        f = tempfile.NamedTemporaryFile(mode="w", suffix="_deploy", delete=False)
        f.write(private_key)
        f.close()
        os.chmod(f.name, 0o600)
        return f.name
    except Exception:
        return None


def _log_plugin_action(plugin_id: str, action: str, detail: dict | None = None, user_id: str | None = None, ip: str | None = None) -> None:
    try:
        import json
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO plugin_audit_log (plugin_id, action, detail, user_id, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (plugin_id, action, json.dumps(detail or {}), user_id, ip))
    except Exception as e:
        logger.warning(f"Plugin audit log failed for {plugin_id}/{action}: {e}")

# ── Install rate limiter (P22-G3) ────────────────────────────────────
# Max 5 install attempts per IP per 5-minute window.
# Stored in-process; resets on restart (acceptable — prevents runaway installs).

_INSTALL_RATE_WINDOW = 5 * 60   # seconds
_INSTALL_RATE_LIMIT  = 5
_install_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_install_rate(client_ip: str) -> None:
    """Raise 429 if this IP has exceeded the install rate limit."""
    now = time.monotonic()
    window_start = now - _INSTALL_RATE_WINDOW
    recent = [t for t in _install_timestamps[client_ip] if t > window_start]
    if len(recent) >= _INSTALL_RATE_LIMIT:
        raise HTTPException(
            429,
            f"Too many install requests. Maximum {_INSTALL_RATE_LIMIT} installs per "
            f"{_INSTALL_RATE_WINDOW // 60} minutes.",
        )
    recent.append(now)
    _install_timestamps[client_ip] = recent

router = APIRouter(tags=["plugins"])

# B228: register all plugins.py routes.
# Read tier — viewer+
register_route("GET", "/api/plugins", "plugins.read")
register_route("GET", "/api/plugins/audit-log", "system.audit")
register_route("GET", "/api/plugins/capabilities", "plugins.read")
register_route("GET", "/api/plugins/catalog", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/dashboards/{dashboard_name}", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/datasets/{dataset_name}", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/uninstall-check", "plugins.install")
register_route("GET", "/api/plugins/updates", "plugins.install")
register_route("GET", "/api/plugins/{plugin_id}/alerts/{alert_name}", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/settings", "plugins.configure")
register_route("GET", "/api/plugins/{plugin_id}/modules", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/connections", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/sync/status", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/sync-schedule", "plugins.configure")
register_route("GET", "/api/plugins/{plugin_id}/frontend-components", "plugins.read")
register_route("GET", "/api/plugins/{plugin_id}/widget/{filename}", "plugins.read")
# Write tier — install / uninstall / configure
register_route("POST", "/api/plugins/{plugin_id}/install/test", "plugins.install")
register_route("POST", "/api/plugins/{plugin_id}/install", "plugins.install")
register_route("DELETE", "/api/plugins/{plugin_id}/install", "plugins.install")
register_route("POST", "/api/plugins/{plugin_id}/check-update", "plugins.install")
register_route("POST", "/api/plugins/{plugin_id}/update", "plugins.install")
register_route("POST", "/api/plugins/{plugin_id}/settings", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/modules/{module_name}/enable", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/modules/{module_name}/disable", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/connections", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/sync-schedule", "plugins.configure")
register_route("POST", "/api/plugins/{plugin_id}/trust-frontend", "plugins.install")
register_route("POST", "/api/plugins/{plugin_id}/revoke-frontend-trust", "plugins.install")


# ── P19: repository URL validation (SSRF prevention) ─────────────────

def _validate_repo_url(url: str) -> str:
    """
    Accept HTTPS or SSH git URLs. Block file://, localhost, private IPs.
    For private HTTPS repos, injects GITHUB_TOKEN if configured.
    Returns normalised URL.
    """
    # SSH format: git@github.com:org/repo.git
    if url.startswith("git@"):
        host = url.split("@")[1].split(":")[0] if ":" in url else ""
        if not host or host in ("localhost", "127.0.0.1"):
            raise HTTPException(400, "SSH URL must point to a public host")
        if not url.endswith(".git"):
            url = url.rstrip("/") + ".git"
        return url

    parsed = urlparse(url)
    if parsed.scheme not in ("https", "ssh"):
        raise HTTPException(400, "repository_url must use https:// or git@ (SSH)")
    host = parsed.hostname
    if not host:
        raise HTTPException(400, "Invalid repository_url: no hostname")
    if host in ("localhost", "127.0.0.1", "::1"):
        raise HTTPException(400, "repository_url must point to a public host")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise HTTPException(400, "repository_url must point to a public host (private IP blocked)")
    except ValueError:
        pass
    if not url.endswith(".git"):
        url = url.rstrip("/") + ".git"

    # Inject GitHub token for private HTTPS repos
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if github_token and host and "github.com" in host and "@" not in (parsed.netloc or ""):
        url = url.replace("https://github.com", f"https://{github_token}@github.com")

    return url


class PluginInstallRequest(BaseModel):
    repository_url: Optional[str] = None  # Tier 3 (private) or override


class SyncScheduleBody(BaseModel):
    """Per-plugin schedule override.

    B148: cron=None or "" clears the override (falls back to manifest).
    B205 (v0.9.6): friendly form — supply interval_value + interval_unit
    instead of a raw cron expression. The two forms are mutually exclusive
    in a single request.

    Examples:
        {"cron": "*/15 * * * *"}                      raw cron
        {"interval_value": 15, "interval_unit": "minutes"}  friendly form
        {"cron": null}                                 clear override
    """
    cron: Optional[str] = None
    interval_value: Optional[int] = None
    interval_unit: Optional[str] = None  # "minutes" | "hours" | "days"


# Plugin directories
REPO_ROOT = Path(__file__).resolve().parents[4]
OFFICIAL_DIR  = REPO_ROOT / "plugins" / "official"
INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"
COMMUNITY_DIR = REPO_ROOT / "plugins" / "community"
UTILITIES_DIR = REPO_ROOT / "plugins" / "utilities"

# Capability registry — populated from installed utility plugins' `provides:` field
_registered_capabilities: set[str] = set()

# Only allow safe plugin slug characters — prevents path traversal
_SAFE_PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9\-_]{0,63}$")


def _validate_plugin_id(plugin_id: str) -> None:
    """Raise 400 if plugin_id contains path traversal or unsafe characters."""
    if not _SAFE_PLUGIN_ID.match(plugin_id):
        raise HTTPException(400, f"Invalid plugin id '{plugin_id}'. Must be lowercase alphanumeric with hyphens/underscores.")


def _field_is_secret(field: dict) -> bool:
    """B124 (v0.8.6.2): a field is secret if it declares `secret: true`
    OR if it uses the legacy `type: password` convention. Implicit
    secrecy via `type: password` is preserved for v0.8.5 backward compat —
    plugin authors who want a secret file/text/anything else must set
    `secret: true` explicitly.
    """
    if field.get("secret") is True:
        return True
    return field.get("type") == "password"


def _set_env_safe(key: str, value: str) -> bool:
    """B129 (v0.8.6.4): set os.environ[key] defensively.

    Used for NON-secret plugin settings that mirror into the process env
    so the API worker can use them immediately (health checks, test
    endpoints). Secret values are NOT routed through here — they live in
    the credentials table and are delivered to plugin subprocesses via
    the credential broker (Unix socket) introduced in v0.9.0 (P208).

    Python's putenv refuses null bytes; we strip them defensively. If
    putenv still rejects the value (unusual platforms), we log and return
    False so the caller can continue — the value is already on disk in
    .env or in the DB, the env mirror is just convenience.
    """
    cleaned = (value if isinstance(value, str) else str(value)).replace("\x00", "")
    try:
        os.environ[key] = cleaned
        return True
    except (ValueError, TypeError, OSError) as exc:
        logger.warning(
            "env mirror skipped for %s: %s (value length=%d). DB/file write still applies.",
            key, exc, len(cleaned),
        )
        return False


# Characters forbidden in non-secret field values (these get written to
# .env, which is line-based and shell-parseable).
_ENV_FORBIDDEN_CHARS = ("\n", "\r", "\x00", "=")


def _validate_env_value(field_name: str, val: str) -> None:
    """Raise HTTPException(400) if val contains characters that would
    corrupt .env. Non-secret values MUST round-trip through a `KEY=VAL`
    line safely.

    If a plugin author needs content with newlines, null bytes, or `=`
    in the value, they declare `secret: true` on the field — it then
    lands in the credentials table instead of .env.
    """
    if not isinstance(val, str):
        return
    for ch in _ENV_FORBIDDEN_CHARS:
        if ch in val:
            name = {"\n": "newline", "\r": "carriage return", "\x00": "null byte", "=": "'=' character"}[ch]
            raise HTTPException(
                400,
                f"Field '{field_name}' contains a {name}; non-secret fields must be "
                f"safe for .env storage. Mark the field `secret: true` in plugin.yaml "
                f"to store it encrypted instead.",
            )

# Dirs that contain fully installed plugins (have routes, dashboards, datasets, etc.)
ACTIVE_PLUGIN_DIRS = [INSTALLED_DIR, COMMUNITY_DIR]
# All dirs — includes official/ stubs and utilities/ which are catalog metadata only
ALL_PLUGIN_DIRS = [INSTALLED_DIR, COMMUNITY_DIR, OFFICIAL_DIR, UTILITIES_DIR]


def _get_enabled_module_names(plugin_id: str) -> list[str]:
    """Get list of enabled module names for a plugin."""
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=True)
    if not plugin_dir:
        return []
    modules_dir = plugin_dir / "modules"
    if not modules_dir.exists():
        return []

    enabled = []
    for mod_dir in sorted(modules_dir.iterdir()):
        if not mod_dir.is_dir() or not (mod_dir / "module.yaml").exists():
            continue
        mod_name = mod_dir.name
        # Check DB state
        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT enabled FROM plugin_modules WHERE plugin_id = %s AND module_name = %s",
                    (plugin_id, mod_name),
                )
                row = cur.fetchone()
                if row:
                    if row[0]:
                        enabled.append(mod_name)
                    continue
        except Exception:
            pass
        # No DB row — check module.yaml default
        try:
            with open(mod_dir / "module.yaml") as f:
                mod_manifest = yaml.safe_load(f)
            if mod_manifest.get("enabled_by_default", True):
                enabled.append(mod_name)
        except Exception:
            enabled.append(mod_name)  # Default to enabled

    return enabled


def _merge_module_manifests(plugin_id: str, manifest: dict) -> dict:
    """Merge enabled module manifests into the parent plugin manifest."""
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=True)
    if not plugin_dir:
        return manifest

    modules_dir = plugin_dir / "modules"
    if not modules_dir.exists():
        return manifest

    enabled_modules = _get_enabled_module_names(plugin_id)
    if not enabled_modules:
        return manifest

    # Merge each enabled module
    for mod_name in enabled_modules:
        mod_yaml_path = modules_dir / mod_name / "module.yaml"
        if not mod_yaml_path.exists():
            continue
        try:
            with open(mod_yaml_path) as f:
                mod_manifest = yaml.safe_load(f)
        except Exception:
            continue

        # Merge navigation
        for nav in mod_manifest.get("navigation", []):
            manifest.setdefault("navigation", []).append(nav)

        # Merge dashboards
        for dash in mod_manifest.get("dashboards", []):
            manifest.setdefault("dashboards", []).append(dash)

        # Merge settings (tagged with source module for frontend grouping)
        for setting in mod_manifest.get("settings", []):
            setting["_module"] = mod_name
            setting["_module_label"] = mod_manifest.get("display_name", mod_name)
            manifest.setdefault("settings", []).append(setting)

        # Merge connections (tagged with source module)
        for conn in mod_manifest.get("connections", []):
            conn["_module"] = mod_name
            conn["_module_label"] = mod_manifest.get("display_name", mod_name)
            manifest.setdefault("connections", []).append(conn)

        # Merge tables.
        # B169 (v0.9.5.1): dedupe. Pre-v0.9.5.1 this appended unconditionally,
        # so a plugin whose main plugin.yaml declares table `foo` AND whose
        # module manifest re-declares `foo` ended up with `foo` twice in the
        # merged manifest. Visible on the Datasets page as duplicate rows
        # ("4 tables" rendered as 7 with dupes for SDI). Order-preserving
        # de-dup keeps first declaration wins.
        existing_tables = manifest.setdefault("databases", {}).setdefault("postgres", {}).setdefault("tables", [])
        for table in (mod_manifest.get("databases", {}).get("postgres", {}).get("tables", [])):
            if table not in existing_tables:
                existing_tables.append(table)

    return manifest


def _find_plugin_dir(plugin_id: str, installed_only: bool = False) -> Path | None:
    """Find a plugin's directory.

    installed_only=True (default for content serving) searches installed/ and
    community/ only — official/ stubs have no dashboards/datasets/alerts and
    must not shadow the installed copy.

    installed_only=False includes official/ as a fallback, used only when the
    caller explicitly needs to find a stub (e.g. reading requires before install).
    """
    dirs = ACTIVE_PLUGIN_DIRS if installed_only else ALL_PLUGIN_DIRS
    for base in dirs:
        plugin_dir = base / plugin_id
        if (plugin_dir / "plugin.yaml").exists():
            return plugin_dir
    return None


def _installed_slugs() -> set:
    """Return set of slugs present in installed/ or community/."""
    slugs = set()
    for base in ACTIVE_PLUGIN_DIRS:
        if base.exists():
            for d in base.iterdir():
                if d.is_dir() and (d / "plugin.yaml").exists():
                    slugs.add(d.name)
    return slugs


def _load_plugin(plugin_id: str, installed_only: bool = False) -> dict | None:
    """Load a plugin's plugin.yaml."""
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=installed_only)
    if not plugin_dir:
        return None
    with open(plugin_dir / "plugin.yaml") as f:
        return yaml.safe_load(f)


def _load_yaml(plugin_id: str, subpath: str) -> dict | None:
    """Load a YAML file from within a plugin directory (installed plugins only)."""
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=True)
    if not plugin_dir:
        return None
    filepath = plugin_dir / subpath
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return yaml.safe_load(f)


def _plugin_entry(d: Path, data: dict, installed: bool, source: str = "official") -> dict:
    """Build a plugin list entry from a manifest and its directory."""
    return {
        "id": data.get("id") or data.get("name") or d.name,
        "display_name": data.get("display_name"),
        "version": data.get("version"),
        "description": data.get("description"),
        "author": data.get("author") or (data.get("publisher") or {}).get("name"),
        "icon": data.get("icon"),
        "category": data.get("category"),
        "tags": data.get("tags", []),
        "visibility": data.get("visibility", "public"),
        "license": data.get("license"),
        "homepage": data.get("homepage"),
        "repository": data.get("repository"),
        "repository_url": data.get("repository_url"),  # community plugins declare this
        "installed": installed,
        "source": source,  # "official" | "community" | "installed"
        "dashboards": [
            {"name": db["name"], "label": db["label"]}
            for db in data.get("dashboards", [])
        ],
        "publisher": data.get("publisher"),
        "requires": data.get("requires"),
        "connections": data.get("connections"),
        "databases": data.get("databases"),
        "navigation": data.get("navigation"),
        "datasets": data.get("datasets"),
        "settings": data.get("settings"),
        "alerts": data.get("alerts"),
        "depends_on": data.get("depends_on"),
        "screenshots": data.get("screenshots"),
        "long_description": data.get("long_description"),
        "changelog_url": data.get("changelog_url"),
        "support_url": data.get("support_url"),
        # Utility plugin fields
        "type": data.get("type"),  # "utility" for utility plugins
        "provides": data.get("provides", []),
        "install_hook": data.get("install_hook"),
        "uninstall_hook": data.get("uninstall_hook"),
        "health_check": data.get("health_check"),
        # Module system
        "modules": data.get("modules", []),
    }


def _fetch_last_sync_batch(plugin_ids: list[str]) -> dict[str, str]:
    """Return ``{plugin_id: last_sync_iso}`` for every plugin that has a
    recorded sync, in two batched DB queries instead of 2N per-plugin
    lookups.

    Logic mirrors the original per-plugin path: prefer the most recent
    successful `job_runs` row for `sync:<plugin_id>`; fall back to the
    legacy `plugin_settings._last_sync` value when newer or when no
    `job_runs` row exists. Keystone B — Phase 12 perf fix.

    Missing plugins simply don't appear in the result dict.
    """
    result: dict[str, str] = {}
    if not plugin_ids:
        return result

    job_ids = [f"sync:{pid}" for pid in plugin_ids]
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # 1. Most-recent successful sync per job_id. DISTINCT ON keeps
            # one row per job_id (the most recent one) in one round trip.
            try:
                cur.execute(
                    """
                    SELECT DISTINCT ON (job_id) job_id, completed_at
                    FROM job_runs
                    WHERE job_id = ANY(%s)
                      AND status = 'success'
                      AND completed_at IS NOT NULL
                    ORDER BY job_id, completed_at DESC
                    """,
                    (job_ids,),
                )
                for row in cur.fetchall():
                    jid, completed_at = row[0], row[1]
                    if completed_at and jid.startswith("sync:"):
                        result[jid[len("sync:"):]] = completed_at.isoformat()
            except Exception:
                conn.rollback()

            # 2. Legacy plugin_settings._last_sync — fold in when newer.
            try:
                cur.execute(
                    """
                    SELECT plugin_id, value
                    FROM plugin_settings
                    WHERE plugin_id = ANY(%s) AND key = '_last_sync'
                    """,
                    (plugin_ids,),
                )
                for row in cur.fetchall():
                    pid, value = row[0], row[1]
                    legacy_ts = value.get("timestamp") if isinstance(value, dict) else value
                    if legacy_ts is None:
                        continue
                    legacy_str = str(legacy_ts)
                    existing = result.get(pid)
                    if existing is None or legacy_str > existing:
                        result[pid] = legacy_str
            except Exception:
                conn.rollback()
    except Exception as exc:
        logger.warning(f"_fetch_last_sync_batch: DB error — {exc}")

    return result


def _enrich_datasets(
    entry: dict,
    *,
    tables_drift_by_plugin: dict[str, tuple] | None = None,
    last_sync_by_plugin: dict[str, str] | None = None,
) -> dict:
    """Build datasets[] from the catalog (source of truth) and layer
    manifest annotations on top.

    B170-rev2 (v0.9.5.3): catalog drives, manifest enriches. Pre-v0.9.5.3
    this function trusted the manifest's `datasets[]` declarations and
    added row counts. Now: the catalog's discovered tables are the base,
    and manifest entries (label, description, grain, semantic_type) are
    layered on top by `name`. A plugin without a `datasets:` block in
    its manifest still gets discovered tables surfaced (with default
    label = table name).

    Sets:
      - entry["datasets"]: list of {name, label, db, rows, last_sync,
        columns, schema, ...} for every discovered table.
      - entry["manifest_drift"]: list of table names the manifest
        declared that don't exist in the catalog. Empty when aligned.

    Per-table row counts come from `pg_class.reltuples` via the catalog
    (cheap estimate). For exact counts use the rows endpoint's `total`.

    Per-plugin last_sync logic is unchanged: prefer job_runs, fall back
    to legacy plugin_settings._last_sync.

    Keystone B (Phase 12 perf): when called from ``list_plugins`` the
    caller passes pre-fetched ``tables_drift_by_plugin`` and
    ``last_sync_by_plugin`` dicts, so this function does zero DB work.
    When called without them (other callers, defensive) it falls back to
    the per-plugin path.
    """
    plugin_id = entry.get("id")
    if not plugin_id:
        # Fallback to a no-op: this is an officially-listed marketplace
        # entry with no install slug. Manifest's datasets stay as-is.
        return entry

    # Catalog discovery (source of truth) — use batched data when provided.
    if tables_drift_by_plugin is not None:
        discovered, drift = tables_drift_by_plugin.get(plugin_id, ([], []))
    else:
        try:
            from .. import catalog as catalog_mod
            discovered = catalog_mod.list_tables_for_plugin(plugin_id)
            drift = catalog_mod.detect_manifest_drift(plugin_id)
        except Exception as exc:
            logger.warning(
                f"_enrich_datasets: catalog lookup failed for {plugin_id}: {exc}"
            )
            discovered = []
            drift = []

    # Manifest annotations indexed by name (case-sensitive)
    manifest_datasets = entry.get("datasets") or []
    annotations: dict[str, dict] = {}
    for ds in manifest_datasets:
        if isinstance(ds, dict) and ds.get("name"):
            annotations[ds["name"]] = ds

    # Build dataset entries from catalog + annotations
    enriched: list[dict] = []
    for tbl in discovered:
        ann = annotations.get(tbl.name) or {}
        ds_entry = {
            "name": tbl.name,
            "label": ann.get("label") or tbl.name,
            "description": ann.get("description"),
            "grain": ann.get("grain"),
            "semantic_type": ann.get("semantic_type"),
            "db": ann.get("db") or "postgres",
            "table_type": tbl.table_type,
            "rows": tbl.row_count_estimate,
            "columns": [
                {
                    "name": c.name,
                    "data_type": c.data_type,
                    "is_nullable": c.is_nullable,
                    "ordinal_position": c.ordinal_position,
                }
                for c in tbl.columns
            ],
        }
        enriched.append(ds_entry)

    # Per-plugin last_sync — use batched data when provided.
    if last_sync_by_plugin is not None:
        last_sync_iso = last_sync_by_plugin.get(plugin_id)
    else:
        last_sync_iso = None
        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT completed_at
                        FROM job_runs
                        WHERE job_id = %s AND status = 'success' AND completed_at IS NOT NULL
                        ORDER BY completed_at DESC
                        LIMIT 1
                        """,
                        (f"sync:{plugin_id}",),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        last_sync_iso = row[0].isoformat()
                except Exception:
                    conn.rollback()
                try:
                    cur.execute(
                        "SELECT value FROM plugin_settings WHERE plugin_id = %s AND key = '_last_sync'",
                        (plugin_id,),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        v = row[0]
                        legacy_ts = v.get("timestamp") if isinstance(v, dict) else v
                        if legacy_ts and (last_sync_iso is None or str(legacy_ts) > last_sync_iso):
                            last_sync_iso = str(legacy_ts)
                except Exception:
                    conn.rollback()
        except Exception:
            pass

    if last_sync_iso:
        for ds in enriched:
            ds["last_sync"] = last_sync_iso

    entry["datasets"] = enriched
    entry["manifest_drift"] = drift
    return entry


@router.get(
    "/plugins",
    operation_id="plugins.list",
    response_model=PluginListResponse,
    response_model_exclude_none=True,
    summary="List installed plugins",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
    },
)
async def list_plugins(request: Request, _: None = Depends(requires("plugins.read"))):
    """List only active (installed) plugins — used by the Installed Plugins page and sidebar.

    B144 (v0.9.2.4): each entry carries an `update_status` block from the
    plugin_update_status cache. Stale entries (older than ~1h) trigger a
    fire-and-forget refresh in the background so the next call sees fresh
    data. The current call doesn't block on the network check.

    Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
    lookups that `_enrich_datasets` used to fire per-plugin are now
    pre-fetched in two batched calls before the loop. Drops `/api/plugins`
    DB round trips from ~6N to ~3 for the enrichment block alone.

    B305 (v0.10.0.6): the result list is filtered through
    `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
    allowlist (resource_acls rows for resource_type='plugin') sees only
    their permitted set + utilities. Admins/superadmins bypass.
    """
    from ..rbac import filter_plugins_for_user
    from ..plugin_update_checker import get_cached_status, is_stale, schedule_async_check
    from .. import catalog as catalog_mod

    # First pass: enumerate installed plugin IDs (cheap — already cached
    # by Keystone A via the ownership map). We need the IDs up-front so
    # the batched fetches below can scope to exactly this request's plugins.
    plugin_id_list: list[str] = []
    plugin_dirs: list[tuple[Path, str, dict]] = []  # (dir, plugin_id, parsed_data)
    for base_dir in ACTIVE_PLUGIN_DIRS:
        if base_dir.exists():
            for d in sorted(base_dir.iterdir()):
                if d.is_dir():
                    manifest = d / "plugin.yaml"
                    if manifest.exists():
                        with open(manifest) as f:
                            data = yaml.safe_load(f)
                        plugin_id = data.get("name", d.name)
                        data = _merge_module_manifests(plugin_id, data)
                        plugin_dirs.append((d, plugin_id, data))
                        plugin_id_list.append(plugin_id)

    # Batched catalog + last-sync fetches.
    try:
        tables_drift_by_plugin = catalog_mod.tables_and_drift_for_plugins(plugin_id_list)
    except Exception as exc:
        logger.warning(f"list_plugins: batched catalog lookup failed — {exc}")
        tables_drift_by_plugin = None
    try:
        last_sync_by_plugin = _fetch_last_sync_batch(plugin_id_list)
    except Exception as exc:
        logger.warning(f"list_plugins: batched last_sync lookup failed — {exc}")
        last_sync_by_plugin = None

    # Second pass: enrich each entry from the pre-fetched dicts.
    plugins = []
    for d, plugin_id, data in plugin_dirs:
        entry = _enrich_datasets(
            _plugin_entry(d, data, installed=True),
            tables_drift_by_plugin=tables_drift_by_plugin,
            last_sync_by_plugin=last_sync_by_plugin,
        )

        # B144: attach update status; lazy-refresh if stale
        try:
            cached = get_cached_status(plugin_id)
            if cached is None or is_stale(plugin_id):
                schedule_async_check(plugin_id)
            entry["update_status"] = (
                {
                    "source_class": cached.source_class,
                    "installed_version": cached.installed_version,
                    "latest_version": cached.latest_version,
                    "update_available": cached.update_available,
                    "last_error": cached.last_error,
                }
                if cached
                else {
                    "source_class": "pending",
                    "installed_version": data.get("version"),
                    "latest_version": None,
                    "update_available": False,
                    "last_error": None,
                }
            )
        except Exception as exc:
            logger.debug("update_status enrich failed for %s: %s", plugin_id, exc)

        # B151 (v0.9.4): attach frontend.components + trust state.
        # B304 (v0.10.0.5) + v0.10.0.5.1: also surface admin_proxy
        # flag so the install/Trust modal can render the
        # admin-proxy consent line for opted-in plugins.
        try:
            declared_fe = _frontend_components_from_manifest(data)
            if declared_fe:
                trusted = _is_frontend_trusted(plugin_id)
                admin_proxy = bool(
                    (data.get("frontend") or {}).get("admin_proxy", False)
                )
                entry["frontend"] = {
                    "components": declared_fe,
                    "trusted": trusted,
                    "needs_consent": not trusted,
                    "admin_proxy": admin_proxy,
                }
        except Exception as exc:
            logger.debug("frontend enrich failed for %s: %s", plugin_id, exc)

        plugins.append(entry)

    # B305: per-user plugin allowlist. No-op for admin/superadmin and for
    # viewer/analyst with zero ACL rows.
    #
    # GET /api/plugins is in middleware PUBLIC_GET_PATTERNS, so this handler
    # can be reached without a session token (share-viewer loader, plugin
    # frontend-component bootstrap before the token attaches, etc.). When
    # get_me() raises 401 in that case, fall through to the unfiltered list
    # instead of surfacing a 401 on a public endpoint.
    try:
        current_user = get_me(request)
        plugins = filter_plugins_for_user(plugins, current_user)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    except Exception:
        logger.exception("list_plugins: B305 filter failed — returning unfiltered list")
    return {"plugins": plugins}


def _load_registry_stats() -> dict[str, dict]:
    """
    P20b: Load install counts, featured flags, and listing status from plugin_registry.
    Returns {slug: {install_count, featured, listed, pricing_model}}.
    Falls back gracefully if the table doesn't exist or DB is unavailable.
    """
    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT slug, install_count, featured, listed, pricing_model
                FROM plugin_registry
            """)
            return {
                row[0]: {
                    "install_count": row[1] or 0,
                    "featured": row[2] or False,
                    "listed": row[3] if row[3] is not None else True,
                    "pricing_model": row[4],
                }
                for row in cur.fetchall()
            }
    except Exception:
        return {}


@router.get(
    "/plugins/audit-log",
    operation_id="plugins.audit_log",
    response_model=PluginAuditLogResponse,
    response_model_exclude_none=True,
    summary="Recent plugin lifecycle events (install/uninstall/update/etc.)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def get_plugin_audit_log(
    plugin_id: str | None = None,
    limit: int = 50,
    _: None = Depends(requires("system.audit")),
):
    """View plugin audit log entries."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            if plugin_id:
                cur.execute("""
                    SELECT l.plugin_id, l.action, l.detail, l.ip_address, l.created_at, u.name as user_name
                    FROM plugin_audit_log l LEFT JOIN users u ON u.id = l.user_id
                    WHERE l.plugin_id = %s ORDER BY l.created_at DESC LIMIT %s
                """, (plugin_id, limit))
            else:
                cur.execute("""
                    SELECT l.plugin_id, l.action, l.detail, l.ip_address, l.created_at, u.name as user_name
                    FROM plugin_audit_log l LEFT JOIN users u ON u.id = l.user_id
                    ORDER BY l.created_at DESC LIMIT %s
                """, (limit,))
            cols = [d[0] for d in cur.description]
            entries = []
            for row in cur.fetchall():
                r = dict(zip(cols, row))
                if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
                    r["created_at"] = r["created_at"].isoformat()
                entries.append(r)
        return {"entries": entries}
    except Exception:
        return {"entries": []}


@router.get(
    "/plugins/capabilities",
    operation_id="plugins.capabilities",
    response_model=PluginCapabilitiesResponse,
    summary="Capabilities registered by installed utility plugins",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
    },
)
async def list_capabilities(_: None = Depends(requires("plugins.read"))):
    """Return registered capabilities from installed utility plugins."""
    return {"capabilities": sorted(_registered_capabilities)}


@router.get(
    "/plugins/catalog",
    operation_id="plugins.catalog",
    response_model=PluginCatalogResponse,
    response_model_exclude_none=True,
    summary="Full plugin catalog for the Marketplace page",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
    },
)
async def list_catalog(_: None = Depends(requires("plugins.read"))):
    """
    Full plugin catalog — official + installed + community, with installed flag.
    Used by the Marketplace page.

    Priority: installed/ and community/ win over official/ stubs for the same
    plugin slug — the installed copy has richer metadata and is the live version.
    Official stubs only appear in the catalog when the plugin is not installed.

    P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
    Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.
    """
    installed = _installed_slugs()
    registry = _load_registry_stats()
    seen: set[str] = set()
    plugins = []

    # Installed and community first — these are the live copies with full metadata.
    # Official stubs are fallback for plugins not yet installed.
    _source_for_dir = {
        INSTALLED_DIR: "installed",
        COMMUNITY_DIR: "community",
        OFFICIAL_DIR: "official",
        UTILITIES_DIR: "utility",
    }
    for base_dir in [INSTALLED_DIR, COMMUNITY_DIR, OFFICIAL_DIR, UTILITIES_DIR]:
        if base_dir.exists():
            for d in sorted(base_dir.iterdir()):
                if d.is_dir():
                    manifest = d / "plugin.yaml"
                    if manifest.exists() and d.name not in seen:
                        seen.add(d.name)
                        # P20b: skip unlisted plugins (unless operator has it installed)
                        stats = registry.get(d.name, {})
                        if not stats.get("listed", True) and d.name not in installed:
                            continue
                        with open(manifest) as f:
                            data = yaml.safe_load(f)
                        source = _source_for_dir.get(base_dir, "official")
                        entry = _plugin_entry(d, data, installed=d.name in installed, source=source)
                        # P20b: merge registry stats
                        entry["install_count"] = stats.get("install_count", 0)
                        entry["featured"] = stats.get("featured", False)
                        entry["pricing_model"] = stats.get("pricing_model")
                        plugins.append(entry)

    # P20b: sort — featured first, then by install_count desc, then alphabetically
    plugins.sort(key=lambda p: (
        0 if p.get("featured") else 1,
        -(p.get("install_count") or 0),
        (p.get("display_name") or p.get("id") or "").lower(),
    ))

    return {"plugins": plugins}


@router.get(
    "/plugins/{plugin_id}",
    operation_id="plugins.detail",
    response_model=PluginEntry,
    response_model_exclude_none=True,
    summary="Get a plugin's full manifest with module merges + predicate resolution",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def get_plugin(plugin_id: str, _: None = Depends(requires("plugins.read"))):
    """Get full plugin manifest, with enabled module manifests merged in.

    v0.8.6: also resolves P119 action predicates and P121 checklist
    predicates server-side so the frontend can render without further
    round trips.

    v0.9.0 (P204): includes `load_status` reflecting whether the
    plugin's api/routes.py loaded successfully at API startup. If false,
    `failure_reason` explains why (ModuleNotFoundError, SyntaxError, etc).
    """
    data = _load_plugin(plugin_id, installed_only=True)
    if not data:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    data = _merge_module_manifests(plugin_id, data)
    _resolve_plugin_predicates(plugin_id, data)

    # Attach load_status from the plugin loader's runtime tracking.
    try:
        from ..plugin_loader import LOAD_STATUS
        status = LOAD_STATUS.get(plugin_id)
        if status is not None:
            # Shape the response for the frontend: surface the class +
            # message but NOT the full traceback (that stays in app_logs
            # so only admins with log access see it).
            if status.get("routes_registered"):
                data["load_status"] = {"routes_registered": True}
            else:
                data["load_status"] = {
                    "routes_registered": False,
                    "stage": status.get("stage", "routes"),
                    "failure_reason": (
                        f"{status.get('exception_class', 'Error')}: "
                        f"{status.get('exception_message', '(no message)')}"
                    ),
                }
        else:
            # Plugin has no api/routes.py at all — routes_registered is
            # neither true nor false; omit the field so the frontend
            # treats it as "manifest-only plugin" (no banner).
            pass
    except Exception:
        # Never break the detail endpoint over observability plumbing.
        pass

    # B144 (v0.9.2.4): attach update status (cached). Trigger a refresh
    # if stale. Failures are non-fatal — the detail endpoint must keep
    # working even if the update checker has an off day.
    try:
        from ..plugin_update_checker import get_cached_status, is_stale, schedule_async_check
        cached = get_cached_status(plugin_id)
        if cached is None or is_stale(plugin_id):
            schedule_async_check(plugin_id)
        if cached:
            data["update_status"] = {
                "source_class": cached.source_class,
                "installed_version": cached.installed_version,
                "latest_version": cached.latest_version,
                "update_available": cached.update_available,
                "last_error": cached.last_error,
            }
        else:
            data["update_status"] = {
                "source_class": "pending",
                "installed_version": data.get("version"),
                "latest_version": None,
                "update_available": False,
                "last_error": None,
            }
    except Exception:
        pass

    # B151 (v0.9.4): surface frontend.components + trust state so the
    # install consent UI and the Plugins list don't each need a second fetch.
    # B304 (v0.10.0.5) + v0.10.0.5.1: also surface admin_proxy flag so the
    # install/Trust modal can render the admin-proxy consent line for
    # opted-in plugins.
    try:
        declared = _frontend_components_from_manifest(data)
        if declared:
            admin_proxy = bool((data.get("frontend") or {}).get("admin_proxy", False))
            trusted = _is_frontend_trusted(plugin_id)
            data["frontend"] = {
                "components": declared,
                "trusted": trusted,
                "needs_consent": not trusted,
                "admin_proxy": admin_proxy,
            }
    except Exception:
        pass

    return data


def _resolve_plugin_predicates(plugin_id: str, data: dict) -> None:
    """In-place augmentation: resolve every predicate referenced by the
    plugin's actions: / setup_checklist: blocks, and add a 'resolved' flag
    (for actions) or 'done' flag (for checklist items).

    Runs in a single DB-batch via plugin_predicates.resolve_all so we don't
    make N queries for N references to the same predicate.
    """
    from ..plugin_predicates import resolve_all

    # Collect every predicate name referenced anywhere in this manifest.
    names: list[str] = []
    for action in data.get("actions") or []:
        for k in ("disabled_when", "visible_when"):
            v = action.get(k) if isinstance(action, dict) else None
            if v:
                names.append(v)
    checklist = data.get("setup_checklist") or {}
    if isinstance(checklist, dict):
        for item in checklist.get("items") or []:
            v = item.get("done_if") if isinstance(item, dict) else None
            if v:
                names.append(v)
        # Ensure the predicate used by show_until='credentials_saved' is resolved
        # even if no item uses it directly.
        if checklist.get("show_until") == "credentials_saved":
            names.append("credentials_saved")

    resolved = resolve_all(plugin_id, names) if names else {}

    # Augment actions with `disabled` / `visible` booleans.
    for action in data.get("actions") or []:
        if not isinstance(action, dict):
            continue
        disabled_when = action.get("disabled_when")
        visible_when = action.get("visible_when")
        action["disabled"] = bool(resolved.get(disabled_when, False)) if disabled_when else False
        action["visible"] = bool(resolved.get(visible_when, True)) if visible_when else True

    # Augment checklist items with `done` booleans, plus top-level all_done / visible.
    if isinstance(checklist, dict) and isinstance(checklist.get("items"), list):
        items = checklist["items"]
        for item in items:
            if not isinstance(item, dict):
                continue
            pred = item.get("done_if")
            item["done"] = bool(resolved.get(pred, False)) if pred else False
        all_done = all(item.get("done", False) for item in items if isinstance(item, dict))
        show_until = checklist.get("show_until", "all_done")
        if show_until == "all_done":
            visible = not all_done
        elif show_until == "credentials_saved":
            visible = not bool(resolved.get("credentials_saved", False) or resolved.get("has_credentials", False))
        else:  # dismissed
            visible = True  # frontend tracks dismissal in localStorage
        checklist["all_done"] = all_done
        checklist["visible"] = visible


@router.get(
    "/plugins/{plugin_id}/dashboards/{dashboard_name}",
    operation_id="plugins.dashboard",
    response_model=PluginYamlResource,
    summary="Get a plugin dashboard spec (YAML, returned verbatim)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Dashboard not found in plugin or its enabled modules."},
    },
)
async def get_dashboard(
    plugin_id: str,
    dashboard_name: str,
    _: None = Depends(requires("plugins.read")),
):
    """Get a dashboard spec for rendering. Searches parent dashboards/ first, then enabled modules."""
    data = _load_yaml(plugin_id, f"dashboards/{dashboard_name}.yaml")
    if not data:
        # Search enabled modules
        for mod_name in _get_enabled_module_names(plugin_id):
            data = _load_yaml(plugin_id, f"modules/{mod_name}/dashboards/{dashboard_name}.yaml")
            if data:
                break
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard '{dashboard_name}' not found in plugin '{plugin_id}'",
        )
    return data


@router.get(
    "/plugins/{plugin_id}/datasets/{dataset_name}",
    operation_id="plugins.dataset",
    response_model=PluginYamlResource,
    summary="Get a plugin dataset schema (YAML, returned verbatim)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Dataset not found in plugin."},
    },
)
async def get_dataset(
    plugin_id: str,
    dataset_name: str,
    _: None = Depends(requires("plugins.read")),
):
    """Get a dataset schema."""
    data = _load_yaml(plugin_id, f"datasets/{dataset_name}.yaml")
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_name}' not found in plugin '{plugin_id}'",
        )
    return data


def refresh_capabilities() -> None:
    """Scan installed utility plugins and register their provided capabilities."""
    global _registered_capabilities
    caps: set[str] = set()
    if UTILITIES_DIR.exists():
        for d in UTILITIES_DIR.iterdir():
            if not d.is_dir():
                continue
            # Only count as installed if it exists in installed/ too
            installed_path = INSTALLED_DIR / d.name
            if not installed_path.exists():
                continue
            manifest_path = installed_path / "plugin.yaml"
            if not manifest_path.exists():
                manifest_path = d / "plugin.yaml"
            if manifest_path.exists():
                try:
                    data = yaml.safe_load(manifest_path.read_text())
                    for cap in data.get("provides", []):
                        caps.add(cap)
                except Exception:
                    pass
    _registered_capabilities = caps
    logger.info(f"Registered capabilities: {caps or 'none'}")


def has_capability(name: str) -> bool:
    """Check if a capability is provided by an installed utility plugin."""
    return name in _registered_capabilities


def _validate_requires(plugin_id: str, requires: dict) -> None:
    """
    Block install if the plugin's declared requirements cannot be met.
    Checks registered capabilities and postgres_version.
    Raises HTTP 422 with a clear message if any requirement fails.
    """
    if not requires:
        return

    unmet = []

    # Hardware requirements are validated by the install script, not the capability system
    INSTALL_SCRIPT_FIELDS = {"postgres", "postgres_version", "min_ram_mb", "min_disk_mb", "os"}

    for key in requires:
        if key in INSTALL_SCRIPT_FIELDS:
            continue
        if not has_capability(key):
            unmet.append(f"This plugin requires '{key}' which is not available. Install the corresponding utility plugin first.")

    pg_version_required = requires.get("postgres_version")
    if pg_version_required:
        try:
            from ..db import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT current_setting('server_version_num')::int")
                server_version_num = cur.fetchone()[0]
            # server_version_num is e.g. 160004 for 16.4; major = floor / 10000
            major = server_version_num // 10000
            required_major = int(str(pg_version_required).split(".")[0])
            if major < required_major:
                unmet.append(
                    f"PostgreSQL {required_major}+ is required but server is running {major}. "
                    "Upgrade your PostgreSQL installation."
                )
        except Exception:
            pass  # If we can't check, don't block install

    if unmet:
        raise HTTPException(
            422,
            detail={
                "error": f"Plugin '{plugin_id}' cannot be installed: requirements not met",
                "unmet_requirements": unmet,
            },
        )


@router.post(
    "/plugins/{plugin_id}/install/test",
    operation_id="plugins.install.test",
    response_model=InstallTestResponse,
    response_model_exclude_none=True,
    summary="Pre-install repo connectivity probe (clone + read manifest)",
    responses={
        400: {"model": ErrorDetail, "description": "repository_url required."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission, or SSH auth failed."},
        404: {"model": ErrorDetail, "description": "Repository not found."},
        502: {"model": ErrorDetail, "description": "Clone failed (network/repo error)."},
    },
)
async def test_install_connection(
    plugin_id: str,
    request: Request,
    body: PluginInstallRequest | None = None,
    _: None = Depends(requires("plugins.install")),
):
    """Test connectivity to a private repo before installing. Probe-clones and reads manifest."""
    import subprocess as sp
    import shutil

    _validate_plugin_id(plugin_id)

    repo_url = body.repository_url if body else None
    if not repo_url:
        raise HTTPException(400, "repository_url required for connection test")

    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="nousviz_test_")
    clone_env = os.environ.copy()

    if repo_url.startswith("git@"):
        ssh_host = repo_url.split("@")[1].split(":")[0] if ":" in repo_url else ""
        key_path = _get_deploy_key_path(ssh_host, repo_url=repo_url)
        if key_path:
            clone_env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
        else:
            clone_env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"

    result = sp.run(
        ["git", "clone", "--depth=1", repo_url, tmp_dir],
        capture_output=True, text=True, env=clone_env, timeout=30,
    )

    if result.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        error = result.stderr.strip()
        if "Permission denied" in error or "publickey" in error:
            raise HTTPException(403, "SSH authentication failed. The deploy key may not have access to this repository.")
        if "not found" in error.lower() or "does not exist" in error.lower():
            raise HTTPException(404, "Repository not found. Check the URL.")
        raise HTTPException(502, f"Clone failed: {error[:200]}")

    # Read manifest
    manifest_path = Path(tmp_dir) / "plugin.yaml"
    if not manifest_path.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(400, "Repository cloned but no plugin.yaml found at root.")

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f) or {}
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "ok": True,
        "message": f"Connected — {manifest.get('display_name', plugin_id)} v{manifest.get('version', '?')}",
        "display_name": manifest.get("display_name"),
        "version": manifest.get("version"),
    }


@router.post(
    "/plugins/{plugin_id}/install",
    operation_id="plugins.install",
    response_model=PluginInstallResponse,
    response_model_exclude_none=True,
    summary="Install a plugin",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
        429: {"model": ErrorDetail, "description": "Rate-limited (5 installs / 5 min per IP)."},
        503: {"model": ErrorDetail, "description": "nousviz_sdk not importable in the API runtime."},
    },
)
async def install_plugin(
    plugin_id: str,
    request: Request,
    body: PluginInstallRequest | None = None,
    _: None = Depends(requires("plugins.install")),
):
    """
    Install a plugin. Three-tier source resolution (P19):

    - Tier 1 (official): no repository_url — clones github.com/nousviz/plugin-{slug}
    - Tier 2 (community): no repository_url — reads URL from plugins/community/{slug}/plugin.yaml
    - Tier 3 (private): explicit repository_url in request body

    Idempotent if already installed. Restart the API after installing to activate routes.

    Security (P22):
    - Rate limited: 5 installs per 5 minutes per IP (G3)
    - Git clone pins to declared version tag (G2) — refuses HEAD installs
    - pip runs with a sanitised environment — no NOUSVIZ_* vars exposed (G5)
    - repository_url validated against SSRF blocklist (P19)
    """
    admin = get_me(request)
    actor_user_id = str(admin.get("id")) if admin.get("id") else None
    _validate_plugin_id(plugin_id)
    import shutil
    import subprocess as sp

    # P205 (v0.9.0): install gate. Refuse to install a plugin when the
    # SDK isn't importable in the API runtime — the plugin's routes
    # would silently 404 after install otherwise. Clear 503 with
    # remediation beats opaque "my plugin doesn't work."
    try:
        from ..main import SDK_AVAILABLE, SDK_IMPORT_ERROR
        if not SDK_AVAILABLE:
            raise HTTPException(
                503,
                f"Cannot install plugin: nousviz_sdk is not importable in the API runtime. "
                f"Error: {(SDK_IMPORT_ERROR or 'unknown')[:200]}. "
                f"Run `pip install -e sdk/` in the API venv and restart the API, "
                f"then retry the install."
            )
    except ImportError:
        pass  # main module not importable in this weird context — don't block

    # Validate repository_url BEFORE rate-limiting — bad URLs are rejected cheaply
    explicit_repo_url: str | None = None
    if body and body.repository_url:
        explicit_repo_url = _validate_repo_url(body.repository_url)

    # P22-G3: rate limit (after URL validation so bad URLs don't consume quota)
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    _check_install_rate(client_ip)

    official_src = OFFICIAL_DIR / plugin_id
    community_src = COMMUNITY_DIR / plugin_id
    utility_src = UTILITIES_DIR / plugin_id
    installed_dest = INSTALLED_DIR / plugin_id

    if installed_dest.exists() and (installed_dest / "plugin.yaml").exists():
        with open(installed_dest / "plugin.yaml") as f:
            meta = yaml.safe_load(f)
        return {"status": "already_installed", "plugin": meta}

    installed_dest.parent.mkdir(parents=True, exist_ok=True)

    # ── Resolve source manifest and URL (P19 three-tier) ─────────────

    # Load the stub manifest (version + requires + optional repository_url)
    stub_meta: dict = {}
    if utility_src.exists() and (utility_src / "plugin.yaml").exists():
        with open(utility_src / "plugin.yaml") as f:
            stub_meta = yaml.safe_load(f) or {}
    elif official_src.exists() and (official_src / "plugin.yaml").exists():
        with open(official_src / "plugin.yaml") as f:
            stub_meta = yaml.safe_load(f) or {}
    elif community_src.exists() and (community_src / "plugin.yaml").exists():
        with open(community_src / "plugin.yaml") as f:
            stub_meta = yaml.safe_load(f) or {}
        # Tier 2: community manifest must declare repository_url
        if not explicit_repo_url and not stub_meta.get("repository_url"):
            raise HTTPException(
                400,
                f"Community plugin '{plugin_id}' manifest is missing repository_url. "
                "The manifest in plugins/community/ must declare where to clone from.",
            )
        if not explicit_repo_url:
            explicit_repo_url = _validate_repo_url(stub_meta["repository_url"])
    elif not explicit_repo_url:
        # Neither official nor community stub — require explicit URL
        raise HTTPException(
            404,
            f"Plugin '{plugin_id}' not found in official or community registry. "
            "Provide a repository_url in the request body to install a private plugin.",
        )

    # P17: validate requires: before downloading anything
    _validate_requires(plugin_id, stub_meta.get("requires", {}))

    # Check for utility plugin (always local, never cloned from remote)
    utility_has_code = (
        utility_src.exists()
        and (utility_src / "plugin.yaml").exists()
    )

    # Check for local dev copy (official stub with code beyond plugin.yaml)
    official_has_code = (
        not utility_has_code
        and official_src.exists()
        and (official_src / "plugin.yaml").exists()
        and any(p for p in official_src.iterdir() if p.name != "plugin.yaml")
    )

    clone_urls: list[str] = []

    if utility_has_code:
        shutil.copytree(str(utility_src), str(installed_dest))
    elif official_has_code:
        shutil.copytree(str(official_src), str(installed_dest))
    else:
        declared_version: str | None = stub_meta.get("version")

        # For private plugins with explicit URL but no local stub,
        # do a shallow clone to read the manifest and get the version.
        if not declared_version and explicit_repo_url:
            import tempfile
            tmp_dir = tempfile.mkdtemp(prefix="nousviz_probe_")
            probe_env = os.environ.copy()
            if explicit_repo_url.startswith("git@"):
                ssh_host = explicit_repo_url.split("@")[1].split(":")[0] if ":" in explicit_repo_url else ""
                key_path = _get_deploy_key_path(ssh_host, repo_url=explicit_repo_url)
                if key_path:
                    probe_env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
            # Always allow StrictHostKeyChecking=no for probe clone
            if "GIT_SSH_COMMAND" not in probe_env:
                probe_env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
            logger.info(f"Probe clone: {explicit_repo_url} → {tmp_dir}")
            probe_result = sp.run(
                ["git", "clone", "--depth=1", explicit_repo_url, tmp_dir],
                capture_output=True, text=True, env=probe_env, timeout=30,
            )
            if probe_result.returncode != 0:
                logger.warning(f"Probe clone failed: {probe_result.stderr.strip()}")
            if probe_result.returncode == 0:
                probe_manifest = Path(tmp_dir) / "plugin.yaml"
                if probe_manifest.exists():
                    with open(probe_manifest) as f:
                        probe_meta = yaml.safe_load(f) or {}
                    declared_version = probe_meta.get("version")
                    # Also use probe manifest for requires validation if stub was empty
                    if not stub_meta:
                        stub_meta = probe_meta
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if not declared_version:
            raise HTTPException(
                400,
                f"Cannot install '{plugin_id}': no version declared in manifest. "
                "A pinned version tag is required for security.",
            )

        tag = f"v{declared_version}"

        # Determine clone URL
        if explicit_repo_url:
            clone_urls = [explicit_repo_url]
        else:
            # Tier 1: infer from official slug convention
            clone_urls = [
                f"git@github.com:nousviz/plugin-{plugin_id}.git",
                f"https://github.com/nousviz/plugin-{plugin_id}.git",
            ]

        # Clone pinned to declared version tag (no HEAD installs)
        # For SSH URLs, use deploy key if available, fall back to system SSH
        clone_env = os.environ.copy()
        last_stderr = ""
        for repo_url in clone_urls:
            if repo_url.startswith("git@"):
                ssh_host = repo_url.split("@")[1].split(":")[0] if ":" in repo_url else ""
                key_path = _get_deploy_key_path(ssh_host, repo_url=repo_url)
                logger.info(f"Clone {repo_url} at {tag}: deploy_key={'found' if key_path else 'none'}")
                if key_path:
                    clone_env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
                elif "GIT_SSH_COMMAND" not in clone_env:
                    clone_env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
            result = sp.run(
                ["git", "clone", "--depth=1", "--branch", tag, repo_url, str(installed_dest)],
                capture_output=True, text=True, env=clone_env,
            )
            if result.returncode == 0:
                break
            last_stderr = result.stderr.strip()
            logger.warning(f"Clone failed for {repo_url}: {last_stderr}")
        else:
            # B203: surface to /system/logs so operators can see clone failures.
            try:
                from ..log_events import log_plugin_event
                log_plugin_event(
                    "error",
                    plugin_id,
                    "clone",
                    f"Could not clone any URL for tag {tag}. Last stderr: {last_stderr[:300]}",
                    detail={"tag": tag, "tried_urls": clone_urls},
                    source="plugin_install",
                    actor_user_id=actor_user_id,
                )
            except Exception:
                pass
            raise HTTPException(
                404,
                f"Plugin '{plugin_id}' not found at tag '{tag}'. "
                "Ensure the plugin repo exists and the version tag is published.",
            )

    manifest = installed_dest / "plugin.yaml"
    if not manifest.exists():
        shutil.rmtree(installed_dest)
        raise HTTPException(500, f"Plugin '{plugin_id}' installed but plugin.yaml missing — invalid package")

    with open(manifest) as f:
        meta = yaml.safe_load(f)

    # v0.8.6: validate manifest extensions (hooks, actions, setup_checklist, new field types).
    # Reject the install if the manifest has malformed blocks — gives plugin
    # authors a clear error rather than silent breakage in the UI later.
    try:
        from ..plugin_validation import validate_manifest_extensions, ManifestValidationError
        validate_manifest_extensions(plugin_id, meta or {})
    except ManifestValidationError as _val_err:
        shutil.rmtree(installed_dest)
        raise HTTPException(400, f"Plugin manifest invalid: {_val_err}")

    # P22-G2b + P20a: record install in plugin_registry — commit SHA + install count
    try:
        sha_result = sp.run(
            ["git", "-C", str(installed_dest), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        installed_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO plugin_registry (
                    slug, name, display_name,
                    installed_commit_sha, installed_at, installed_from_url,
                    install_count, version, category
                )
                VALUES (%s, %s, %s, %s, NOW(), %s, 1, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    installed_commit_sha = EXCLUDED.installed_commit_sha,
                    installed_at = EXCLUDED.installed_at,
                    installed_from_url = EXCLUDED.installed_from_url,
                    install_count = plugin_registry.install_count + 1,
                    version = EXCLUDED.version,
                    category = EXCLUDED.category
            """, (
                plugin_id,
                meta.get("name", plugin_id),
                meta.get("display_name", plugin_id),
                installed_sha,
                explicit_repo_url or (clone_urls[0] if not official_has_code else None),
                meta.get("version", "1.0.0"),
                meta.get("category", "analytics"),
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Plugin {plugin_id}: could not record install in registry — {e}")

    # Install Python deps if present.
    # P22-G5: strip NOUSVIZ_* environment variables so the subprocess cannot
    # read the encryption key, database credentials, or API tokens.
    req_file = installed_dest / "requirements.txt"
    if req_file.exists():
        venv_python = REPO_ROOT / ".venv" / "bin" / "python3"
        python_bin = str(venv_python) if venv_python.exists() else "python3"
        safe_env = {k: v for k, v in os.environ.items() if not k.startswith("NOUSVIZ_")}
        sp.run(
            [python_bin, "-m", "pip", "install", "-q", "-r", str(req_file)],
            capture_output=True,
            env=safe_env,
        )

    # Run SQL migrations (idempotent — skips already-applied files)
    migrations_applied = []
    try:
        migrations_applied = _run_plugin_migrations(plugin_id, installed_dest)
    except Exception as e:
        logger.warning(f"Plugin {plugin_id}: migrations failed — {e}")
        # B203: install-time migration failures matter for diagnosis.
        try:
            from ..log_events import log_plugin_event
            log_plugin_event(
                "error",
                plugin_id,
                "migrate",
                f"migrations failed: {str(e)[:300]}",
                source="plugin_install",
                actor_user_id=actor_user_id,
            )
        except Exception:
            pass

    # P203 (v0.9.0): grant nousviz_plugin role CRUD on this plugin's
    # declared tables. Runs AFTER migrations so the tables exist.
    # Idempotent — re-granting on an already-granted table is a no-op.
    try:
        from ..plugin_grants import grant_plugin_tables
        grant_plugin_tables(plugin_id, meta or {})
    except Exception as _grant_err:
        logger.warning(f"Plugin {plugin_id}: grant nousviz_plugin failed — {_grant_err}")

    # B125 (v0.8.6.2): auto-enable modules that declare `enabled_by_default: true`.
    # Seeds plugin_modules rows on install (previously only happened when an
    # operator clicked "Enable" in the UI — so multi-module plugins looked
    # broken on first load even though enable_by_default was declared).
    # Also runs each auto-enabled module's migrations.
    try:
        declared_modules = meta.get("modules") or []
        for mod_name in declared_modules:
            if not isinstance(mod_name, str):
                continue
            mod_yaml = installed_dest / "modules" / mod_name / "module.yaml"
            if not mod_yaml.exists():
                continue
            try:
                mod_meta = yaml.safe_load(mod_yaml.read_text()) or {}
            except Exception as _e:
                logger.warning(f"Plugin {plugin_id}: could not parse module.yaml for {mod_name}: {_e}")
                continue
            # Default is True when unspecified — matches _get_enabled_module_names's
            # fallback behavior so we don't accidentally flip semantics.
            enabled = bool(mod_meta.get("enabled_by_default", True))
            try:
                with get_pg_conn() as _c:
                    _cur = _c.cursor()
                    _cur.execute(
                        """
                        INSERT INTO plugin_modules (plugin_id, module_name, enabled)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (plugin_id, module_name) DO UPDATE SET enabled = EXCLUDED.enabled
                        """,
                        (plugin_id, mod_name, enabled),
                    )
            except Exception as _e:
                logger.warning(f"Plugin {plugin_id}: could not seed plugin_modules row for {mod_name}: {_e}")
                continue
            # Run module migrations only for auto-enabled modules. Disabled
            # modules get their migrations when an operator turns them on.
            if enabled:
                mod_migrations_dir = installed_dest / "modules" / mod_name / "storage" / "migrations"
                if mod_migrations_dir.exists():
                    for sql_file in sorted(mod_migrations_dir.glob("*_up.sql")) + sorted(mod_migrations_dir.glob("[0-9]*.sql")):
                        if sql_file.name.endswith("_down.sql"):
                            continue
                        try:
                            with get_pg_conn() as _c:
                                _cur = _c.cursor()
                                _cur.execute(sql_file.read_text())
                            logger.info(f"Plugin {plugin_id}/{mod_name}: ran migration {sql_file.name}")
                        except Exception as _e:
                            logger.warning(f"Plugin {plugin_id}/{mod_name}: migration {sql_file.name} failed: {_e}")
    except Exception as _e:
        logger.warning(f"Plugin {plugin_id}: module auto-enable step failed: {_e}")

    # B141 (v0.9.2.1): second-pass grant after module migrations.
    # The first grant pass above ran BEFORE module migrations created
    # their tables, so any module-owned table was logged as "not yet created"
    # and skipped. Re-run grants now that all tables exist. Idempotent —
    # GRANT on already-granted tables is a Postgres no-op.
    try:
        from ..plugin_grants import grant_plugin_tables as _grant_after_modules
        _grant_after_modules(plugin_id, meta or {})
    except Exception as _grant_err:
        logger.warning(f"Plugin {plugin_id}: post-module grant failed — {_grant_err}")

    # Run install hook if declared (utility plugins use this to download binaries, start services)
    install_hook = meta.get("install_hook")
    hook_result = None
    if install_hook:
        hook_script = installed_dest / install_hook
        if hook_script.exists():
            try:
                logger.info(f"Plugin {plugin_id}: running install hook {install_hook}")
                import subprocess as _sp
                # S107: strip NOUSVIZ_* and other secrets from hook env
                from ..plugin_subprocess import plugin_hook_env
                result = _sp.run(
                    ["bash", str(hook_script)],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(REPO_ROOT),
                    env=plugin_hook_env(extra={"NOUSVIZ_DIR": str(REPO_ROOT)}),
                )
                hook_result = result.stdout[-500:] if result.stdout else None
                if result.returncode != 0:
                    logger.error(f"Plugin {plugin_id}: install hook failed: {result.stderr[-500:]}")
                    # B203: surface install-hook failures to /system/logs.
                    try:
                        from ..log_events import log_plugin_event
                        log_plugin_event(
                            "error",
                            plugin_id,
                            "hook_install",
                            f"install_hook returned rc={result.returncode}",
                            detail={"stderr": (result.stderr or "")[-500:], "hook": install_hook},
                            source="plugin_install",
                            actor_user_id=actor_user_id,
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Plugin {plugin_id}: install hook error: {e}")
                try:
                    from ..log_events import log_plugin_event
                    log_plugin_event(
                        "error",
                        plugin_id,
                        "hook_install",
                        f"install_hook subprocess error: {str(e)[:300]}",
                        detail={"hook": install_hook},
                        source="plugin_install",
                        actor_user_id=actor_user_id,
                    )
                except Exception:
                    pass

    # P118: fire declarative on_install hook (Python-side, runs async in jobs-worker).
    # Coexists with the bash install_hook above — bash runs synchronously here,
    # Python hook is enqueued and picked up by the worker.
    try:
        from ..plugin_hooks import fire_hook
        fire_hook(plugin_id, "on_install", payload={})
    except Exception as _hook_err:
        logger.warning(f"Plugin {plugin_id}: on_install hook enqueue failed: {_hook_err}")

    # Refresh capability registry after utility plugin install
    refresh_capabilities()

    # Auto-create default connection for utility plugins with provides
    is_utility = meta.get("type") == "utility"
    if is_utility and meta.get("provides"):
        try:
            import json as _j
            for capability in meta["provides"]:
                conn_type = capability  # mysql, clickhouse, etc.
                if conn_type not in ("mysql", "clickhouse", "postgres"):
                    continue
                with get_pg_conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM connections WHERE type = %s AND is_default = true", (conn_type,))
                    if not cur.fetchone():
                        # Read default config from connections field in manifest
                        defaults = {}
                        for c in (meta.get("connections") or []):
                            for field in (c.get("fields") or []):
                                if field.get("default"):
                                    defaults[field["name"]] = str(field["default"])
                        display = meta.get("display_name", conn_type.title())
                        cur.execute(
                            "INSERT INTO connections (name, type, config, is_default) VALUES (%s, %s, %s, true)",
                            (f"{display} (Default)", conn_type, _j.dumps(defaults)),
                        )
                        logger.info(f"Auto-created default {conn_type} connection")
        except Exception as e:
            logger.warning(f"Could not auto-create connection: {e}")
            # B203
            try:
                from ..log_events import log_plugin_event
                log_plugin_event(
                    "warning",
                    plugin_id,
                    "auto_connection",
                    f"could not auto-create default connection: {str(e)[:300]}",
                    source="plugin_install",
                    actor_user_id=actor_user_id,
                )
            except Exception:
                pass

    # Hot-reload plugin routes without restart
    routes_loaded = False
    routes_file = installed_dest / "api" / "routes.py"
    if routes_file.exists():
        try:
            from ..plugin_loader import load_plugin_routes
            load_plugin_routes(request.app)
            routes_loaded = True
        except Exception as e:
            logger.warning(f"Plugin {plugin_id}: hot-reload failed — {e}")
            # B203: hot-reload failures mean operator's plugin endpoints
            # won't work until a restart. Surface this loudly.
            try:
                from ..log_events import log_plugin_event
                log_plugin_event(
                    "error",
                    plugin_id,
                    "hot_reload",
                    f"route hot-reload failed; restart required: {str(e)[:300]}",
                    source="plugin_install",
                    actor_user_id=actor_user_id,
                )
            except Exception:
                pass

    from .activity import record_activity
    record_activity(
        action="plugin_install",
        plugin_id=plugin_id,
        detail={"version": meta.get("version"), "display_name": meta.get("display_name", plugin_id)},
        ip=client_ip,
    )
    _log_plugin_action(plugin_id, "install", {"version": meta.get("version")}, ip=client_ip)

    return {
        "status": "installed",
        "plugin": meta,
        "migrations_applied": migrations_applied,
        "routes_active": routes_loaded,
    }


def _purge_plugin_db_rows(plugin_id: str) -> dict[str, int]:
    """B163 (v0.9.4.11): delete all DB rows that belonged to a plugin.

    Pre-v0.9.4.11, uninstall removed the on-disk plugin directory + ran
    down-migrations + revoked grants — but never cleaned up these tables:

      connections WHERE name = 'plugin:<slug>'  (cascades to credentials
                                                  and credential_audit_log)
      plugin_settings WHERE plugin_id = <slug>  (_trust_frontend, _conn.*,
                                                  _sync_schedule.*, declared)
      plugin_registry WHERE slug = <slug>       (note: column is `slug`)
      plugin_update_status WHERE plugin_id = <slug>
      sync_schedule_registry WHERE plugin_id = <slug>

    The result was orphaned encrypted credentials in the DB and silent
    inheritance of trust consent + settings on reinstall — defeating
    operator-consent intent.

    This helper does the cleanup in one transaction. Each individual
    DELETE is wrapped in a savepoint so a missing table on an old install
    (e.g. pre-v0.9.3 instances without sync_schedule_registry) logs a
    warning and continues with the others; the rmtree of the plugin dir
    is the load-bearing cleanup.

    Returns row counts per table for the activity log.

    plugin_audit_log is intentionally preserved — operators need to see
    install/uninstall history for forensics even after the plugin is gone.
    """
    counts: dict[str, int] = {
        "connections": 0,
        "plugin_settings": 0,
        "plugin_registry": 0,
        "plugin_update_status": 0,
        "sync_schedule_registry": 0,
    }
    deletes = [
        # connections cascade-deletes credentials + credential_audit_log
        # rows for this plugin via ON DELETE CASCADE (migration 046).
        ("connections", "DELETE FROM connections WHERE name = %s", (f"plugin:{plugin_id}",)),
        ("plugin_settings", "DELETE FROM plugin_settings WHERE plugin_id = %s", (plugin_id,)),
        # plugin_registry uses `slug`, not `plugin_id`.
        ("plugin_registry", "DELETE FROM plugin_registry WHERE slug = %s", (plugin_id,)),
        ("plugin_update_status", "DELETE FROM plugin_update_status WHERE plugin_id = %s", (plugin_id,)),
        ("sync_schedule_registry", "DELETE FROM sync_schedule_registry WHERE plugin_id = %s", (plugin_id,)),
    ]
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            for table, sql, params in deletes:
                try:
                    cur.execute(f"SAVEPOINT purge_{table}")
                    cur.execute(sql, params)
                    counts[table] = cur.rowcount or 0
                    cur.execute(f"RELEASE SAVEPOINT purge_{table}")
                except Exception as exc:
                    cur.execute(f"ROLLBACK TO SAVEPOINT purge_{table}")
                    logger.warning(
                        f"Plugin {plugin_id}: purge of {table} skipped — {exc}"
                    )
    except Exception as exc:
        logger.warning(f"Plugin {plugin_id}: _purge_plugin_db_rows failed — {exc}")
    return counts


def _find_dependents(plugin_id: str) -> list[dict]:
    """Return all installed plugins that depend on plugin_id.

    Two sources:
    1. `depends_on: [{plugin: slug}]` — explicit plugin-to-plugin dependency
    2. `requires.{capability}: true` where `capability` is in plugin_id's `provides[]`
       (utility-to-plugin dependency: uninstalling the utility would break them)
    """
    target_manifest = _load_plugin(plugin_id) or {}
    provided_capabilities = set(target_manifest.get("provides", []) or [])

    dependents = []
    for slug in _installed_slugs():
        if slug == plugin_id:
            continue
        manifest = _load_plugin(slug)
        if not manifest:
            continue

        # Explicit depends_on
        for dep in manifest.get("depends_on", []):
            if dep.get("plugin") == plugin_id:
                dependents.append({
                    "plugin": slug,
                    "display_name": manifest.get("display_name", slug),
                    "reason": dep.get("reason", "") or f"depends on {plugin_id}",
                })
                break  # one entry per dependent
        else:
            # Capability-based (utility providing something this plugin requires)
            if provided_capabilities:
                requires = manifest.get("requires", {}) or {}
                for cap, needed in requires.items():
                    if needed and cap in provided_capabilities:
                        dependents.append({
                            "plugin": slug,
                            "display_name": manifest.get("display_name", slug),
                            "reason": f"requires.{cap}",
                        })
                        break
    return dependents


def _cleanup_plugin_references(plugin_id: str) -> dict:
    """B281 (v0.9.11.21): auto-clean orphan references on uninstall when
    the operator opts in via ?remove_references=true.

    Re-runs `_find_references` (can't trust client-supplied list — the
    operator could craft a request) and performs a per-kind cleanup
    inside try/except so one failure doesn't abort the rest:

      annotation → DELETE FROM annotations WHERE id = %s
      share      → DELETE FROM shared_links WHERE id = %s
      fusion     → fusions.requires JSONB array, strip the plugin slug
                   (fusion itself preserved so the operator can repoint
                    widgets later — they'd lose work otherwise)
      alert      → left alone (Phase 2: needs richer deactivate UX)

    Returns a structured outcome dict that gets merged into both the
    API response (for the post-uninstall summary) and the audit log
    (for the trail).
    """
    outcome: dict = {
        "annotations_deleted": [],
        "shares_deleted": [],
        "fusions_repointed": [],
        "alerts_left_alone": [],
        "failed": [],
    }
    refs = _find_references(plugin_id)
    if not refs:
        return outcome

    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()

            for ref in refs:
                kind = ref.get("kind")
                rid = ref.get("id")
                display = ref.get("display_name")
                try:
                    if kind == "annotation":
                        cur.execute(
                            "DELETE FROM annotations WHERE id = %s",
                            (rid,),
                        )
                        if cur.rowcount > 0:
                            outcome["annotations_deleted"].append({
                                "id": str(rid), "title": display,
                            })
                    elif kind == "share":
                        cur.execute(
                            "DELETE FROM shared_links WHERE id = %s",
                            (rid,),
                        )
                        if cur.rowcount > 0:
                            outcome["shares_deleted"].append({
                                "id": str(rid), "label": display,
                            })
                    elif kind == "fusion":
                        # Strip the plugin slug from `requires` JSONB array.
                        # `requires` is `JSONB[]` of plugin slugs; we filter
                        # out the slug being uninstalled and write back.
                        cur.execute(
                            """
                            UPDATE fusions
                            SET requires = COALESCE(
                                (
                                    SELECT jsonb_agg(elem)
                                    FROM jsonb_array_elements(requires) AS elem
                                    WHERE elem != to_jsonb(%s::text)
                                ),
                                '[]'::jsonb
                            )
                            WHERE id = %s
                            """,
                            (plugin_id, rid),
                        )
                        if cur.rowcount > 0:
                            outcome["fusions_repointed"].append({
                                "id": str(rid), "name": display,
                            })
                    elif kind == "alert":
                        # Phase 1: documented decision is to leave alert
                        # rules in place. Operator can pause/edit them
                        # explicitly via the alerts UI.
                        outcome["alerts_left_alone"].append({
                            "id": str(rid), "name": display,
                        })
                    else:
                        outcome["failed"].append({
                            "kind": kind, "id": str(rid),
                            "error": f"unknown reference kind: {kind!r}",
                        })
                except Exception as e:
                    outcome["failed"].append({
                        "kind": kind,
                        "id": str(rid),
                        "error": f"{e.__class__.__name__}: {str(e)[:200]}",
                    })

            conn.commit()
    except Exception as e:
        # Outer connection failure — record once and return the partial
        # outcome so the caller can still render what was attempted.
        outcome["failed"].append({
            "kind": "*",
            "id": "",
            "error": f"connection failure: {e.__class__.__name__}",
        })
        logger.warning(f"Plugin {plugin_id}: reference cleanup failed: {e}")

    return outcome


def _find_references(plugin_id: str) -> list[dict]:
    """Return operator-created artefacts (fusions, alerts, annotations, shares)
    that reference this plugin. Unlike `_find_dependents`, these are NOT auto-cleaned
    on uninstall — they become orphans that need manual cleanup.

    Each entry: {kind, id, display_name, reason}
    """
    references: list[dict] = []
    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # Fusions — `requires` is a JSONB array of plugin slugs
            try:
                cur.execute(
                    "SELECT id, name FROM fusions WHERE requires @> to_jsonb(ARRAY[%s::text])",
                    (plugin_id,),
                )
                for row in cur.fetchall():
                    references.append({
                        "kind": "fusion",
                        "id": row[0],
                        "display_name": row[1],
                        "reason": f"fusion requires {plugin_id}",
                    })
            except Exception:
                pass

            # Alert rules — plugin_id column
            try:
                cur.execute(
                    "SELECT id, name FROM alert_rules WHERE plugin_id = %s",
                    (plugin_id,),
                )
                for row in cur.fetchall():
                    references.append({
                        "kind": "alert",
                        "id": row[0],
                        "display_name": row[1],
                        "reason": f"alert rule on {plugin_id}",
                    })
            except Exception:
                pass

            # Annotations — plugin_id column
            try:
                cur.execute(
                    "SELECT id, COALESCE(title, 'Annotation #' || id::text) FROM annotations WHERE plugin_id = %s",
                    (plugin_id,),
                )
                for row in cur.fetchall():
                    references.append({
                        "kind": "annotation",
                        "id": row[0],
                        "display_name": row[1],
                        "reason": f"annotation pinned to {plugin_id}",
                    })
            except Exception:
                pass

            # Shared links — page_path starts with /plugin/{slug}/
            try:
                cur.execute(
                    "SELECT id, COALESCE(label, page_path) FROM shared_links WHERE page_path LIKE %s",
                    (f"/plugin/{plugin_id}/%",),
                )
                for row in cur.fetchall():
                    references.append({
                        "kind": "share",
                        "id": row[0],
                        "display_name": row[1],
                        "reason": f"shared link to {plugin_id}",
                    })
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Plugin {plugin_id}: reference scan failed: {e}")
    return references


def _migration_skip_is_safe(cur, plugin_id: str, declared_tables: list[str]) -> bool:
    """B285: return True if it's safe to honor a schema_migrations row's
    "already applied" claim — i.e. every declared table actually exists
    in the public schema.

    Empty declared_tables ⇒ True (utility plugin or manifest with no
    declared tables; no integrity check possible, trust the tracking row
    as before B285).

    pg_class query failure ⇒ True (defensive default: preserve current
    behavior on uncertainty rather than risk re-running unsafe migrations).
    The warning is logged so an operator can investigate.

    relkind filter accepts ordinary tables ('r') and partitioned tables
    ('p'); foreign tables ('f') and views ('v') deliberately excluded —
    a plugin's manifest declares concrete tables, not derived objects.
    """
    if not declared_tables:
        return True
    try:
        cur.execute(
            "SELECT count(*) FROM pg_class "
            "WHERE relkind IN ('r','p') AND relname = ANY(%s)",
            (declared_tables,),
        )
        existing = cur.fetchone()[0]
        return existing >= len(declared_tables)
    except Exception as exc:
        logger.warning(
            f"Plugin {plugin_id}: migration integrity check (pg_class lookup) "
            f"failed, defaulting to honor schema_migrations — {exc}"
        )
        return True


def _run_plugin_migrations(plugin_id: str, installed_dest: Path) -> list[str]:
    """Run up migrations for a plugin in lexicographic order.
    Skips files already recorded in schema_migrations (idempotent).
    Returns list of migration filenames that were applied.

    B285 integrity check: when a schema_migrations row says "applied," verify
    the manifest's declared tables actually exist via pg_class before honoring
    the skip. If any declared table is missing, delete the stale row and
    re-run the migration. Defense-in-depth against any path that drops tables
    out-of-band (B278's _drop_declared_tables before B285's symmetry fix,
    manual psql cleanup, partial restore-from-snapshot, future operator
    tooling). Without this, install/Update silently returns 200 against a
    state where tables don't exist — sync then fails with UndefinedTable.
    """
    from ..db import get_pg_conn

    migrations_dir = installed_dest / "storage" / "migrations"
    if not migrations_dir.exists():
        return []

    # B299: forward migrations must match <NNN>_<name>.sql per the
    # load-bearing naming convention in
    # nousviz-plugin-authoring/docs/02-plugin-contract.md. Pre-B299 the
    # glob was *.sql with `endswith("_down.sql")` exclusion only, which
    # silently mis-classified bare-name files (e.g. down.sql) as forward
    # migrations and ran them — for a file containing DROPs that meant
    # tables were destroyed milliseconds after CREATE.
    up_files = sorted([
        f for f in migrations_dir.glob("[0-9]*.sql")
        if not f.name.endswith("_down.sql")
    ])

    # B299: warn on any *.sql in the dir that the new glob filtered out
    # (and isn't a *_down.sql). Surfaces contract deviations in API logs
    # at install time rather than as silent skips.
    all_sql = set(migrations_dir.glob("*.sql"))
    recognized = set(up_files) | set(migrations_dir.glob("*_down.sql"))
    for ignored in sorted(all_sql - recognized):
        logger.warning(
            f"Plugin {plugin_id}: ignoring migration file "
            f"'{ignored.name}' — does not match <NNN>_<name>.sql "
            f"convention; will not be executed"
        )

    if not up_files:
        return []

    # B285: load manifest's declared tables once. Empty list ⇒ utility plugin
    # path — integrity check no-ops and we trust schema_migrations as before
    # (no regression for plugins that don't declare tables).
    declared_tables: list[str] = []
    manifest_path = installed_dest / "plugin.yaml"
    if manifest_path.exists():
        try:
            with open(manifest_path) as fh:
                manifest = yaml.safe_load(fh) or {}
            raw_tables = (
                manifest.get("databases", {})
                        .get("postgres", {})
                        .get("tables", []) or []
            )
            declared_tables = [
                t for t in raw_tables
                if isinstance(t, str) and _VALID_TABLE_NAME_B278.match(t)
            ]
        except Exception as exc:
            logger.warning(
                f"Plugin {plugin_id}: could not parse manifest for migration "
                f"integrity check, skipping check — {exc}"
            )

    applied = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # Ensure tracking table exists (may not if setup.sh hasn't run migration 016)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        conn.commit()
        for f in up_files:
            filename = f"{plugin_id}/{f.name}"
            cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
            if cur.fetchone():
                # B285: tracking row exists. Honor the skip ONLY if the
                # declared tables actually exist in pg_class. Otherwise
                # the row is stale (tables dropped out-of-band) and the
                # migration must re-run.
                if _migration_skip_is_safe(cur, plugin_id, declared_tables):
                    continue
                logger.warning(
                    f"Plugin {plugin_id}: schema_migrations claims {filename} "
                    f"applied but declared tables are missing; deleting stale "
                    f"row and re-running migration"
                )
                cur.execute(
                    "DELETE FROM schema_migrations WHERE filename = %s",
                    (filename,),
                )
                conn.commit()
                # Fall through to re-run the migration below
            cur.execute(f.read_text())
            cur.execute(
                "INSERT INTO schema_migrations (filename, applied_at) VALUES (%s, NOW())",
                (filename,),
            )
            conn.commit()
            applied.append(f.name)

    # B294 (v0.10.0.3): grant SELECT on plugin tables to the read-only
    # query role unconditionally — every install + Update self-heals,
    # not just when fresh migrations applied. Closes the gap where
    # Update on a plugin with stale tracking rows (B285) skipped the
    # grant block. Identifier-safe via psycopg2.sql.Identifier; the
    # previous f-string interpolation is gone.
    try:
        from ..services.plugin_grants import ensure_plugin_query_grants
        granted = ensure_plugin_query_grants(plugin_id)
        if granted:
            logger.info(
                f"Plugin {plugin_id}: granted SELECT on {granted} to nousviz_query"
            )
    except Exception as e:
        logger.warning(
            f"Plugin {plugin_id}: could not grant SELECT to query role — {e}"
        )

    return applied


def _run_down_migrations(plugin_id: str) -> list[str]:
    """Run down migrations for a plugin in reverse lexicographic order.
    Returns list of migration filenames that were executed."""
    from ..db import get_pg_conn

    plugin_dir = INSTALLED_DIR / plugin_id
    migrations_dir = plugin_dir / "storage" / "migrations"
    if not migrations_dir.exists():
        return []

    down_files = sorted(
        [f for f in migrations_dir.glob("*_down.sql")],
        reverse=True,
    )
    if not down_files:
        return []

    executed = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        for f in down_files:
            cur.execute(f.read_text())
            conn.commit()
            # Remove migration tracking record — up file is named without _down suffix
            up_name = f.name.replace("_down.sql", ".sql")
            filename = f"{plugin_id}/{up_name}"
            cur.execute(
                "DELETE FROM schema_migrations WHERE filename = %s",
                (filename,),
            )
            conn.commit()
            executed.append(f.name)
    return executed


# B278 (v0.9.11.14): defense-in-depth drop of manifest-declared tables.
# Runs in addition to _run_down_migrations during uninstall when
# remove_data=True. Catches plugins that ship no _down.sql, or whose
# _down.sql doesn't actually drop the declared tables.
#
# Identifier validator matches catalog._VALID_IDENT semantics — any table
# name that doesn't conform never reaches SQL composition.
_VALID_TABLE_NAME_B278 = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _drop_declared_tables(plugin_id: str, manifest_data: dict) -> tuple[list[str], list[dict]]:
    """Drop every table the plugin's manifest declares under
    `databases.postgres.tables[]`. Returns (dropped, failed) where:
      - dropped: list[str] of table names that were dropped (or already absent)
      - failed:  list[{"table": str, "reason": str}] for tables that DROP errored

    Defense in depth — runs alongside _run_down_migrations during uninstall.
    DROP TABLE IF EXISTS is idempotent so calling on already-dropped tables
    is harmless. CASCADE handles foreign-key dependencies the plugin may
    have created (views, materialized views, fkey constraints).

    Identifier validation prevents SQL injection via malformed manifest
    entries; non-conforming entries are added to `failed` and never reach
    SQL composition.
    """
    from psycopg2 import sql as pg_sql
    from ..db import get_pg_conn

    declared = (manifest_data or {}).get("databases", {}).get("postgres", {}).get("tables", [])
    if not isinstance(declared, list):
        # B285: still purge stale schema_migrations rows even if the manifest
        # is malformed — symmetry with _run_down_migrations's contract.
        _purge_schema_migrations_rows(plugin_id)
        return ([], [])

    dropped: list[str] = []
    failed: list[dict] = []

    if not declared:
        # B285: utility plugin path — no tables to drop, but the plugin may
        # still have shipped migrations that registered tracking rows.
        # Symmetry guarantee: after uninstall, no stale rows for this plugin.
        _purge_schema_migrations_rows(plugin_id)
        return (dropped, failed)

    with get_pg_conn() as conn:
        cur = conn.cursor()
        for table_name in declared:
            if not isinstance(table_name, str) or not _VALID_TABLE_NAME_B278.match(table_name):
                failed.append({
                    "table": str(table_name)[:100],
                    "reason": "invalid identifier; refused to compose SQL",
                })
                continue
            try:
                cur.execute(
                    pg_sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                        pg_sql.Identifier(table_name)
                    )
                )
                conn.commit()
                dropped.append(table_name)
            except Exception as exc:
                conn.rollback()
                failed.append({
                    "table": table_name,
                    "reason": str(exc)[:200],
                })
                logger.warning(
                    f"Plugin {plugin_id}: DROP TABLE {table_name} failed — {exc}"
                )

    # B285: clear stale schema_migrations rows for this plugin. Without this,
    # the next install/Update sees the rows and skips re-running the up files
    # — install returns 200 but tables don't exist and sync fails with
    # UndefinedTable. _run_down_migrations cleared rows for plugins that ship
    # *_down.sql files, but plugins shipping up-only migrations never had
    # their rows cleared, so reinstall was silently broken.
    _purge_schema_migrations_rows(plugin_id)

    return (dropped, failed)


def _purge_schema_migrations_rows(plugin_id: str) -> int:
    """B285: clear schema_migrations rows for a plugin (filename LIKE
    '{plugin_id}/%'). Used by _drop_declared_tables to keep the tracking
    table in sync with actual table state. Idempotent — returns the row
    count deleted (0 if none). Failures log a warning rather than raise
    so they don't disrupt the uninstall flow."""
    from ..db import get_pg_conn

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM schema_migrations WHERE filename LIKE %s",
                (f"{plugin_id}/%",),
            )
            conn.commit()
            deleted = cur.rowcount or 0
            if deleted:
                logger.info(
                    f"Plugin {plugin_id}: cleared {deleted} stale schema_migrations row(s)"
                )
            return deleted
    except Exception as exc:
        logger.warning(
            f"Plugin {plugin_id}: failed to purge schema_migrations rows — {exc}"
        )
        return 0


@router.get(
    "/plugins/{plugin_id}/uninstall-check",
    operation_id="plugins.uninstall_check",
    response_model=UninstallCheckResponse,
    response_model_exclude_none=True,
    summary="Pre-uninstall info for the confirmation modal",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def uninstall_check(plugin_id: str, _: None = Depends(requires("plugins.install"))):
    """
    Return information needed to render the uninstall confirmation modal:
    - dependents: installed plugins that depend on this one (via `requires.{capability}`)
    - tables: Postgres/ClickHouse tables owned by this plugin
    - data_dirs: filesystem data directories (mainly for utility plugins)
    """
    _validate_plugin_id(plugin_id)

    manifest = _load_plugin(plugin_id)
    if not manifest:
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    dependents = _find_dependents(plugin_id)

    tables = []
    dbs = manifest.get("databases", {})
    for engine, cfg in dbs.items():
        if isinstance(cfg, dict):
            for table in cfg.get("tables", []):
                tables.append({"table": table, "engine": engine})

    # Utility plugins store data on the filesystem under {repo}/data/{slug}/.
    # Report any directory we find so the modal can offer keep/delete.
    data_dirs = []
    data_dir = REPO_ROOT / "data" / plugin_id
    if data_dir.exists() and data_dir.is_dir():
        try:
            size_bytes = sum(
                f.stat().st_size for f in data_dir.rglob("*") if f.is_file()
            )
        except OSError:
            size_bytes = 0
        data_dirs.append({
            "path": str(data_dir),
            "size_mb": round(size_bytes / (1024 * 1024), 1),
        })

    references = _find_references(plugin_id)

    # B280 (v0.9.11.15): per-table sizes + row counts for the uninstall
    # confirmation modal. Same identifier validation as B278's helper —
    # malformed manifest entries silently skipped (defense in depth).
    # Tables declared in manifest but missing from pg_class also silently
    # skipped (could be partial-install state).
    tables_to_drop_if_data_removed: list[dict] = []
    total_size_mb = 0.0
    declared_pg_tables = (manifest.get("databases", {}) or {}).get("postgres", {}).get("tables", []) or []
    if isinstance(declared_pg_tables, list) and declared_pg_tables:
        try:
            from ..db import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                for table_name in declared_pg_tables:
                    if not isinstance(table_name, str) or not _VALID_TABLE_NAME_B278.match(table_name):
                        continue
                    cur.execute(
                        """
                        SELECT
                          pg_total_relation_size(c.oid) AS size_bytes,
                          COALESCE(s.n_live_tup, 0) AS rows
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        LEFT JOIN pg_stat_user_tables s
                          ON s.relname = c.relname AND s.schemaname = n.nspname
                        WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = %s
                        """,
                        (table_name,),
                    )
                    row = cur.fetchone()
                    if not row:
                        continue
                    size_mb = round((row[0] or 0) / (1024 ** 2), 2)
                    rows = int(row[1] or 0)
                    tables_to_drop_if_data_removed.append({
                        "name": table_name,
                        "size_mb": size_mb,
                        "rows": rows,
                    })
                    total_size_mb += size_mb
        except Exception as exc:
            logger.warning(f"uninstall_check: per-table size lookup failed for {plugin_id} — {exc}")

    return {
        "plugin_id": plugin_id,
        "display_name": manifest.get("display_name", plugin_id),
        "type": manifest.get("type"),
        "dependents": dependents,
        "references": references,
        "tables": tables,
        "data_dirs": data_dirs,
        "has_dependents": len(dependents) > 0,
        "has_references": len(references) > 0,
        "has_data": len(tables) > 0 or len(data_dirs) > 0,
        # B280 (v0.9.11.15): per-table sizes for honest uninstall modal
        "tables_to_drop_if_data_removed": tables_to_drop_if_data_removed,
        "tables_to_drop_total_size_mb": round(total_size_mb, 2),
        "tables_to_drop_total_count": len(tables_to_drop_if_data_removed),
    }


@router.delete(
    "/plugins/{plugin_id}/install",
    operation_id="plugins.uninstall",
    response_model=PluginUninstallResponse,
    response_model_exclude_none=True,
    summary="Uninstall a plugin (with optional dependent cascade)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def uninstall_plugin(
    plugin_id: str,
    request: Request,
    remove_data: bool = False,
    remove_references: bool = False,
    cascade: bool = False,
    _: None = Depends(requires("plugins.install")),
):
    """
    Uninstall a plugin.

    - remove_data=true: run down migrations to drop plugin tables before removal
    - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
      references — delete annotations pinned to the plugin, delete
      shares pointing at /plugin/<id>/*, strip the plugin slug from
      fusion `requires` arrays. Alert rules are left alone (Phase 2).
    - cascade=true: also uninstall all plugins that depend on this one

    Returns has_dependents status if dependents exist and cascade=false —
    the frontend should prompt the user to confirm cascade or cancel.
    """
    admin = get_me(request)
    actor_user_id = str(admin.get("id")) if admin.get("id") else None
    _validate_plugin_id(plugin_id)
    import shutil

    installed_dest = INSTALLED_DIR / plugin_id
    if not installed_dest.exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    # Check for dependents
    dependents = _find_dependents(plugin_id)
    if dependents and not cascade:
        return {
            "status": "has_dependents",
            "dependents": [
                {"plugin": d["plugin"], "display_name": d["display_name"]}
                for d in dependents
            ],
        }

    uninstalled = []
    data_removed = []
    # B163 (v0.9.4.11): row counts of DB cleanup, keyed by slug — flowed
    # into the per-slug audit log entry below.
    purged_counts: dict[str, dict[str, int]] = {}

    # Collect display names before any directory is deleted
    to_uninstall = [dep["plugin"] for dep in dependents] + [plugin_id] if cascade else [plugin_id]
    name_map: dict[str, str] = {}
    for slug in to_uninstall:
        m = _load_plugin(slug)
        name_map[slug] = m.get("display_name", slug) if m else slug

    # Cascade: uninstall dependents first
    if cascade:
        for dep in dependents:
            dep_dest = INSTALLED_DIR / dep["plugin"]
            if dep_dest.exists():
                if remove_data:
                    data_removed.extend(_run_down_migrations(dep["plugin"]))
                shutil.rmtree(dep_dest)
                # B163: clean up cascaded plugin's DB rows
                purged_counts[dep["plugin"]] = _purge_plugin_db_rows(dep["plugin"])
                uninstalled.append(dep["plugin"])

    # Run uninstall hook if declared (utility plugins use this to stop services)
    meta = _load_plugin(plugin_id) or {}
    uninstall_hook = meta.get("uninstall_hook")
    if uninstall_hook:
        hook_script = installed_dest / uninstall_hook
        if hook_script.exists():
            try:
                import subprocess as _sp
                logger.info(f"Plugin {plugin_id}: running uninstall hook {uninstall_hook} (remove_data={remove_data})")
                # S107: strip NOUSVIZ_* and other secrets from hook env
                from ..plugin_subprocess import plugin_hook_env
                _sp.run(
                    ["bash", str(hook_script)],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(REPO_ROOT),
                    env=plugin_hook_env(extra={
                        "NOUSVIZ_DIR": str(REPO_ROOT),
                        "NOUSVIZ_REMOVE_DATA": "1" if remove_data else "0",
                    }),
                )
            except Exception as e:
                logger.warning(f"Plugin {plugin_id}: uninstall hook failed: {e}")
                # B203
                try:
                    from ..log_events import log_plugin_event
                    log_plugin_event(
                        "error",
                        plugin_id,
                        "hook_uninstall",
                        f"bash uninstall_hook failed: {str(e)[:300]}",
                        source="plugin_uninstall",
                        actor_user_id=actor_user_id,
                    )
                except Exception:
                    pass

    # P118: run Python on_uninstall hook inline (plugin dir is about to be
    # removed, so we can't defer to the async worker). Capped at 30s.
    try:
        from ..plugin_hooks import run_hook_inline
        run_hook_inline(plugin_id, "on_uninstall", payload={"remove_data": bool(remove_data)})
    except Exception as _hook_err:
        logger.warning(f"Plugin {plugin_id}: on_uninstall hook failed: {_hook_err}")
        # B203
        try:
            from ..log_events import log_plugin_event
            log_plugin_event(
                "error",
                plugin_id,
                "hook_uninstall",
                f"on_uninstall hook failed: {str(_hook_err)[:300]}",
                source="plugin_uninstall",
                actor_user_id=actor_user_id,
            )
        except Exception:
            pass

    # P203 (v0.9.0): revoke nousviz_plugin role's access to this plugin's
    # declared tables BEFORE running down-migrations. If remove_data=False,
    # the tables stick around but the role can no longer touch them — a
    # future reinstall will re-grant.
    try:
        from ..plugin_grants import revoke_plugin_tables
        revoke_plugin_tables(plugin_id, meta or {})
    except Exception as _revoke_err:
        logger.warning(f"Plugin {plugin_id}: revoke nousviz_plugin failed — {_revoke_err}")

    # Remove data for the target plugin
    # B278 (v0.9.11.14): two-step approach.
    # 1. _run_down_migrations: plugin author's intended cleanup via *_down.sql
    # 2. _drop_declared_tables: defense-in-depth — drops the manifest's
    #    declared tables. Catches plugins that ship no _down.sql or whose
    #    _down.sql doesn't actually drop the tables (silent-failure pattern
    #    that kept 601 MB of data on production through 2026-05-04).
    # Both calls are idempotent. The audit log below records what each
    # path actually accomplished, not the operator's intent.
    target_tables_dropped: list[str] = []
    target_tables_drop_failed: list[dict] = []
    if remove_data:
        data_removed.extend(_run_down_migrations(plugin_id))
        target_tables_dropped, target_tables_drop_failed = _drop_declared_tables(plugin_id, meta or {})

    # B281 (v0.9.11.21): auto-clean orphan references when the operator
    # opted in. Runs BEFORE the plugin's source dir is removed so any
    # plugin-supplied cleanup hook (future) could still execute. The
    # helper returns None outcome if remove_references=false so the
    # audit/response code below can short-circuit without branching
    # on the flag again.
    references_cleanup: Optional[dict] = None
    if remove_references:
        references_cleanup = _cleanup_plugin_references(plugin_id)

    shutil.rmtree(installed_dest)
    # B163 (v0.9.4.11): clean up the target plugin's DB rows. Without this,
    # encrypted credentials, _trust_frontend consent, settings, and registry
    # rows persist past uninstall — and a future reinstall silently inherits
    # them, defeating the operator-consent design (B151).
    purged_counts[plugin_id] = _purge_plugin_db_rows(plugin_id)
    uninstalled.append(plugin_id)

    # Refresh capability registry after uninstall
    refresh_capabilities()

    uninstalled_names = [name_map.get(slug, slug) for slug in uninstalled]

    # Auto-reload API to deactivate plugin routes (zero-downtime via PM2)
    try:
        import subprocess as _sp
        _sp.Popen(["pm2", "reload", "api", "--update-env"], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        logger.info(f"Plugin {plugin_id}: triggered PM2 reload to deactivate routes")
    except Exception as e:
        logger.warning(f"Plugin {plugin_id}: could not trigger PM2 reload: {e}")

    from .activity import record_activity
    for slug in uninstalled:
        record_activity(
            action="plugin_uninstall",
            plugin_id=slug,
            detail={"display_name": name_map.get(slug, slug), "data_removed": remove_data},
        )
        # B278 (v0.9.11.14): audit log records actual outcome, not just intent.
        # Only the target plugin (plugin_id) carries the per-table breakdown;
        # cascading dependent uninstalls don't currently track per-plugin
        # drop results in this loop (their _drop_declared_tables calls
        # happen inside the dependency-recursion path above; recorded there).
        is_target = slug == plugin_id
        audit_detail = {
            "data_removed": remove_data,
            "purged_rows": purged_counts.get(slug, {}),
        }
        if is_target and remove_data:
            audit_detail["data_tables_dropped"] = target_tables_dropped
            audit_detail["data_tables_drop_failed"] = target_tables_drop_failed
            audit_detail["down_migrations_run"] = data_removed
        # B281 (v0.9.11.21): record references-cleanup outcome on the
        # target plugin's audit row only. Cascading dependents don't
        # currently get individual reference cleanup — Phase 2 follow-up.
        if is_target and remove_references and references_cleanup is not None:
            audit_detail["references_removed"] = True
            audit_detail["annotations_deleted"] = references_cleanup.get("annotations_deleted") or []
            audit_detail["shares_deleted"] = references_cleanup.get("shares_deleted") or []
            audit_detail["fusions_repointed"] = references_cleanup.get("fusions_repointed") or []
            audit_detail["alerts_left_alone"] = references_cleanup.get("alerts_left_alone") or []
            audit_detail["references_cleanup_failed"] = references_cleanup.get("failed") or []
        _log_plugin_action(slug, "uninstall", audit_detail)

    return {
        "status": "uninstalled",
        "uninstalled": uninstalled,
        "uninstalled_names": uninstalled_names,
        "data_removed": remove_data,
        # B278 (v0.9.11.14): expose actual outcome to the API client so the
        # frontend (B280 in v0.9.11.15) can render an honest post-uninstall
        # summary instead of just echoing the operator's intent flag.
        "data_tables_dropped": target_tables_dropped,
        "data_tables_drop_failed": target_tables_drop_failed,
        "migrations_run": data_removed,
        # B281 (v0.9.11.21): per-kind cleanup outcomes for the modal's
        # post-summary. Null when the operator didn't opt in.
        "references_removed": bool(remove_references),
        "references_cleanup": references_cleanup,
        "restart_required": False,
        "note": "API is reloading automatically to deactivate plugin routes.",
    }


# ── Updates (B144 / v0.9.2.4) ─────────────────────────────────────────


@router.get(
    "/plugins/updates",
    operation_id="plugins.updates.list",
    response_model=PluginUpdatesListResponse,
    response_model_exclude_none=True,
    summary="Bulk update status for every installed plugin (B144 cache)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
    },
)
async def list_plugin_updates(
    request: Request,
    _: None = Depends(requires("plugins.install")),
):
    """Bulk fetch cached update status for every installed plugin.

    Stale entries (older than ~1h) get a fire-and-forget refresh kicked
    off in the background so the UI sees fresh data on the next poll.
    """
    from ..plugin_update_checker import get_cached_status, is_stale, schedule_async_check

    out: list[dict] = []
    if INSTALLED_DIR.exists():
        for plugin_dir in INSTALLED_DIR.iterdir():
            if not plugin_dir.is_dir():
                continue
            if not (plugin_dir / "plugin.yaml").exists():
                continue
            slug = plugin_dir.name
            cached = get_cached_status(slug)
            if cached is None or is_stale(slug):
                schedule_async_check(slug)
            if cached is not None:
                out.append({
                    "plugin_id": cached.plugin_id,
                    "source_class": cached.source_class,
                    "installed_version": cached.installed_version,
                    "latest_version": cached.latest_version,
                    "update_available": cached.update_available,
                    "last_error": cached.last_error,
                })
            else:
                out.append({
                    "plugin_id": slug,
                    "source_class": "pending",
                    "installed_version": None,
                    "latest_version": None,
                    "update_available": False,
                    "last_error": None,
                })

    return {"updates": out}


@router.post(
    "/plugins/{plugin_id}/check-update",
    operation_id="plugins.check_update",
    response_model=PluginUpdateInfo,
    response_model_exclude_none=True,
    summary="Force a synchronous update check for one plugin",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
    },
)
async def check_plugin_update(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.install")),
):
    """Synchronously check this plugin for an available update.

    Use when the operator clicks an explicit "Check now" affordance, or
    when the cached status says no-update but the operator wants to force
    a re-check after pushing a new version upstream.
    """
    _validate_plugin_id(plugin_id)
    from ..plugin_update_checker import check_plugin

    status = check_plugin(plugin_id)
    return {
        "plugin_id": status.plugin_id,
        "source_class": status.source_class,
        "source_url": status.source_url,
        "installed_version": status.installed_version,
        "latest_version": status.latest_version,
        "update_available": status.update_available,
        "last_error": status.last_error,
    }


def _stage_plugin_clone(
    plugin_id: str,
    source_class: str,
    source_url: Optional[str],
    staging_dir: Path,
) -> str:
    """Clone or copy the plugin into a staging directory.

    Returns the resolved tag/version that was checked out (informational).
    Raises HTTPException on any failure — caller must clean up `staging_dir`.

    For first_party: copy the bundled catalog dir verbatim.
    For git: shallow-clone the highest semver tag using deploy_keys auth.
    """
    import shutil
    import subprocess as sp

    if source_class == "first_party":
        # Find the catalog source. Prefer utilities/, then official/.
        utility_src = UTILITIES_DIR / plugin_id
        official_src = OFFICIAL_DIR / plugin_id
        src: Optional[Path] = None
        if utility_src.exists() and (utility_src / "plugin.yaml").exists():
            src = utility_src
        elif official_src.exists() and (official_src / "plugin.yaml").exists():
            src = official_src
        if src is None:
            raise HTTPException(
                404,
                f"First-party plugin '{plugin_id}' has no bundled catalog source",
            )
        shutil.copytree(str(src), str(staging_dir))
        meta = yaml.safe_load((staging_dir / "plugin.yaml").read_text()) or {}
        return str(meta.get("version") or "?")

    if source_class == "git":
        if not source_url:
            raise HTTPException(400, "git source has no source_url")
        # B152 (v0.9.4.4): use the WITH_REF variant so we clone the exact
        # tag the upstream author pushed (e.g. `v0.3.0` or `0.3.0`).
        # The previous code reused the v-stripped normalization for both
        # display AND clone, which broke `git clone --branch` against
        # repos that only push v-prefixed tags.
        from ..plugin_update_checker import fetch_latest_git_tag_with_ref
        tag_pair = fetch_latest_git_tag_with_ref(source_url)
        if not tag_pair:
            raise HTTPException(
                502,
                f"No semver tags found on '{source_url}'. "
                f"Push a tag (e.g. v1.0.0) before attempting an update.",
            )
        original_ref, normalized_version = tag_pair

        clone_env = os.environ.copy()
        if source_url.startswith("git@"):
            ssh_host = source_url.split("@")[1].split(":")[0] if ":" in source_url else ""
            key_path = _get_deploy_key_path(ssh_host, repo_url=source_url)
            if key_path:
                clone_env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
            elif "GIT_SSH_COMMAND" not in clone_env:
                clone_env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"

        result = sp.run(
            ["git", "clone", "--depth=1", "--branch", original_ref, source_url, str(staging_dir)],
            capture_output=True, text=True, env=clone_env,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[:300]
            raise HTTPException(
                502,
                f"git clone failed for tag '{original_ref}': {stderr}",
            )
        # Return the normalized version for display in the update result.
        return normalized_version

    raise HTTPException(400, f"Unsupported source_class '{source_class}'")


def _validate_staged_plugin(plugin_id: str, staging_dir: Path) -> dict:
    """Sanity-check the staged plugin before swapping. Returns parsed manifest."""
    manifest_path = staging_dir / "plugin.yaml"
    if not manifest_path.exists():
        raise HTTPException(500, "Staged plugin missing plugin.yaml")
    try:
        meta = yaml.safe_load(manifest_path.read_text()) or {}
    except Exception as exc:
        raise HTTPException(500, f"Staged plugin's plugin.yaml is invalid: {exc}")
    declared_name = meta.get("name")
    if declared_name and declared_name != plugin_id:
        raise HTTPException(
            500,
            f"Staged plugin declares name='{declared_name}', expected '{plugin_id}'. "
            f"Aborting to prevent corrupting the install.",
        )
    return meta


@router.post(
    "/plugins/{plugin_id}/update",
    operation_id="plugins.update",
    response_model=PluginUpdateResponse,
    response_model_exclude_none=True,
    summary="Atomic-swap update to the latest version (B145)",
    responses={
        400: {"model": ErrorDetail, "description": "Cannot determine update source."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def update_plugin(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.install")),
):
    """Update an installed plugin to the latest version from its source.

    Atomic-swap design (B145): the new code is cloned to a staging directory
    first, validated, then atomically swapped with the live install. If
    anything fails before the swap, the live install is untouched. If the
    post-swap idempotent steps (migrations, grants) fail, the previous live
    install is restored from a sibling backup.

    Credentials, settings, and synced data are preserved across the swap
    (DB tables are not dropped). The plugin briefly becomes unavailable
    while PM2 reloads to pick up the new routes.
    """
    import shutil
    import time
    _validate_plugin_id(plugin_id)
    from ..plugin_update_checker import detect_source_class, check_plugin

    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    source_class, source_url = detect_source_class(plugin_id)
    if source_class == "unknown":
        raise HTTPException(
            400,
            f"Cannot determine update source for '{plugin_id}'. "
            f"The installed manifest has no repository_url and no first-party catalog source.",
        )

    # Snapshot pre-update version for the response
    pre_meta = yaml.safe_load((plugin_dir / "plugin.yaml").read_text()) or {}
    pre_version = pre_meta.get("version")

    ts = int(time.time())
    staging_dir = INSTALLED_DIR / f"{plugin_id}.staging.{ts}"
    backup_dir = INSTALLED_DIR / f"{plugin_id}.backup.{ts}"

    # ── Phase 1: stage the new code (live install untouched) ──────────
    try:
        resolved_tag = _stage_plugin_clone(plugin_id, source_class, source_url, staging_dir)
        post_meta = _validate_staged_plugin(plugin_id, staging_dir)
    except HTTPException as exc:
        # Clean up staging on any pre-swap failure; live install untouched
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        logger.warning(f"Update for {plugin_id}: staging failed — {exc.detail}")
        raise
    except Exception as exc:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        logger.error(f"Update for {plugin_id}: staging crashed — {exc}", exc_info=True)
        raise HTTPException(500, f"Staging failed: {exc}")

    post_version = post_meta.get("version")

    # ── Phase 2: atomic filesystem swap ───────────────────────────────
    # Move live → backup, staging → live. Both renames are atomic on the
    # same filesystem. If renaming live → backup fails, abort cleanly.
    swap_completed = False
    try:
        plugin_dir.rename(backup_dir)
        try:
            staging_dir.rename(plugin_dir)
            swap_completed = True
        except Exception as exc:
            # Couldn't promote staging — try to restore backup
            logger.error(f"Update for {plugin_id}: staging→live rename failed — {exc}")
            try:
                backup_dir.rename(plugin_dir)
            except Exception as restore_exc:
                logger.error(f"Update for {plugin_id}: backup restore also failed — {restore_exc}")
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise HTTPException(500, f"Filesystem swap failed: {exc}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Update for {plugin_id}: live→backup rename failed — {exc}")
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise HTTPException(500, f"Could not move live install aside: {exc}")

    # ── Phase 3: idempotent post-swap steps ───────────────────────────
    # Run new migrations (already-applied skipped via schema_migrations),
    # refresh grants (idempotent), update plugin_registry version row.
    # Failures here trigger a rollback to the backup.
    rollback_triggered = False
    rollback_reason: Optional[str] = None
    migrations_applied: list[str] = []
    try:
        try:
            migrations_applied = _run_plugin_migrations(plugin_id, plugin_dir)
        except Exception as exc:
            rollback_reason = f"migration step failed: {exc}"
            raise

        # Grants — both passes (matching install_plugin's behavior post-B141)
        try:
            from ..plugin_grants import grant_plugin_tables
            grant_plugin_tables(plugin_id, post_meta or {})
        except Exception as exc:
            rollback_reason = f"grant step failed: {exc}"
            raise

        # Update plugin_registry version + installed_commit_sha.
        # The SHA must be refreshed so the loader's S109 integrity check
        # accepts the new files. Without this, the next page load reports
        # "Plugin failed integrity check — files modified since install".
        try:
            import subprocess as _sp
            sha_proc = _sp.run(
                ["git", "-C", str(plugin_dir), "rev-parse", "HEAD"],
                capture_output=True, text=True,
            )
            new_sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else None
        except Exception as exc:
            new_sha = None
            logger.warning(f"Update for {plugin_id}: rev-parse failed — {exc}")

        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE plugin_registry
                    SET version = %s,
                        installed_commit_sha = COALESCE(%s, installed_commit_sha),
                        installed_at = NOW()
                    WHERE slug = %s
                    """,
                    (str(post_version) if post_version else None, new_sha, plugin_id),
                )
        except Exception as exc:
            # Non-fatal — registry is informational; the file swap succeeded
            logger.warning(f"Update for {plugin_id}: registry update failed — {exc}")

        # Second-pass grant after any module migrations (B141)
        try:
            from ..plugin_grants import grant_plugin_tables as _grant2
            _grant2(plugin_id, post_meta or {})
        except Exception as exc:
            logger.warning(f"Update for {plugin_id}: post-module grant skipped — {exc}")

    except Exception:
        # Rollback: live → discard, backup → live
        rollback_triggered = True
        logger.error(f"Update for {plugin_id}: rollback triggered — {rollback_reason}")
        try:
            shutil.rmtree(plugin_dir, ignore_errors=True)
            backup_dir.rename(plugin_dir)
        except Exception as restore_exc:
            logger.error(f"Update for {plugin_id}: rollback rename failed — {restore_exc}")
        raise HTTPException(
            500,
            f"Update post-swap step failed; rolled back to v{pre_version}. Cause: {rollback_reason}",
        )

    # ── Phase 4: cleanup + audit ──────────────────────────────────────
    if swap_completed and not rollback_triggered:
        shutil.rmtree(backup_dir, ignore_errors=True)

    try:
        _log_plugin_action(
            plugin_id,
            "update",
            {
                "from_version": pre_version,
                "to_version": post_version,
                "source_class": source_class,
                "resolved_tag": resolved_tag,
                "migrations_applied": migrations_applied,
            },
        )
    except Exception:
        pass

    # Refresh the cached update status so the UI immediately sees the
    # post-update state ("no update available").
    try:
        check_plugin(plugin_id)
    except Exception:
        pass

    # B161 (v0.9.4.10): trigger pm2 reload so the new routes.py is actually
    # imported. Without this, the file swap is on disk but Python's module
    # cache still holds the old plugin module — and FastAPI keeps dispatching
    # to the old route handlers until the hourly cron_restart fires (up to
    # 60 minutes later). Same pattern uninstall already uses (see
    # _deactivate_plugin_routes — Popen is fire-and-forget; reload happens
    # after this response returns so the operator gets a clean 200).
    try:
        import subprocess as _sp
        _sp.Popen(
            ["pm2", "reload", "api", "--update-env"],
            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
        )
        logger.info(f"Plugin {plugin_id}: triggered PM2 reload to load new routes")
    except Exception as exc:
        logger.warning(f"Plugin {plugin_id}: could not trigger PM2 reload: {exc}")

    return {
        "status": "updated",
        "plugin_id": plugin_id,
        "from_version": pre_version,
        "to_version": post_version,
        "resolved_tag": resolved_tag,
        "source_class": source_class,
        "source_url": source_url,
        "migrations_applied": migrations_applied,
        "note": "API is reloading automatically to pick up new routes.",
    }


@router.get(
    "/plugins/{plugin_id}/alerts/{alert_name}",
    operation_id="plugins.alert",
    response_model=PluginYamlResource,
    summary="Get a plugin alert definition (YAML, returned verbatim)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Alert not found in plugin."},
    },
)
async def get_alert(
    plugin_id: str,
    alert_name: str,
    _: None = Depends(requires("plugins.read")),
):
    """Get an alert definition."""
    data = _load_yaml(plugin_id, f"alerts/{alert_name}.yaml")
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Alert '{alert_name}' not found in plugin '{plugin_id}'",
        )
    return data


# ── Plugin settings ──────────────────────────────────────────────────

class PluginSettingValue(BaseModel):
    key: str
    value: object  # JSONB — string, bool, number, list all valid


class PluginSettingsBody(BaseModel):
    settings: list[PluginSettingValue]


@router.get(
    "/plugins/{plugin_id}/settings",
    operation_id="plugins.settings.get",
    response_model=PluginSettingsResponse,
    summary="Read a plugin's saved settings",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def get_plugin_settings(
    plugin_id: str,
    _: None = Depends(requires("plugins.configure")),
):
    """Return current saved settings for a plugin."""
    _validate_plugin_id(plugin_id)
    plugin = _load_plugin(plugin_id, installed_only=True)
    if not plugin:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")
    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            # B130 (v0.8.6.5): exclude `_conn.*` rows — those are connection
            # fields stored via plugin_config; they belong to /connections,
            # not the plugin-declared /settings surface.
            cur.execute(
                "SELECT key, value FROM plugin_settings WHERE plugin_id = %s AND key NOT LIKE '_conn.%%'",
                (plugin_id,)
            )
            rows = cur.fetchall()
        return {"settings": [{"key": r[0], "value": r[1]} for r in rows]}
    except Exception as e:
        raise HTTPException(500, f"Failed to load settings: {e}")


@router.post(
    "/plugins/{plugin_id}/settings",
    operation_id="plugins.settings.set",
    response_model=PluginSettingsSaveResponse,
    summary="Upsert a plugin's settings",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
        422: {"model": ErrorDetail, "description": "Setting key not declared in the plugin manifest."},
    },
)
async def save_plugin_settings(
    plugin_id: str,
    body: PluginSettingsBody,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Upsert settings for a plugin. Each key/value pair stored as a separate row."""
    _validate_plugin_id(plugin_id)
    plugin = _load_plugin(plugin_id, installed_only=True)
    if not plugin:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")
    declared = {s["name"] for s in (plugin.get("settings") or [])}
    for s in body.settings:
        if declared and s.key not in declared:
            raise HTTPException(422, f"Unknown setting key '{s.key}' for plugin '{plugin_id}'")
    try:
        import json as _json
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            for s in body.settings:
                cur.execute(
                    """
                    INSERT INTO plugin_settings (plugin_id, key, value, updated_at)
                    VALUES (%s, %s, %s::jsonb, now())
                    ON CONFLICT (plugin_id, key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (plugin_id, s.key, _json.dumps(s.value))
                )
            conn.commit()
        _log_plugin_action(plugin_id, "settings_update")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save settings: {e}")


# ── Plugin modules ────────────────────────────────────────────────────

@router.get(
    "/plugins/{plugin_id}/modules",
    operation_id="plugins.modules.list",
    response_model=PluginModulesListResponse,
    response_model_exclude_none=True,
    summary="List a plugin's modules with enabled state",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def list_modules(
    plugin_id: str,
    _: None = Depends(requires("plugins.read")),
):
    """List modules for a plugin with their enabled state."""
    _validate_plugin_id(plugin_id)
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=True)
    if not plugin_dir:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    modules_dir = plugin_dir / "modules"
    if not modules_dir or not modules_dir.exists():
        return {"modules": []}

    enabled_names = set(_get_enabled_module_names(plugin_id))
    result = []
    for mod_dir in sorted(modules_dir.iterdir()):
        if not mod_dir.is_dir() or not (mod_dir / "module.yaml").exists():
            continue
        try:
            with open(mod_dir / "module.yaml") as f:
                mod = yaml.safe_load(f)
        except Exception:
            continue
        # Derive metadata from module files
        has_routes = (mod_dir / "api" / "routes.py").exists()
        dashboards = mod.get("dashboards", [])
        navigation = mod.get("navigation", [])
        tables = mod.get("databases", {}).get("postgres", {}).get("tables", [])
        settings = mod.get("settings", [])

        result.append({
            "name": mod_dir.name,
            "display_name": mod.get("display_name", mod_dir.name),
            "description": mod.get("description", ""),
            "version": mod.get("version", ""),
            "enabled": mod_dir.name in enabled_names,
            "enabled_by_default": mod.get("enabled_by_default", True),
            "dashboards": [{"name": d.get("name", ""), "label": d.get("label", "")} for d in dashboards],
            "navigation": [{"label": n.get("label", ""), "path": n.get("path", "")} for n in navigation],
            "tables": tables,
            "has_routes": has_routes,
            "has_settings": len(settings) > 0,
            "settings": settings,
        })
    return {"modules": result}


@router.post(
    "/plugins/{plugin_id}/modules/{module_name}/enable",
    operation_id="plugins.modules.enable",
    response_model=PluginModuleToggleResponse,
    summary="Enable a plugin module (runs migrations, grants tables)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Module not found in plugin."},
    },
)
async def enable_module(
    plugin_id: str,
    module_name: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Enable a plugin module."""
    _validate_plugin_id(plugin_id)
    plugin_dir = _find_plugin_dir(plugin_id, installed_only=True)
    if not plugin_dir or not (plugin_dir / "modules" / module_name / "module.yaml").exists():
        raise HTTPException(404, f"Module '{module_name}' not found in plugin '{plugin_id}'")

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO plugin_modules (plugin_id, module_name, enabled)
            VALUES (%s, %s, true)
            ON CONFLICT (plugin_id, module_name) DO UPDATE SET enabled = true
        """, (plugin_id, module_name))

    # Run module migrations
    migrations_dir = plugin_dir / "modules" / module_name / "storage" / "migrations"
    if migrations_dir.exists():
        for sql_file in sorted(migrations_dir.glob("*_up.sql")) + sorted(migrations_dir.glob("[0-9]*.sql")):
            if sql_file.name.endswith("_down.sql"):
                continue
            try:
                with get_pg_conn() as conn:
                    cur = conn.cursor()
                    cur.execute(sql_file.read_text())
                logger.info(f"Ran module migration: {sql_file.name}")
            except Exception as e:
                logger.warning(f"Module migration {sql_file.name} failed: {e}")

    # B141 (v0.9.2.1): grant nousviz_plugin on the plugin's declared tables
    # after module migrations have created the module-owned tables.
    # Without this, enabling a module leaves its tables ungranted and
    # plugin queries hit `permission denied`.
    try:
        plugin_yaml = plugin_dir / "plugin.yaml"
        if plugin_yaml.exists():
            plugin_meta = yaml.safe_load(plugin_yaml.read_text()) or {}
            from ..plugin_grants import grant_plugin_tables
            grant_plugin_tables(plugin_id, plugin_meta)
    except Exception as _grant_err:
        logger.warning(
            f"Plugin {plugin_id}/module {module_name}: post-enable grant failed — {_grant_err}"
        )

    return {"ok": True, "message": f"Module '{module_name}' enabled. Restart API to load routes."}


@router.post(
    "/plugins/{plugin_id}/modules/{module_name}/disable",
    operation_id="plugins.modules.disable",
    response_model=PluginModuleToggleResponse,
    summary="Disable a plugin module (data preserved)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
    },
)
async def disable_module(
    plugin_id: str,
    module_name: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Disable a plugin module. Data is preserved."""
    _validate_plugin_id(plugin_id)

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO plugin_modules (plugin_id, module_name, enabled)
            VALUES (%s, %s, false)
            ON CONFLICT (plugin_id, module_name) DO UPDATE SET enabled = false
        """, (plugin_id, module_name))

    return {"ok": True, "message": f"Module '{module_name}' disabled. Restart API to unload routes."}


# ── Utility plugin connection config ──────────────────────────────────

@router.get(
    "/plugins/{plugin_id}/connections",
    operation_id="plugins.connections.get",
    response_model=PluginConnectionsResponse,
    response_model_exclude_none=True,
    summary="Read a plugin's connection config (secrets masked)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin not found."},
    },
)
async def get_plugin_connections(
    plugin_id: str,
    _: None = Depends(requires("plugins.read")),
):
    """Return connection config for a plugin including module connections. Masks secrets."""
    _validate_plugin_id(plugin_id)
    plugin = _load_plugin(plugin_id, installed_only=False)
    if not plugin:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    # Merge module connections so module-declared credentials appear
    plugin = _merge_module_manifests(plugin_id, plugin)

    connections = plugin.get("connections", [])
    if not connections:
        return {"connections": []}

    from ..plugin_credentials import get_plugin_credential
    from ..plugin_config import get_config_field

    result = []
    for conn_spec in connections:
        prefix = conn_spec.get("env_prefix", "").upper()
        fields = conn_spec.get("fields", [])
        values = {}
        for f in fields:
            if _field_is_secret(f):
                val = get_plugin_credential(plugin_id, f["name"], env_prefix=prefix, performed_by="settings_read")
                values[f["name"]] = "••••••••" if val else ""
            else:
                # B130 (v0.8.6.5): read non-secret fields from plugin_settings
                # (DB), falling back to os.environ for pre-v0.8.6.5 installs.
                # get_config_field self-heals the fallback path into DB.
                values[f["name"]] = get_config_field(
                    plugin_id, f["name"], env_prefix=prefix, default=f.get("default", "")
                )
        entry = {
            "name": conn_spec.get("name"),
            "label": conn_spec.get("label"),
            "description": conn_spec.get("description"),
            "fields": fields,
            "values": values,
        }
        # Pass module tag through to frontend for grouping
        if conn_spec.get("_module"):
            entry["_module"] = conn_spec["_module"]
            entry["_module_label"] = conn_spec.get("_module_label", conn_spec["_module"])
        result.append(entry)
    return {"connections": result}


@router.post(
    "/plugins/{plugin_id}/connections",
    operation_id="plugins.connections.set",
    response_model=PluginConnectionsSaveResponse,
    response_model_exclude_none=True,
    summary="Save plugin connection config + run health hook",
    responses={
        400: {"model": ErrorDetail, "description": "Plugin has no connection config declared."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin not found."},
    },
)
async def save_plugin_connections(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Save connection config for a plugin. Secrets → encrypted DB. Non-secrets → .env."""
    _validate_plugin_id(plugin_id)
    plugin = _load_plugin(plugin_id, installed_only=False)
    if not plugin:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    body = await request.json()
    connections = plugin.get("connections", [])
    if not connections:
        raise HTTPException(400, "This plugin has no connection config")

    from ..plugin_credentials import store_plugin_credential
    from ..plugin_config import upsert_config_field

    conn_spec = connections[0]  # Currently only support first connection
    prefix = conn_spec.get("env_prefix", "").upper()
    fields = conn_spec.get("fields", [])

    for f in fields:
        field_name = f["name"]
        val = body.get(field_name, f.get("default", ""))

        if _field_is_secret(f):
            # Secret fields → encrypted credentials table (skip masked values).
            # Subprocesses fetch via the credential broker (Unix socket);
            # API in-process via the registered resolver. (P208 / v0.9.0)
            if val and val != "••••••••":
                store_plugin_credential(plugin_id, field_name, val, credential_type=conn_spec.get("type", "api_key"))
        else:
            # B130 (v0.8.6.5): non-secret fields → plugin_settings table.
            # Previously went to .env + os.environ mirror, which caused
            # the "all fields show •••••••• after save" bug because env
            # is per-process and doesn't survive worker restart/reload.
            # DB is now the single source of truth; .env is read-only
            # fallback for pre-v0.8.6.5 installs (see plugin_config.py).
            if val:
                upsert_config_field(plugin_id, field_name, str(val))

    # P118: fire declarative on_credentials_saved hook.
    # Non-blocking — hook runs async in jobs-worker. Payload includes the
    # field names that were saved (not the values).
    try:
        from ..plugin_hooks import fire_hook
        saved_fields = [f["name"] for f in fields if body.get(f["name"])]
        fire_hook(plugin_id, "on_credentials_saved", payload={"fields": saved_fields})
    except Exception as _hook_err:
        logger.warning(f"Plugin {plugin_id}: on_credentials_saved hook enqueue failed: {_hook_err}")

    # Run health check if available
    health_result = None
    health_hook = plugin.get("health_check")
    if health_hook:
        installed_dir = _find_plugin_dir(plugin_id, installed_only=True)
        hook_path = installed_dir / health_hook if installed_dir else UTILITIES_DIR / plugin_id / health_hook
        if hook_path and hook_path.exists():
            try:
                import subprocess as _sp
                import json as _json
                # S107: health hooks also run plugin-authored bash — strip secrets
                from ..plugin_subprocess import plugin_hook_env
                result = _sp.run(
                    ["bash", str(hook_path)],
                    capture_output=True, text=True, timeout=10,
                    env=plugin_hook_env(),
                )
                health_result = _json.loads(result.stdout) if result.stdout.strip() else {"ok": False, "error": "No output"}
            except Exception as e:
                health_result = {"ok": False, "error": str(e)}

    return {"ok": True, "health": health_result}


# ── Plugin sync ──────────────────────────────────────────────────────
#
# B221 (v0.9.7.1): the `POST /plugins/{plugin_id}/sync` handler that lived
# here was a shadow of `routes/sync.py:trigger_sync` introduced before the
# B205 (v0.9.6.0) sync UX overhaul. FastAPI's first-match-wins router
# resolution made this one win because main.py registered plugins.router
# before sync.router, silently disabling B205's always-async + 409 active-
# run guard and B212's actor propagation in production. Deleted here so
# `routes/sync.py:197:trigger_sync` becomes the live handler.

@router.get(
    "/plugins/{plugin_id}/sync/status",
    operation_id="plugins.sync_status",
    response_model=SyncStatusResponse,
    response_model_exclude_none=True,
    summary="Sync status snapshot for the unified Sync card (B205)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
    },
)
async def get_sync_status(
    plugin_id: str,
    _: None = Depends(requires("plugins.read")),
):
    """Sync status snapshot for the unified Sync card (B205, v0.9.6).

    Returns:
        current: most recent run with status IN ('queued','running','cancelling'),
            including live progress JSONB and elapsed seconds. None when idle.
        last_success: most recent successful run.
        last_failure: most recent failed run (error/timeout/cancelled).
        last_sync: ISO timestamp of last_success.completed_at — kept for
            backward compatibility with pre-v0.9.6 frontend code.

    The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
    job_runs is the single source of truth.
    """
    _validate_plugin_id(plugin_id)
    current: dict | None = None
    last_success: dict | None = None
    last_failure: dict | None = None

    job_id = f"sync:{plugin_id}"
    try:
        from ..db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()

            # Current — most recent non-terminal run.
            cur.execute(
                """
                SELECT id, status, source, started_at, heartbeat_at, progress,
                       EXTRACT(EPOCH FROM (now() - started_at))::int AS elapsed_sec
                FROM job_runs
                WHERE job_id = %s
                  AND status IN ('queued', 'running', 'cancelling')
                ORDER BY started_at DESC NULLS LAST
                LIMIT 1
                """,
                (job_id,),
            )
            r = cur.fetchone()
            if r:
                current = {
                    "run_id": r[0],
                    "status": r[1],
                    "source": r[2],
                    "started_at": r[3].isoformat() if r[3] else None,
                    "heartbeat_at": r[4].isoformat() if r[4] else None,
                    "progress": r[5] or {},
                    "elapsed_sec": r[6],
                }

            # Last success.
            cur.execute(
                """
                SELECT id, completed_at, duration_ms, rows_written, source
                FROM job_runs
                WHERE job_id = %s AND status = 'success' AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (job_id,),
            )
            r = cur.fetchone()
            if r:
                last_success = {
                    "run_id": r[0],
                    "completed_at": r[1].isoformat() if r[1] else None,
                    "duration_ms": r[2],
                    "rows_written": r[3],
                    "source": r[4],
                }

            # Last failure (error/timeout/cancelled).
            cur.execute(
                """
                SELECT id, completed_at, status, error, source
                FROM job_runs
                WHERE job_id = %s
                  AND status IN ('error', 'timeout', 'cancelled')
                  AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (job_id,),
            )
            r = cur.fetchone()
            if r:
                # B313 (v0.10.4): extract a clean, operator-actionable
                # headline from the stderr-tail-style traceback the SDK
                # stored. Surfaces show the summary up front and the raw
                # text behind a "Show details" toggle.
                from ..services.error_summary import extract_error_summary
                parsed = extract_error_summary(r[3])
                last_failure = {
                    "run_id": r[0],
                    "completed_at": r[1].isoformat() if r[1] else None,
                    "status": r[2],
                    "error": parsed["summary"] or ((r[3] or "")[:500] if r[3] else None),
                    "error_details": (parsed["details"] or None) if parsed["summary"] else None,
                    "source": r[4],
                }
    except Exception as exc:
        logger.warning("get_sync_status query failed for %s: %s", plugin_id, exc)

    return {
        "current": current,
        "last_success": last_success,
        "last_failure": last_failure,
        # Back-compat: existing frontend reads `last_sync` directly. Keep
        # populating it from last_success.completed_at so a deploy that
        # ships only the backend doesn't break the old plugin page.
        "last_sync": last_success["completed_at"] if last_success else None,
    }


# ── Sync schedule overrides (B148 / v0.9.3) ───────────────────────────


def _validate_cron(cron_str: str) -> str:
    """Validate a 5-field cron expression. Returns the trimmed cron, or
    raises HTTPException(400) with a clear error."""
    if not isinstance(cron_str, str):
        raise HTTPException(400, "cron must be a string")
    cron = cron_str.strip()
    if not cron:
        raise HTTPException(400, "cron expression is empty")
    try:
        from croniter import croniter
    except ImportError:
        raise HTTPException(500, "Server missing croniter — run scripts/setup.sh")
    try:
        croniter(cron, datetime.now(timezone.utc))
    except Exception as exc:
        raise HTTPException(400, f"Invalid cron expression '{cron}': {exc}")
    return cron


def _cron_to_display(cron: Optional[str]) -> Optional[str]:
    """B205: convert simple every-N-period cron expressions to a human label.

    Returns None for non-roundtrippable expressions (caller falls back to
    showing raw cron). The frontend builder accepts the same set of shapes
    that this returns a label for — they're mirror images.

    Recognized shapes (mirror of _interval_to_cron):
        */N * * * *      -> "Every N minutes"
        0 */N * * *      -> "Every N hours"
        0 0 */N * *      -> "Every N days"
        M * * * *        -> "Every hour at :MM"
        M H * * *        -> "Daily at HH:MM"
    """
    if not cron:
        return None
    parts = cron.strip().split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts

    # Every N days: 0 0 */N * *  (must check before the (*,*,*) gate below)
    if (
        minute == "0"
        and hour == "0"
        and dom.startswith("*/")
        and month == "*"
        and dow == "*"
    ):
        try:
            n = int(dom[2:])
            if n >= 1:
                return f"Every {n} day{'s' if n != 1 else ''}"
        except ValueError:
            pass

    # Remaining shapes all require dom/month/dow to be wildcards.
    if (dom, month, dow) != ("*", "*", "*"):
        return None

    # Every N minutes: */N * * * *
    if minute.startswith("*/") and hour == "*":
        try:
            n = int(minute[2:])
            if n >= 1:
                return f"Every {n} minute{'s' if n != 1 else ''}"
        except ValueError:
            pass
    # Every N hours: 0 */N * * *
    if minute == "0" and hour.startswith("*/"):
        try:
            n = int(hour[2:])
            if n >= 1:
                return f"Every {n} hour{'s' if n != 1 else ''}"
        except ValueError:
            pass
    # Hourly at :M (minute fixed, hour wildcard): M * * * *
    if minute.isdigit() and hour == "*":
        return f"Every hour at :{int(minute):02d}"
    # Daily at H:M
    if minute.isdigit() and hour.isdigit():
        return f"Daily at {int(hour):02d}:{int(minute):02d}"
    return None


def _interval_to_cron(value: int, unit: str) -> str:
    """B205: convert a friendly interval to a 5-field cron expression.

    Raises HTTPException(400) for combinations that can't be expressed as
    a single roundtrippable cron (e.g. "every 90 minutes" — frontend builder
    constrains the input to prevent this; backend defends in depth).
    """
    if not isinstance(value, int) or value < 1:
        raise HTTPException(400, "interval_value must be an integer >= 1")
    if unit == "minutes":
        if value > 59:
            raise HTTPException(
                400,
                f"interval_value={value} for minutes is out of range — "
                f"use hours unit for >= 60 minutes",
            )
        return f"*/{value} * * * *"
    if unit == "hours":
        if value > 23:
            raise HTTPException(
                400,
                f"interval_value={value} for hours is out of range — "
                f"use days unit for >= 24 hours",
            )
        return f"0 */{value} * * *"
    if unit == "days":
        if value > 31:
            raise HTTPException(
                400,
                f"interval_value={value} for days is out of range "
                f"(max 31)",
            )
        return f"0 0 */{value} * *"
    raise HTTPException(
        400,
        f"unknown interval_unit {unit!r} — expected 'minutes', 'hours', or 'days'",
    )


@router.get(
    "/plugins/{plugin_id}/sync-schedule",
    operation_id="plugins.sync_schedule.get",
    response_model=SyncScheduleGetResponse,
    response_model_exclude_none=True,
    summary="Composite read of manifest + override + scheduler state",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def get_sync_schedule(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.configure")),
):
    """Composite read: manifest cron + override cron + scheduler registry state.

    Used by the Settings tab's schedule override block (B148).
    """
    _validate_plugin_id(plugin_id)

    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    manifest_meta = yaml.safe_load((plugin_dir / "plugin.yaml").read_text()) or {}
    manifest_cron = ((manifest_meta.get("sync") or {}).get("schedule")) or None
    if isinstance(manifest_cron, str):
        manifest_cron = manifest_cron.strip() or None

    override_cron: Optional[str] = None
    registry_row: Optional[dict] = None
    scheduler_alive = False
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM plugin_settings WHERE plugin_id = %s AND key = '_sync_schedule'",
                (plugin_id,),
            )
            row = cur.fetchone()
            if row and isinstance(row[0], str) and row[0].strip():
                override_cron = row[0].strip()

            cur.execute(
                """
                SELECT cron_expression, cron_source, next_fire_at,
                       last_enqueued_at, last_run_id, last_error, updated_at
                FROM sync_schedule_registry WHERE plugin_id = %s
                """,
                (plugin_id,),
            )
            r = cur.fetchone()
        if r:
            registry_row = {
                "cron_expression": r[0],
                "cron_source": r[1],
                "next_fire_at": r[2].isoformat() if r[2] else None,
                "last_enqueued_at": r[3].isoformat() if r[3] else None,
                "last_run_id": r[4],
                "last_error": r[5],
                "updated_at": r[6].isoformat() if r[6] else None,
            }
            if r[6]:
                age = (datetime.now(timezone.utc) - r[6]).total_seconds()
                scheduler_alive = age < 300.0
    except Exception as exc:
        logger.warning("get_sync_schedule registry read failed for %s: %s", plugin_id, exc)

    effective_cron = override_cron or manifest_cron

    return {
        "plugin_id": plugin_id,
        "manifest_cron": manifest_cron,
        "manifest_cron_display": _cron_to_display(manifest_cron),
        "override_cron": override_cron,
        "override_cron_display": _cron_to_display(override_cron),
        "effective_cron": effective_cron,
        "effective_cron_display": _cron_to_display(effective_cron),
        "source": "override" if override_cron else "manifest",
        "registry": registry_row,
        "scheduler_alive": scheduler_alive,
    }


@router.post(
    "/plugins/{plugin_id}/sync-schedule",
    operation_id="plugins.sync_schedule.set",
    response_model=SyncScheduleSetResponse,
    response_model_exclude_none=True,
    summary="Write or clear the per-plugin schedule override",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid cron, invalid interval, or both forms supplied."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.configure permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def set_sync_schedule(
    plugin_id: str,
    request: Request,
    body: SyncScheduleBody,
    _: None = Depends(requires("plugins.configure")),
):
    """Write a per-plugin schedule override.

    Body forms (mutually exclusive):
      {"cron": "0 */12 * * *"}                 raw cron
      {"interval_value": 15, "interval_unit": "minutes"}  friendly form
      {"cron": null} or {"cron": ""}           clear override

    The scheduler observes the change on its next poll (within ~30s).
    To make the change visible immediately, we delete the registry row;
    the scheduler re-creates it on next poll with the new effective cron.
    """
    _validate_plugin_id(plugin_id)

    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    # B205: resolve friendly form to a cron string. Reject if both forms
    # are supplied to avoid ambiguity.
    interval_supplied = body.interval_value is not None or body.interval_unit is not None
    cron_supplied = body.cron is not None and (
        not isinstance(body.cron, str) or body.cron.strip()
    )
    if interval_supplied and cron_supplied:
        raise HTTPException(
            400,
            "Supply either {cron} or {interval_value, interval_unit}, not both",
        )
    if interval_supplied:
        if body.interval_value is None or body.interval_unit is None:
            raise HTTPException(
                400,
                "interval_value and interval_unit must both be provided",
            )
        # Construct a cron string and fall through to the existing path.
        body = SyncScheduleBody(
            cron=_interval_to_cron(body.interval_value, body.interval_unit)
        )

    raw = body.cron
    clearing = raw is None or (isinstance(raw, str) and not raw.strip())

    if clearing:
        # Delete the override row + nudge scheduler by deleting registry row
        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM plugin_settings WHERE plugin_id = %s AND key = '_sync_schedule'",
                    (plugin_id,),
                )
                cur.execute(
                    "DELETE FROM sync_schedule_registry WHERE plugin_id = %s",
                    (plugin_id,),
                )
        except Exception as exc:
            raise HTTPException(500, f"Failed to clear override: {exc}")

        _log_plugin_action(plugin_id, "sync_schedule_clear")
        return {
            "saved": True,
            "override_cron": None,
            "preview_next_fires": [],
            "note": "Override cleared. Scheduler will fall back to manifest cron within ~30s.",
        }

    # Saving a non-empty override
    cron = _validate_cron(raw)

    # Compute preview before writing — keeps "what does this schedule mean"
    # visible to the operator in the response.
    from croniter import croniter
    now = datetime.now(timezone.utc)
    itr = croniter(cron, now)
    preview = []
    for _ in range(5):
        nxt = itr.get_next(datetime)
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=timezone.utc)
        preview.append(nxt.isoformat())

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO plugin_settings (plugin_id, key, value, updated_at)
                VALUES (%s, '_sync_schedule', to_jsonb(%s::text), NOW())
                ON CONFLICT (plugin_id, key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
                """,
                (plugin_id, cron),
            )
            cur.execute(
                "DELETE FROM sync_schedule_registry WHERE plugin_id = %s",
                (plugin_id,),
            )
    except Exception as exc:
        raise HTTPException(500, f"Failed to save override: {exc}")

    _log_plugin_action(plugin_id, "sync_schedule_set", {"cron": cron})

    return {
        "saved": True,
        "override_cron": cron,
        "preview_next_fires": preview,
        "note": "Scheduler will pick up the new schedule within ~30s.",
    }


# ── Frontend plugin components (B151 / v0.9.4) ────────────────────────


def _frontend_components_from_manifest(meta: dict) -> list[dict]:
    """Read frontend.components from a parsed manifest. Returns [] if absent."""
    fe = meta.get("frontend") if isinstance(meta, dict) else None
    if not isinstance(fe, dict):
        return []
    comps = fe.get("components") or []
    if not isinstance(comps, list):
        return []
    out: list[dict] = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        name = c.get("name")
        path = c.get("path")
        if isinstance(name, str) and isinstance(path, str):
            out.append({"name": name, "path": path})
    return out


def _is_frontend_trusted(plugin_id: str) -> bool:
    """Read plugin_settings._trust_frontend for the given plugin."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM plugin_settings WHERE plugin_id = %s AND key = '_trust_frontend'",
                (plugin_id,),
            )
            row = cur.fetchone()
        if not row:
            return False
        # JSONB: stored as boolean true, returns Python True
        return bool(row[0])
    except Exception:
        return False


@router.get(
    "/plugins/{plugin_id}/frontend-components",
    operation_id="plugins.frontend_components",
    response_model=PluginFrontendComponentsResponse,
    summary="Plugin's declared React components + trust state (B151)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.read permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
        500: {"model": ErrorDetail, "description": "Failed to read manifest."},
    },
)
async def list_frontend_components(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.read")),
):
    """List a plugin's declared frontend components and their trust state.

    Public-ish: any logged-in user can read (the frontend needs this at boot
    to know which components to dynamically import). Doesn't expose secrets.
    """
    _validate_plugin_id(plugin_id)
    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    try:
        meta = yaml.safe_load((plugin_dir / "plugin.yaml").read_text()) or {}
    except Exception as exc:
        raise HTTPException(500, f"Failed to read manifest: {exc}")

    declared = _frontend_components_from_manifest(meta)
    trusted = _is_frontend_trusted(plugin_id)
    admin_proxy = bool((meta.get("frontend") or {}).get("admin_proxy", False))

    components = []
    for comp in declared:
        # Stat-check the file under the plugin dir, with traversal defense.
        path = comp["path"]
        try:
            file_path = (plugin_dir / path).resolve()
            # Defense in depth: ensure resolved path is under the plugin dir
            in_plugin_dir = str(file_path).startswith(str(plugin_dir.resolve()) + os.sep)
            exists_on_disk = in_plugin_dir and file_path.exists() and file_path.is_file()
        except Exception:
            exists_on_disk = False
            in_plugin_dir = False
        components.append({
            "name": comp["name"],
            "path": path,
            "filename": Path(path).name,
            "exists_on_disk": bool(exists_on_disk),
        })

    return {
        "plugin_id": plugin_id,
        "components": components,
        "trusted": trusted,
        "needs_consent": bool(components) and not trusted,
        "admin_proxy": admin_proxy,
    }


@router.post(
    "/plugins/{plugin_id}/trust-frontend",
    operation_id="plugins.trust_frontend",
    response_model=TrustFrontendResponse,
    response_model_exclude_none=True,
    summary="Operator consent: trust this plugin's React components",
    responses={
        400: {"model": ErrorDetail, "description": "Plugin declares no frontend.components."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
        404: {"model": ErrorDetail, "description": "Plugin not installed."},
    },
)
async def trust_frontend(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.install")),
):
    """Operator consent: set plugin_settings._trust_frontend = true.

    Required before the frontend will dynamically import this plugin's
    declared React components. Audited via plugin_audit_log so revocation
    history is queryable.
    """
    _validate_plugin_id(plugin_id)
    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    try:
        meta = yaml.safe_load((plugin_dir / "plugin.yaml").read_text()) or {}
    except Exception as exc:
        raise HTTPException(500, f"Failed to read manifest: {exc}")

    declared = _frontend_components_from_manifest(meta)
    if not declared:
        raise HTTPException(
            400,
            f"Plugin '{plugin_id}' does not declare any frontend.components — nothing to trust",
        )

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO plugin_settings (plugin_id, key, value, updated_at)
                VALUES (%s, '_trust_frontend', 'true'::jsonb, NOW())
                ON CONFLICT (plugin_id, key) DO UPDATE SET
                    value = 'true'::jsonb, updated_at = NOW()
                """,
                (plugin_id,),
            )
    except Exception as exc:
        raise HTTPException(500, f"Failed to record trust: {exc}")

    _log_plugin_action(
        plugin_id,
        "frontend_trust_granted",
        {"components": [c["name"] for c in declared]},
    )

    return {
        "plugin_id": plugin_id,
        "trusted": True,
        "components": declared,
    }


@router.post(
    "/plugins/{plugin_id}/revoke-frontend-trust",
    operation_id="plugins.revoke_frontend_trust",
    response_model=RevokeFrontendTrustResponse,
    summary="Operator revoke: clear plugin frontend trust",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the plugins.install permission."},
    },
)
async def revoke_frontend_trust(
    plugin_id: str,
    request: Request,
    _: None = Depends(requires("plugins.install")),
):
    """Operator revoke: clear plugin_settings._trust_frontend.

    Idempotent — calling on an already-untrusted plugin returns success.
    """
    _validate_plugin_id(plugin_id)

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM plugin_settings WHERE plugin_id = %s AND key = '_trust_frontend'",
                (plugin_id,),
            )
    except Exception as exc:
        raise HTTPException(500, f"Failed to revoke trust: {exc}")

    _log_plugin_action(plugin_id, "frontend_trust_revoked")

    return {"plugin_id": plugin_id, "trusted": False}


@router.get(
    "/plugins/{plugin_id}/widget/{filename}",
    operation_id="plugins.widget_asset",
    summary="Serve a plugin's bundled JS widget asset",
    responses={
        200: {"content": {"application/javascript": {}}, "description": "Widget JS bundle."},
        400: {"model": ErrorDetail, "description": "Invalid filename (must be `[A-Za-z0-9._-]+\\.js`)."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Plugin frontend not trusted by operator."},
        404: {"model": ErrorDetail, "description": "Plugin not installed or filename not declared."},
    },
)
async def serve_plugin_widget(
    plugin_id: str,
    filename: str,
    _: None = Depends(requires("plugins.read")),
):
    """Serve a plugin's bundled JS widget file.

    Refuses unless:
      - Plugin exists + has a manifest
      - Plugin is trusted (operator consented via /trust-frontend)
      - Filename matches a declared component's path basename
      - File exists on disk inside the plugin dir
      - Resolved path is contained within the plugin dir (no traversal)
    """
    _validate_plugin_id(plugin_id)
    # Filename validation: alphanumerics, dot, hyphen, underscore. No slashes.
    if not re.match(r"^[A-Za-z0-9._-]+\.js$", filename):
        raise HTTPException(400, f"Invalid widget filename: {filename!r}")

    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists() or not (plugin_dir / "plugin.yaml").exists():
        raise HTTPException(404, f"Plugin '{plugin_id}' is not installed")

    if not _is_frontend_trusted(plugin_id):
        raise HTTPException(
            403,
            f"Plugin '{plugin_id}' frontend code is not trusted. "
            f"An admin must consent via Settings → Plugins → Trust frontend code.",
        )

    try:
        meta = yaml.safe_load((plugin_dir / "plugin.yaml").read_text()) or {}
    except Exception as exc:
        raise HTTPException(500, f"Failed to read manifest: {exc}")

    declared = _frontend_components_from_manifest(meta)
    # Find the declared component whose path basename matches filename
    matched_path: Optional[str] = None
    for comp in declared:
        if Path(comp["path"]).name == filename:
            matched_path = comp["path"]
            break

    if matched_path is None:
        raise HTTPException(
            404,
            f"Plugin '{plugin_id}' does not declare a frontend component with filename {filename!r}",
        )

    # Resolve under plugin dir; refuse if the resolved file escapes.
    try:
        plugin_root = plugin_dir.resolve()
        file_path = (plugin_dir / matched_path).resolve()
        if not str(file_path).startswith(str(plugin_root) + os.sep):
            raise HTTPException(400, "Path traversal blocked")
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(404, f"Widget bundle not found at {matched_path!r}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to resolve widget path: {exc}")

    # Build response with ETag based on mtime (cheap cache invalidation).
    from fastapi.responses import FileResponse
    import hashlib
    try:
        mtime = file_path.stat().st_mtime
    except Exception:
        mtime = 0
    etag = hashlib.sha256(f"{plugin_id}:{matched_path}:{mtime}".encode()).hexdigest()[:16]
    headers = {
        "ETag": etag,
        "Cache-Control": "private, max-age=60",
    }
    return FileResponse(
        path=str(file_path),
        media_type="application/javascript",
        headers=headers,
    )
