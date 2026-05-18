"""
Nousviz unit tests — offline, no API or DB required.

Run: `pytest tests/test_unit.py -v`

P62 (v0.3.0) expands this file to the ~55-test baseline covering manifest
validation, auth hashing, rate-limiter state, error sanitisation, etc.

For now: B190 regression coverage for _get_ssl_status (no cache leak across
calls — the multi-worker env drift fix).
"""

import os
import sys
from pathlib import Path

import pytest

# Make apps/api/src importable as a package
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── B190: _get_ssl_status has no cross-call cache on the env read ─────────


@pytest.fixture(autouse=True)
def clear_ssl_env(monkeypatch):
    """Every test starts with NOUSVIZ_SSL / NOUSVIZ_DOMAIN unset."""
    monkeypatch.delenv("NOUSVIZ_SSL", raising=False)
    monkeypatch.delenv("NOUSVIZ_DOMAIN", raising=False)
    # Also clear the cert-expiry cache so mtime-based caching doesn't leak
    from apps.api.src.routes import health as _health
    _health._cert_expiry_cache.clear()


def test_get_ssl_status_returns_none_when_unset():
    from apps.api.src.routes.health import _get_ssl_status
    assert _get_ssl_status() is None


def test_get_ssl_status_reflects_env_change_without_restart(monkeypatch):
    """B190 regression: repeated calls must reflect the current os.environ.

    Before the fix, _get_ssl_status cached the None result for 1 hour. After a
    setup flow that flipped NOUSVIZ_SSL to 'letsencrypt', subsequent calls
    from a non-handling worker would still return None for up to 3600s.
    """
    from apps.api.src.routes.health import _get_ssl_status

    # 1. First call: SSL not configured
    assert _get_ssl_status() is None

    # 2. SSL gets configured (simulates the setup endpoint patching os.environ
    #    and other workers receiving the pm2 reload --update-env)
    monkeypatch.setenv("NOUSVIZ_SSL", "letsencrypt")
    monkeypatch.setenv("NOUSVIZ_DOMAIN", "example.com")

    # 3. Next call must reflect the new env — no stale None from cache
    result = _get_ssl_status()
    assert result is not None
    assert result["enabled"] is True
    assert result["type"] == "letsencrypt"
    assert result["domain"] == "example.com"

    # 4. If SSL gets un-configured later, the call must reflect that too
    monkeypatch.delenv("NOUSVIZ_SSL")
    assert _get_ssl_status() is None


def test_get_ssl_status_no_cached_leak_between_calls(monkeypatch):
    """Flipping env back and forth returns correct result each time."""
    from apps.api.src.routes.health import _get_ssl_status

    for _ in range(5):
        monkeypatch.setenv("NOUSVIZ_SSL", "letsencrypt")
        monkeypatch.setenv("NOUSVIZ_DOMAIN", "a.example.com")
        assert _get_ssl_status() == {
            "enabled": True,
            "type": "letsencrypt",
            "domain": "a.example.com",
        }
        monkeypatch.delenv("NOUSVIZ_SSL")
        assert _get_ssl_status() is None


def test_get_ssl_status_empty_string_is_not_configured(monkeypatch):
    """Empty NOUSVIZ_SSL (not unset, just empty) should still return None."""
    from apps.api.src.routes.health import _get_ssl_status

    monkeypatch.setenv("NOUSVIZ_SSL", "")
    monkeypatch.setenv("NOUSVIZ_DOMAIN", "")
    assert _get_ssl_status() is None


def test_get_ssl_status_strips_whitespace(monkeypatch):
    """Leading/trailing whitespace in env vars shouldn't count as 'configured'."""
    from apps.api.src.routes.health import _get_ssl_status

    monkeypatch.setenv("NOUSVIZ_SSL", "   ")
    assert _get_ssl_status() is None


# ── B190: write_and_reload patches os.environ synchronously ───────────────


