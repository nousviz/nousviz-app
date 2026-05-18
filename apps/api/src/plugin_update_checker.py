"""
plugin_update_checker — discover available plugin updates (B144 / v0.9.2.4).

Two source classes:
  - first_party: plugin code lives in the core repo at plugins/{official,utilities}/<slug>/.
                 "Latest" is the version: in that catalog manifest.
  - git: plugin was cloned from a repository_url. "Latest" is the highest
         semver-compatible tag returned by `git ls-remote --tags <url>`.

Status is cached in plugin_update_status (migration 049) for ~1h. The
GET /api/plugins endpoint triggers async refreshes for stale entries so
the UI sees fresh data without blocking the request.

# Why git ls-remote vs the GitHub API

ls-remote works against any git remote (GitLab, self-hosted, etc.), needs
no auth for public repos, and isn't rate-limited. The GitHub API has a
60 req/h unauthenticated cap which would burn out fast on a NousViz with
many plugins installed.

# Semver tolerance

Tags don't always look like v1.2.3. We accept:
  - v1.2.3
  - 1.2.3
  - 1.2.3-rc.1 (pre-release)
  - 1.2.3.4 (Microsoft-style four-component — rare)

Anything we can't parse is skipped. If no tags parse, we report no
update (better silent than crashing the UI).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml

from .db import get_pg_conn

logger = logging.getLogger("nousviz.api.plugin_update_checker")

REPO_ROOT = Path(__file__).resolve().parents[3]
OFFICIAL_DIR = REPO_ROOT / "plugins" / "official"
UTILITIES_DIR = REPO_ROOT / "plugins" / "utilities"
INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"

# Cache TTL. After this, GET /api/plugins kicks off a refresh.
CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# git ls-remote timeout. Keep tight so a wedged remote doesn't block other plugins.
LS_REMOTE_TIMEOUT_SEC = 8


# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class UpdateStatus:
    plugin_id: str
    source_class: str  # "first_party" | "git"
    source_url: Optional[str]
    installed_version: Optional[str]
    latest_version: Optional[str]
    update_available: bool
    last_error: Optional[str]


# ── Source class detection ───────────────────────────────────────────


def detect_source_class(plugin_id: str) -> tuple[str, Optional[str]]:
    """Return (source_class, source_url) for an installed plugin.

    source_class is one of:
      - "first_party": the plugin's catalog source is in this repo
      - "git": the plugin was installed from a remote repository_url
      - "unknown": couldn't determine (manifest missing, etc.)

    source_url is the repository URL for git installs, None otherwise.
    """
    installed_yaml = INSTALLED_DIR / plugin_id / "plugin.yaml"
    if not installed_yaml.exists():
        return ("unknown", None)

    try:
        installed_meta = yaml.safe_load(installed_yaml.read_text()) or {}
    except Exception:
        return ("unknown", None)

    # First check: is there a catalog source in plugins/{official,utilities}/<slug>?
    for catalog_dir in (UTILITIES_DIR, OFFICIAL_DIR):
        catalog_yaml = catalog_dir / plugin_id / "plugin.yaml"
        if catalog_yaml.exists():
            return ("first_party", None)

    # Otherwise, look for a repository URL in the installed manifest.
    # Plugins use a few different shapes — accept all of them:
    #   - repository_url: <url>           (NousViz install handler convention)
    #   - repository: <url>               (top-level — common in plugin authors' manifests)
    #   - publisher.repository: <url>     (nested under publisher)
    repo_url = (
        installed_meta.get("repository_url")
        or installed_meta.get("repository")
        or (installed_meta.get("publisher") or {}).get("repository")
    )
    if isinstance(repo_url, str) and repo_url.strip():
        return ("git", repo_url.strip())

    return ("unknown", None)


# ── Version reading ──────────────────────────────────────────────────


def read_installed_version(plugin_id: str) -> Optional[str]:
    """Read the version: from the plugin's installed manifest."""
    p = INSTALLED_DIR / plugin_id / "plugin.yaml"
    if not p.exists():
        return None
    try:
        m = yaml.safe_load(p.read_text()) or {}
        v = m.get("version")
        return str(v) if v else None
    except Exception:
        return None