def test_write_and_reload_patches_environ_before_scheduling(monkeypatch, tmp_path):
    """write_and_reload must update os.environ BEFORE the caller returns, so
    the handling worker sees new values in the same request."""
    import apps.api.src._env as env_mod

    # Redirect .env to a temp file so we don't touch the real one
    monkeypatch.setattr(env_mod, "ENV_FILE", tmp_path / ".env")
    # Stub out the PM2 reload scheduler — we only want to verify the sync parts
    calls = []
    monkeypatch.setattr(env_mod, "_schedule_pm2_reload", lambda *a, **kw: calls.append("scheduled"))

    monkeypatch.delenv("TEST_B190_KEY", raising=False)
    env_mod.write_and_reload({"TEST_B190_KEY": "new_value"})

    # os.environ patched synchronously
    assert os.environ.get("TEST_B190_KEY") == "new_value"
    # .env written synchronously
    assert (tmp_path / ".env").read_text().strip() == "TEST_B190_KEY=new_value"
    # pm2 reload scheduled exactly once
    assert calls == ["scheduled"]

    # Cleanup — the fixture doesn't cover TEST_B190_KEY
    monkeypatch.delenv("TEST_B190_KEY", raising=False)


# ── B193: schedule max-age + status classification + cron source ──────


def test_schedule_max_age_known_patterns():
    from apps.api.src.routes.jobs import _schedule_max_age
    from datetime import timedelta

    assert _schedule_max_age("*/5 * * * *") == timedelta(minutes=5)
    assert _schedule_max_age("0 * * * *") == timedelta(hours=1)
    assert _schedule_max_age("0 */4 * * *") == timedelta(hours=4)
    assert _schedule_max_age("0 6 * * *") == timedelta(hours=24)
    assert _schedule_max_age("0 0 * * 1") == timedelta(days=7)


def test_schedule_max_age_unknown_defaults_to_24h():
    from apps.api.src.routes.jobs import _schedule_max_age
    from datetime import timedelta

    assert _schedule_max_age("42 3 * 1-6 *") == timedelta(hours=24)
    assert _schedule_max_age("") == timedelta(hours=24)
    assert _schedule_max_age("not even a cron expression") == timedelta(hours=24)


def test_classify_status_never_when_no_last_run():
    from apps.api.src.routes.jobs import _classify_status
    assert _classify_status(None, "0 * * * *") == "never"
    assert _classify_status("", "0 * * * *") == "never"


def test_classify_status_ok_when_recent(monkeypatch):
    from apps.api.src.routes.jobs import _classify_status
    from datetime import datetime, timezone, timedelta

    # Last run 30 minutes ago on an hourly schedule → ok (within 2× = 2h)
    recent = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    assert _classify_status(recent, "0 * * * *") == "ok"


def test_classify_status_stale_when_past_threshold():
    from apps.api.src.routes.jobs import _classify_status
    from datetime import datetime, timezone, timedelta

    # Last run 3 hours ago on an hourly schedule → stale (beyond 2× = 2h)
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    assert _classify_status(old, "0 * * * *") == "stale"

    # Health-monitor specific: 15 min old on 5-min schedule → stale (2× = 10 min)
    old_health = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    assert _classify_status(old_health, "*/5 * * * *") == "stale"


def test_classify_cron_source():
    from apps.api.src.routes.jobs import _classify_cron_source

    assert _classify_cron_source([], []) == "none"
    assert _classify_cron_source([{"source": "crontab"}], []) == "crontab"
    assert _classify_cron_source([], [{"source": "pm2"}]) == "pm2"
    assert _classify_cron_source([{"source": "crontab"}], [{"source": "pm2"}]) == "both"


def test_cron_active_matches_command_substring():
    from apps.api.src.routes.jobs import _cron_active

    entries = [
        {"source": "pm2", "name": "alerts", "command": "apps/worker/src/run_alerts.py"},
        {"source": "pm2", "name": "health-monitor", "command": "curl -X POST http://127.0.0.1:8000/api/health/record"},
    ]
    # Matches on command
    is_active, source = _cron_active(["run_alerts"], entries)
    assert is_active is True
    assert source == "pm2"

    # Matches on name
    is_active, source = _cron_active(["health/record"], entries)
    assert is_active is True
    assert source == "pm2"

    # No match
    is_active, source = _cron_active(["nonexistent-plugin"], entries)
    assert is_active is False
    assert source is None


# ═══════════════════════════════════════════════════════════════════════
# P62: expanded unit test baseline
# ═══════════════════════════════════════════════════════════════════════


# ── Query guardrails ──────────────────────────────────────────────────


def test_enforce_limit_adds_limit_when_missing():
    from apps.api.src.routes.query import _enforce_limit
    assert _enforce_limit("SELECT * FROM t", 100) == "SELECT * FROM t LIMIT 100"


def test_enforce_limit_caps_existing_high_limit():
    from apps.api.src.routes.query import _enforce_limit
    result = _enforce_limit("SELECT * FROM t LIMIT 50000", 1000)
    assert "LIMIT 1000" in result
    assert "50000" not in result


def test_enforce_limit_keeps_existing_low_limit():
    from apps.api.src.routes.query import _enforce_limit
    result = _enforce_limit("SELECT * FROM t LIMIT 50", 1000)
    assert "LIMIT 50" in result


def test_blocked_patterns_catches_writes():
    from apps.api.src.routes.query import BLOCKED_PATTERNS
    for word in ["DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE", "ALTER", "CREATE"]:
        assert BLOCKED_PATTERNS.search(f"{word} TABLE foo"), f"{word} should be blocked"


def test_blocked_patterns_allows_select():
    from apps.api.src.routes.query import BLOCKED_PATTERNS
    assert BLOCKED_PATTERNS.search("SELECT * FROM foo LIMIT 10") is None


def test_pg_blocked_tables_blocks_sensitive():
    from apps.api.src.routes.query import PG_BLOCKED_TABLES
    for table in ["users", "user_sessions", "user_activity", "api_keys", "alert_rules"]:
        assert PG_BLOCKED_TABLES.search(f"SELECT * FROM {table}"), f"{table} should be blocked"


def test_pg_blocked_tables_allows_plugin_tables():
    from apps.api.src.routes.query import PG_BLOCKED_TABLES
    assert PG_BLOCKED_TABLES.search("SELECT * FROM hello_items") is None
    assert PG_BLOCKED_TABLES.search("SELECT * FROM fusions") is None


# ── Plugin ID validation ──────────────────────────────────────────────


def test_validate_plugin_id_accepts_valid():
    from apps.api.src.routes.plugins import _validate_plugin_id
    for slug in ["starter-plugin", "my_plugin", "a123", "x"]:
        _validate_plugin_id(slug)


def test_validate_plugin_id_rejects_traversal():
    from apps.api.src.routes.plugins import _validate_plugin_id
    from fastapi import HTTPException
    for slug in ["../etc/passwd", "a/b", ".hidden", "UPPERCASE", "", "a" * 100]:
        with pytest.raises(HTTPException):
            _validate_plugin_id(slug)


# ── Repository URL validation (SSRF prevention) ──────────────────────


def test_validate_repo_url_accepts_https():
    from apps.api.src.routes.plugins import _validate_repo_url
    url = _validate_repo_url("https://github.com/user/repo")
    assert url.endswith(".git")
    assert url.startswith("https://")


def test_validate_repo_url_rejects_unsafe_schemes():
    from apps.api.src.routes.plugins import _validate_repo_url
    from fastapi import HTTPException
    for bad in ["http://example.com/repo", "file:///etc/passwd", "ftp://host/repo"]:
        with pytest.raises(HTTPException):
            _validate_repo_url(bad)
    # SSH and HTTPS should be accepted
    assert _validate_repo_url("git@github.com:org/repo.git") == "git@github.com:org/repo.git"
    assert _validate_repo_url("https://github.com/org/repo").endswith(".git")