def read_first_party_latest(plugin_id: str) -> Optional[str]:
    """Read the version: from the bundled catalog manifest (first-party)."""
    for catalog_dir in (UTILITIES_DIR, OFFICIAL_DIR):
        p = catalog_dir / plugin_id / "plugin.yaml"
        if p.exists():
            try:
                m = yaml.safe_load(p.read_text()) or {}
                v = m.get("version")
                return str(v) if v else None
            except Exception:
                return None
    return None


# ── Semver-tolerant version comparison ───────────────────────────────


_VERSION_RE = re.compile(
    r"""
    ^
    v?                          # optional leading v
    (\d+)\.(\d+)\.(\d+)         # major.minor.patch
    (?:\.(\d+))?                # optional .build (Microsoft-style)
    (?:-([\w.]+))?              # optional -prerelease
    $
    """,
    re.VERBOSE,
)


def parse_version(s: str) -> Optional[tuple]:
    """Parse a version string into a sortable tuple. Returns None if unparseable.

    Comparable: pre-release sorts BEFORE the same release without one
    (1.2.3-rc.1 < 1.2.3). Build component (4-tuple) extends the version.
    """
    if not s:
        return None
    m = _VERSION_RE.match(s.strip())
    if not m:
        return None
    major, minor, patch, build, prerelease = m.groups()
    # Pre-release sorts before release: encode "no prerelease" as ZZZ
    # (greater than any actual identifier so 1.2.3-rc < 1.2.3)
    pre_key = (0, prerelease) if prerelease else (1, "")
    return (int(major), int(minor), int(patch), int(build) if build else 0, pre_key)


def is_newer(latest: Optional[str], installed: Optional[str]) -> bool:
    """True if `latest` parses to a strictly higher version than `installed`."""
    lt, it = parse_version(latest or ""), parse_version(installed or "")
    if lt is None or it is None:
        return False
    return lt > it


# ── git ls-remote ────────────────────────────────────────────────────


def _extract_host(repo_url: str) -> str:
    """Pull the hostname out of a repo URL (SSH or HTTPS form). Defaults to github.com."""
    if repo_url.startswith("git@"):
        # git@github.com:foo/bar.git
        try:
            return repo_url.split("@", 1)[1].split(":", 1)[0]
        except Exception:
            return "github.com"
    parsed = urlparse(repo_url)
    return parsed.hostname or "github.com"