def test_validate_repo_url_rejects_private_ips():
    from apps.api.src.routes.plugins import _validate_repo_url
    from fastapi import HTTPException
    for bad in ["https://127.0.0.1/repo", "https://192.168.1.1/repo", "https://10.0.0.1/repo", "https://localhost/repo"]:
        with pytest.raises(HTTPException):
            _validate_repo_url(bad)


# ── Auth middleware — public route matching ────────────────────────────


def test_is_public_route_health():
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route("/api/health", "GET") is True
    assert is_public_route("/api/health/config", "GET") is True


def test_is_public_route_auth_status():
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route("/api/auth/status", "GET") is True
    assert is_public_route("/api/auth/login", "POST") is True


def test_is_public_route_blocks_settings():
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route("/api/settings/database", "GET") is False
    assert is_public_route("/api/settings/api-keys", "POST") is False


def test_is_public_route_blocks_data_port():
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route("/api/data-port/plugins", "GET") is False


def test_is_public_route_plugins_get_only():
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route("/api/plugins/starter-plugin", "GET") is True
    assert is_public_route("/api/plugins/starter-plugin/install", "POST") is False


# ── B160: plugin route allowlist is exact, not prefix ────────────────
# Before v0.9.4.9, PUBLIC_GET_PREFIXES contained "/api/plugins/" which made
# every GET under that namespace public — including plugin-shipped data
# routes (/overview, /programs, etc.) and core admin routes
# (/audit-log, /updates, /{id}/connections, /{id}/sync/status). v0.9.4.9
# narrowed this to a regex allowlist matching exactly the four shapes
# share-viewers + the host loader need.

B160_PUBLIC_GET = [
    "/api/plugins",
    "/api/plugins/",
    "/api/plugins/example-plugin",
    "/api/plugins/example-plugin/",
    "/api/plugins/example-plugin/dashboards/overview",
    "/api/plugins/example-plugin/dashboards/overview/",
    "/api/plugins/example-plugin/widget/SDIMiniBarList.js",
    "/api/plugins/starter-plugin/widget/Greeter.js",
    "/api/widget-runtime/react.js",
    "/api/widget-runtime/react-jsx-runtime.js",
]

B160_BLOCKED_GET = [
    # Plugin-shipped data routes (the actual leak)
    "/api/plugins/example-plugin/overview",
    "/api/plugins/example-plugin/programs",
    "/api/plugins/example-plugin/brands",
    "/api/plugins/example-plugin/sync-report/2026-04-25",
    # Core admin endpoints under /api/plugins/
    "/api/plugins/example-plugin/connections",
    "/api/plugins/example-plugin/sync/status",
    "/api/plugins/example-plugin/sync-schedule",
    "/api/plugins/example-plugin/settings",
    "/api/plugins/example-plugin/modules",
    "/api/plugins/example-plugin/uninstall-check",
    "/api/plugins/example-plugin/datasets/programs",
    "/api/plugins/example-plugin/alerts/sync-stale",
    "/api/plugins/example-plugin/frontend-components",
    "/api/plugins/audit-log",
    "/api/plugins/updates",
    "/api/plugins/capabilities",
    "/api/plugins/catalog",
]


@pytest.mark.parametrize("path", B160_PUBLIC_GET)
def test_b160_public_get_paths(path):
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route(path, "GET") is True, f"{path} should be public on GET"


@pytest.mark.parametrize("path", B160_BLOCKED_GET)
def test_b160_blocked_get_paths(path):
    from apps.api.src.middleware.auth import is_public_route
    assert is_public_route(path, "GET") is False, f"{path} must require auth (B160)"


@pytest.mark.parametrize("path", B160_PUBLIC_GET)
def test_b160_public_get_paths_only_for_get(path):
    """Public allowlist is GET-only; POST/DELETE on the same path must require auth."""
    from apps.api.src.middleware.auth import is_public_route
    # Skip widget-runtime; modify is GET-only by design but the path itself
    # has no other methods. Test on the plugin-namespace paths.
    if path.startswith("/api/widget-runtime/"):
        return
    assert is_public_route(path, "POST") is False, f"POST {path} must require auth"
    assert is_public_route(path, "DELETE") is False, f"DELETE {path} must require auth"


def test_b160_slug_pattern_does_not_match_nested():
    """The {slug} regex uses [^/]+ so it can't match nested paths via greedy matching."""
    from apps.api.src.middleware.auth import is_public_route
    # /api/plugins/foo/bar would match a hypothetical greedy regex; with [^/]+ it won't.
    assert is_public_route("/api/plugins/foo/bar", "GET") is False
    # Dashboard pattern requires exactly /dashboards/ between slug and name
    assert is_public_route("/api/plugins/foo/dashboardsfake/bar", "GET") is False


# ── B169 (v0.9.5.1): _merge_module_manifests dedupes tables ──────────
# Pre-v0.9.5.1, the table-merge loop appended every module-declared
# table without checking overlap with the parent manifest. A plugin
# whose plugin.yaml declared table `foo` AND whose module.yaml
# re-declared `foo` ended up with `foo` twice in the merged response.
# Visible on the v0.9.5 Datasets page as duplicate rows for SDI
# (4 unique tables rendered as 7 with dupes).


def test_b169_merge_module_manifests_dedupes_tables(tmp_path, monkeypatch):
    """Module-declared tables that overlap with parent must NOT
    appear twice in the merged manifest."""
    import yaml as _yaml
    from apps.api.src.routes import plugins as plugins_module

    # Build a fixture plugin on disk: plugin.yaml declares two tables;
    # one module re-declares one of them plus adds a new one.
    plugin_dir = tmp_path / "fixture-plugin"
    plugin_dir.mkdir()
    modules_dir = plugin_dir / "modules" / "extras"
    modules_dir.mkdir(parents=True)

    (plugin_dir / "plugin.yaml").write_text(_yaml.safe_dump({
        "name": "fixture-plugin",
        "version": "1.0.0",
        "databases": {"postgres": {"tables": ["foo", "bar"]}},
    }))
    (modules_dir / "module.yaml").write_text(_yaml.safe_dump({
        "name": "extras",
        "display_name": "Extras Module",
        # Re-declares `foo` (overlap) and adds `baz` (new).
        "databases": {"postgres": {"tables": ["foo", "baz"]}},
    }))

    # Stub out the disk + DB lookups _merge_module_manifests calls.
    monkeypatch.setattr(plugins_module, "_find_plugin_dir", lambda pid, installed_only=True: plugin_dir)
    monkeypatch.setattr(plugins_module, "_get_enabled_module_names", lambda pid: ["extras"])

    # Start from a manifest matching what plugin.yaml declares.
    parent = {"databases": {"postgres": {"tables": ["foo", "bar"]}}}
    merged = plugins_module._merge_module_manifests("fixture-plugin", parent)

    tables = merged["databases"]["postgres"]["tables"]
    # `foo` should appear ONCE (parent's `foo` survives, module's
    # duplicate is skipped); `bar` and `baz` are unique additions.
    assert tables == ["foo", "bar", "baz"], (
        f"Expected ['foo', 'bar', 'baz'], got {tables}. B169 dedupe failed."
    )
    assert len(tables) == len(set(tables)), (
        f"Tables list contains duplicates: {tables}. B169."
    )


# ── Share password hashing ────────────────────────────────────────────


def test_share_password_hash_roundtrip():
    from apps.api.src.routes.share import _hash_password, _check_password
    pw = "test-password-123"
    hashed = _hash_password(pw)
    assert _check_password(pw, hashed) is True
    assert _check_password("wrong-password", hashed) is False


def test_share_password_hash_unique_per_call():
    from apps.api.src.routes.share import _hash_password
    h1 = _hash_password("same")
    h2 = _hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


# ── Encryption ────────────────────────────────────────────────────────


try:
    import cryptography  # noqa: F401
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