def fetch_latest_git_tag(repo_url: str) -> Optional[str]:
    """Run `git ls-remote --tags <repo_url>` and return the highest semver tag.

    Resolves a deploy key from the deploy_keys table (per-repo, host fallback)
    and uses it via GIT_SSH_COMMAND so private SSH-cloned plugins authenticate
    correctly — same auth flow as the install handler uses.

    Returns None if no tags or all tags are unparseable. Raises only on
    truly fatal errors (ls-remote exit, timeout).
    """
    git = shutil.which("git")
    if not git:
        logger.warning("git binary not found on PATH — cannot check for updates")
        return None

    # Resolve deploy key for SSH URLs (or any URL that has a registered key).
    # Lazy-import to avoid circular: routes/plugins imports this module too.
    key_path: Optional[str] = None
    try:
        from .routes.plugins import _get_deploy_key_path
        host = _extract_host(repo_url)
        key_path = _get_deploy_key_path(host, repo_url)
    except Exception as exc:
        logger.debug("deploy key lookup failed for %s: %s", repo_url, exc)

    env = os.environ.copy()
    if key_path:
        # Match the install handler's SSH config (StrictHostKeyChecking=no for non-interactive).
        env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o BatchMode=yes"
    else:
        # Fall back to BatchMode=yes so missing keys fail fast instead of prompting.
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o BatchMode=yes"

    try:
        try:
            proc = subprocess.run(
                [git, "ls-remote", "--tags", "--refs", repo_url],
                capture_output=True,
                text=True,
                timeout=LS_REMOTE_TIMEOUT_SEC,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git ls-remote timed out after {LS_REMOTE_TIMEOUT_SEC}s")

        if proc.returncode != 0:
            raise RuntimeError(f"git ls-remote failed (rc={proc.returncode}): {(proc.stderr or '').strip()[:200]}")
    finally:
        # Best-effort cleanup of the temp key file (created by _get_deploy_key_path)
        if key_path and os.path.exists(key_path):
            try:
                os.unlink(key_path)
            except Exception:
                pass

    # Output format: "<sha>\trefs/tags/<tag>\n"
    candidates: list[tuple[tuple, str]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        ref = parts[1]
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/"):]
        # Strip dereferenced peel (^{}) — we want the tag itself, not the commit it dereferences to
        if tag.endswith("^{}"):
            continue
        parsed = parse_version(tag)
        if parsed is not None:
            candidates.append((parsed, tag))

    if not candidates:
        return None
    candidates.sort()
    # Normalize: strip leading 'v' so callers see plain semver consistently
    # (manifest version: fields don't have a v-prefix; tags often do).
    # NOTE: callers that need the ORIGINAL tag for `git clone --branch`
    # must use fetch_latest_git_tag_with_ref() — this function loses the
    # `v` prefix on purpose (B146 normalization for display + version
    # comparison). Mixing them was the v0.9.4.3 update bug — see B152.
    tag = candidates[-1][1]
    return tag[1:] if tag.startswith("v") else tag


def fetch_latest_git_tag_with_ref(repo_url: str) -> Optional[tuple[str, str]]:
    """Like fetch_latest_git_tag, but returns BOTH the original tag ref
    (for `git clone --branch`) AND the normalized version (for display
    + comparison). Returns None if no semver tags found.

    Returns (tag_ref, normalized_version):
      - tag_ref: the actual tag as it exists upstream — `v0.3.0` or `0.3.0`,
        whichever the author pushed. Pass this to `git clone --branch`.
      - normalized_version: same value with leading `v` stripped.
        Compare this against plugin.yaml's `version:` field.

    The two MUST stay distinct because git refs are case-sensitive byte-
    matches: `git clone --branch 0.3.0` against an upstream that only has
    `v0.3.0` fails with 'Remote branch 0.3.0 not found'. (B152 / v0.9.4.4.)
    """
    # Reuse fetch_latest_git_tag's full machinery via a small helper. We
    # could share more code but the duplication is small and avoids a
    # second `git ls-remote` call.
    git = shutil.which("git")
    if not git:
        logger.warning("git binary not found on PATH — cannot check for updates")
        return None

    key_path: Optional[str] = None
    try:
        from .routes.plugins import _get_deploy_key_path
        host = _extract_host(repo_url)
        key_path = _get_deploy_key_path(host, repo_url)
    except Exception as exc:
        logger.debug("deploy key lookup failed for %s: %s", repo_url, exc)

    env = os.environ.copy()
    if key_path:
        env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o StrictHostKeyChecking=no -o BatchMode=yes"
    else:
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o BatchMode=yes"

    try:
        try:
            proc = subprocess.run(
                [git, "ls-remote", "--tags", "--refs", repo_url],
                capture_output=True,
                text=True,
                timeout=LS_REMOTE_TIMEOUT_SEC,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git ls-remote timed out after {LS_REMOTE_TIMEOUT_SEC}s")

        if proc.returncode != 0:
            raise RuntimeError(f"git ls-remote failed (rc={proc.returncode}): {(proc.stderr or '').strip()[:200]}")
    finally:
        if key_path and os.path.exists(key_path):
            try:
                os.unlink(key_path)
            except Exception:
                pass

    candidates: list[tuple[tuple, str]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        ref = parts[1]
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/"):]
        if tag.endswith("^{}"):
            continue
        parsed = parse_version(tag)
        if parsed is not None:
            candidates.append((parsed, tag))

    if not candidates:
        return None
    candidates.sort()
    original_ref = candidates[-1][1]
    normalized = original_ref[1:] if original_ref.startswith("v") else original_ref
    return (original_ref, normalized)


# ── Cache layer ──────────────────────────────────────────────────────


def get_cached_status(plugin_id: str) -> Optional[UpdateStatus]:
    """Read latest cached row for plugin_id. Returns None if no row yet."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT plugin_id, source_class, source_url, installed_version,
                       latest_version, update_available, last_error, checked_at
                FROM plugin_update_status
                WHERE plugin_id = %s
                """,
                (plugin_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return UpdateStatus(
            plugin_id=row[0],
            source_class=row[1] or "unknown",
            source_url=row[2],
            installed_version=row[3],
            latest_version=row[4],
            update_available=bool(row[5]),
            last_error=row[6],
        )
    except Exception as exc:
        logger.warning("get_cached_status DB read failed for %s: %s", plugin_id, exc)
        return None


def is_stale(plugin_id: str) -> bool:
    """True if the cached row is older than CACHE_TTL_SECONDS or absent."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT (NOW() - checked_at) > make_interval(secs => %s)
                FROM plugin_update_status WHERE plugin_id = %s
                """,
                (CACHE_TTL_SECONDS, plugin_id),
            )
            row = cur.fetchone()
        return row is None or bool(row[0])
    except Exception:
        return True


def upsert_status(status: UpdateStatus) -> None:
    """Write/update the cache row."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO plugin_update_status (
                    plugin_id, source_class, source_url,
                    installed_version, latest_version, update_available,
                    last_error, checked_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (plugin_id) DO UPDATE SET
                    source_class      = EXCLUDED.source_class,
                    source_url        = EXCLUDED.source_url,
                    installed_version = EXCLUDED.installed_version,
                    latest_version    = EXCLUDED.latest_version,
                    update_available  = EXCLUDED.update_available,
                    last_error        = EXCLUDED.last_error,
                    checked_at        = EXCLUDED.checked_at
                """,
                (
                    status.plugin_id,
                    status.source_class,
                    status.source_url,
                    status.installed_version,
                    status.latest_version,
                    status.update_available,
                    status.last_error,
                ),
            )
    except Exception as exc:
        logger.warning("upsert_status failed for %s: %s", status.plugin_id, exc)


# ── Top-level check ──────────────────────────────────────────────────


def check_plugin(plugin_id: str) -> UpdateStatus:
    """Synchronously check a single plugin and write the result to cache.

    Idempotent. Always returns a status (never raises) — a check that hits
    a network error reports `last_error` and `update_available=False`.
    """
    source_class, source_url = detect_source_class(plugin_id)
    installed = read_installed_version(plugin_id)
    latest: Optional[str] = None
    last_error: Optional[str] = None

    try:
        if source_class == "first_party":
            latest = read_first_party_latest(plugin_id)
        elif source_class == "git" and source_url:
            latest = fetch_latest_git_tag(source_url)
        elif source_class == "unknown":
            last_error = "Source unknown — manifest missing or no repository_url"
    except Exception as exc:
        last_error = str(exc)[:500]
        # B203/B204: surface to /system/logs so operators can diagnose
        # without SSH. If the failure looks like an SSH auth error AND
        # no per-repo deploy key is registered, augment the message with
        # the actionable hint (B204).
        hint = ""
        if source_class == "git" and source_url and source_url.startswith("git@"):
            try:
                from .routes.plugins import _get_deploy_key_path
                host = _extract_host(source_url)
                if not _get_deploy_key_path(host, source_url):
                    hint = (
                        f" — no deploy key registered for {source_url}. "
                        f"Add one at Settings → Deploy Keys."
                    )
            except Exception:
                pass
        try:
            from .log_events import log_plugin_event
            log_plugin_event(
                "error",
                plugin_id,
                "update_check",
                last_error + hint,
                detail={"source_class": source_class, "source_url": source_url},
                source="plugin_update",
            )
        except Exception:
            pass
        if hint:
            last_error = (last_error + hint)[:500]

    update_available = bool(latest and installed and is_newer(latest, installed))

    status = UpdateStatus(
        plugin_id=plugin_id,
        source_class=source_class,
        source_url=source_url,
        installed_version=installed,
        latest_version=latest,
        update_available=update_available,
        last_error=last_error,
    )
    upsert_status(status)
    return status


# ── Lazy fan-out (used by GET /api/plugins) ──────────────────────────


def schedule_async_check(plugin_id: str) -> None:
    """Fire-and-forget update check for a plugin. Non-blocking.

    Uses a background thread so the GET /api/plugins request that
    triggered it doesn't wait. Errors swallowed (already cached).
    """
    import threading
    threading.Thread(target=_safe_check, args=(plugin_id,), daemon=True).start()


def _safe_check(plugin_id: str) -> None:
    try:
        check_plugin(plugin_id)
    except Exception as exc:
        logger.warning("async update check failed for %s: %s", plugin_id, exc)
        # B203: also surface to operator logs.
        try:
            from .log_events import log_plugin_event
            log_plugin_event(
                "error",
                plugin_id,
                "update_check",
                f"async update check failed: {str(exc)[:300]}",
                source="plugin_update",
            )
        except Exception:
            pass