@pytest.mark.skipif(not _HAS_CRYPTO, reason="cryptography package not installed")
def test_encryption_roundtrip(monkeypatch):
    monkeypatch.setenv("NOUSVIZ_ENCRYPTION_KEY", "a" * 64)
    from core.connections.encryption import encrypt, decrypt
    plaintext = "my-secret-api-key"
    encrypted, nonce = encrypt(plaintext)
    assert decrypt(encrypted, nonce) == plaintext


@pytest.mark.skipif(not _HAS_CRYPTO, reason="cryptography package not installed")
def test_encryption_rejects_short_key(monkeypatch):
    monkeypatch.setenv("NOUSVIZ_ENCRYPTION_KEY", "short")
    from core.connections.encryption import encrypt, EncryptionError
    with pytest.raises(EncryptionError):
        encrypt("test")


def test_encryption_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("NOUSVIZ_ENCRYPTION_KEY", raising=False)
    from core.connections.encryption import EncryptionError
    # _get_master_key raises before it even tries to import cryptography
    from core.connections.encryption import _get_master_key
    with pytest.raises(EncryptionError):
        _get_master_key()


def test_generate_app_secret_length():
    from core.connections.encryption import generate_app_secret
    secret = generate_app_secret()
    assert len(secret) == 64  # hex-encoded 32 bytes


# ── Env file helpers ──────────────────────────────────────────────────


def test_sanitise_env_value_strips_newlines():
    from apps.api.src._env import _sanitise_env_value
    assert _sanitise_env_value("hello\nworld") == "helloworld"
    assert _sanitise_env_value("clean") == "clean"
    assert _sanitise_env_value("a\rb\nc") == "abc"


def test_write_env_file_creates_new(tmp_path, monkeypatch):
    import apps.api.src._env as env_mod
    env_file = tmp_path / ".env"
    monkeypatch.setattr(env_mod, "ENV_FILE", env_file)
    env_mod.write_env_file({"KEY1": "val1", "KEY2": "val2"})
    content = env_file.read_text()
    assert "KEY1=val1" in content
    assert "KEY2=val2" in content


def test_write_env_file_preserves_comments(tmp_path, monkeypatch):
    import apps.api.src._env as env_mod
    env_file = tmp_path / ".env"
    env_file.write_text("# Important comment\nEXISTING=old\n")
    monkeypatch.setattr(env_mod, "ENV_FILE", env_file)
    env_mod.write_env_file({"EXISTING": "new", "ADDED": "fresh"})
    content = env_file.read_text()
    assert "# Important comment" in content
    assert "EXISTING=new" in content
    assert "ADDED=fresh" in content
    assert "EXISTING=old" not in content


# ── Docs allowlist ────────────────────────────────────────────────────


def test_docs_index_all_have_required_fields():
    from apps.api.src.routes.docs import DOCS_INDEX
    for slug, title, path, section in DOCS_INDEX:
        assert slug, "empty slug"
        assert title, "empty title"
        assert path, "empty path"
        assert section in ("platform", "plugins", "development"), f"unknown section: {section}"


def test_docs_index_slugs_unique():
    from apps.api.src.routes.docs import DOCS_INDEX
    slugs = [s for s, _, _, _ in DOCS_INDEX]
    assert len(slugs) == len(set(slugs)), f"duplicate slugs: {[s for s in slugs if slugs.count(s) > 1]}"


# ── Rate limiter state machine ────────────────────────────────────────


def test_login_rate_limit_blocks_after_threshold():
    from apps.api.src.routes.auth import _check_login_rate, _login_limiter
    _login_limiter._store.clear()
    ip = "test-rate-limit-ip"
    for _ in range(5):
        assert _check_login_rate(ip) is False
    assert _check_login_rate(ip) is True
    _login_limiter._store.clear()


def test_install_rate_limit_blocks_after_threshold():
    from apps.api.src.routes.plugins import _check_install_rate, _install_timestamps, _INSTALL_RATE_LIMIT
    from fastapi import HTTPException
    _install_timestamps.clear()
    ip = "test-install-ip"
    for _ in range(_INSTALL_RATE_LIMIT):
        _check_install_rate(ip)  # should not raise
    with pytest.raises(HTTPException) as exc_info:
        _check_install_rate(ip)  # 6th attempt should raise 429
    assert exc_info.value.status_code == 429
    _install_timestamps.clear()


# ── formatStatus + formatRelativeTime + labelForLevel ─────────────────


def test_health_ssl_status_returns_dict_when_configured(monkeypatch):
    """Verify _get_ssl_status returns consistent shape for downstream consumers."""
    from apps.api.src.routes.health import _get_ssl_status, _cert_expiry_cache
    _cert_expiry_cache.clear()
    monkeypatch.setenv("NOUSVIZ_SSL", "letsencrypt")
    monkeypatch.setenv("NOUSVIZ_DOMAIN", "example.com")
    result = _get_ssl_status()
    assert result is not None
    assert result["enabled"] is True
    assert result["type"] == "letsencrypt"
    assert result["domain"] == "example.com"


def test_health_ssl_status_returns_none_when_empty(monkeypatch):
    from apps.api.src.routes.health import _get_ssl_status, _cert_expiry_cache
    _cert_expiry_cache.clear()
    monkeypatch.delenv("NOUSVIZ_SSL", raising=False)
    assert _get_ssl_status() is None


# ── P58: auth helpers ─────────────────────────────────────────────────


def test_bcrypt_hash_roundtrip():
    from apps.api.src.routes.auth import _hash_password, _check_password
    pw = "test-password-123!"
    hashed = _hash_password(pw)
    assert _check_password(pw, hashed) is True
    assert _check_password("wrong", hashed) is False


def test_bcrypt_hash_unique_salts():
    from apps.api.src.routes.auth import _hash_password
    h1 = _hash_password("same")
    h2 = _hash_password("same")
    assert h1 != h2  # different salts


def test_smtp_is_configured(monkeypatch):
    from apps.api.src.services.email import is_configured
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert is_configured() is False
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    assert is_configured() is True
    monkeypatch.setenv("SMTP_HOST", "   ")
    assert is_configured() is False


# ── B179: Bounded rate limiter ──────────────────────────────────────────

def test_rate_limiter_blocks_after_max_attempts():
    from apps.api.src.rate_limit import RateLimiter
    rl = RateLimiter(max_attempts=3, window_sec=60, max_keys=100)
    assert rl.is_limited("ip1") is False
    assert rl.is_limited("ip1") is False
    assert rl.is_limited("ip1") is False
    assert rl.is_limited("ip1") is True


def test_rate_limiter_lru_eviction_preserves_active():
    from apps.api.src.rate_limit import RateLimiter
    rl = RateLimiter(max_attempts=3, window_sec=60, max_keys=5)
    # Fill 3 attempts for ip_target
    for _ in range(3):
        rl.is_limited("ip_target")
    assert rl.is_limited("ip_target") is True
    # Flood with 10 new IPs to trigger eviction
    for i in range(10):
        rl.is_limited(f"flood_{i}")
    # ip_target was evicted (LRU), so it resets
    # but the flood IPs didn't reset each other
    assert len(rl._store) <= 5


def test_rate_limiter_no_full_flush():
    from apps.api.src.rate_limit import RateLimiter
    rl = RateLimiter(max_attempts=2, window_sec=60, max_keys=10)
    # Rate-limit ip_a and ip_b
    rl.is_limited("ip_a")
    rl.is_limited("ip_a")
    rl.is_limited("ip_b")
    rl.is_limited("ip_b")
    assert rl.is_limited("ip_a") is True
    assert rl.is_limited("ip_b") is True
    # Flood with 5 new IPs (under max_keys) — should NOT flush ip_a or ip_b
    for i in range(5):
        rl.is_limited(f"new_{i}")
    assert rl.is_limited("ip_a") is True
    assert rl.is_limited("ip_b") is True


# ── RBAC role hierarchy (catalog defaults) ──────────────────────────────
# B235 (v0.9.9.3): the inline _require_analyst / _require_admin shims were
# replaced by Depends(requires("permission")). The invariant these tests
# guard — that analyst-tier perms accept analyst+ and admin-tier perms
# accept admin+ — is now expressed against the catalog defaults via
# default_permissions_for_role (no DB, matches the offline CI job).

def test_analyst_tier_permission_role_hierarchy():
    """Permissions held by analysts must also be held by admins and superadmins."""
    from apps.api.src.rbac.permissions import default_permissions_for_role
    perm = "jobs.read"  # analyst-tier permission (not in viewer set)
    for role in ("analyst", "admin", "superadmin"):
        assert perm in default_permissions_for_role(role), f"{role!r} should hold {perm!r}"
    for role in ("viewer", "", "nonexistent"):
        assert perm not in default_permissions_for_role(role), f"{role!r} should NOT hold {perm!r}"


def test_admin_tier_permission_role_hierarchy():
    """Permissions held by admins must also be held by superadmins, not by analyst/viewer."""
    from apps.api.src.rbac.permissions import default_permissions_for_role
    perm = "users.manage"  # admin-tier permission
    for role in ("admin", "superadmin"):
        assert perm in default_permissions_for_role(role), f"{role!r} should hold {perm!r}"
    for role in ("viewer", "analyst", "", "nonexistent"):
        assert perm not in default_permissions_for_role(role), f"{role!r} should NOT hold {perm!r}"


# ── P65: Plugin contract validation ─────────────────────────────────────

def test_all_official_plugins_have_valid_manifests():
    """Every plugin in plugins/official/ must have a valid plugin.yaml."""
    from pathlib import Path
    import yaml
    official = Path("plugins/official")
    if not official.exists():
        pytest.skip("No plugins/official/ directory")
    required_fields = {"name", "display_name", "version", "description", "license", "icon"}
    for d in official.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        manifest = d / "plugin.yaml"
        assert manifest.exists(), f"{d.name}: missing plugin.yaml"
        data = yaml.safe_load(manifest.read_text())
        assert data, f"{d.name}: empty plugin.yaml"
        for field in required_fields:
            assert field in data, f"{d.name}: missing required field '{field}'"


def test_all_plugins_use_path_not_href():
    """Navigation entries should use 'path', not 'href'."""
    from pathlib import Path
    import yaml
    for base in [Path("plugins/official"), Path("plugins/utilities")]:
        if not base.exists():
            continue
        for d in base.iterdir():
            manifest = d / "plugin.yaml"
            if not manifest.exists():
                continue
            data = yaml.safe_load(manifest.read_text())
            for nav in (data.get("navigation") or []):
                assert "path" in nav or "href" not in nav, f"{d.name}: navigation uses 'href' instead of 'path'"


def test_no_1engine_references():
    """No plugin manifest should reference the old 1Engine brand."""
    from pathlib import Path
    for base in [Path("plugins/official"), Path("plugins/utilities")]:
        if not base.exists():
            continue
        for d in base.iterdir():
            manifest = d / "plugin.yaml"
            if not manifest.exists():
                continue
            content = manifest.read_text().lower()
            assert "1engine" not in content, f"{d.name}: still references 1Engine"


def test_utility_plugins_have_provides():
    """Utility plugins must declare what capability they provide."""
    from pathlib import Path
    import yaml
    utilities = Path("plugins/utilities")
    if not utilities.exists():
        pytest.skip("No plugins/utilities/ directory")
    for d in utilities.iterdir():
        if not d.is_dir():
            continue
        manifest = d / "plugin.yaml"
        if not manifest.exists():
            continue
        data = yaml.safe_load(manifest.read_text())
        if data.get("type") == "utility":
            assert data.get("provides"), f"{d.name}: utility plugin missing 'provides' field"
