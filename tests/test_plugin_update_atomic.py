"""Tests for the atomic update flow (B145 / v0.9.2.5).

Pure-logic and filesystem tests for _validate_staged_plugin and the
first-party path of _stage_plugin_clone. Git-clone path is exercised live
during deploy, not unit-tested here.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── _validate_staged_plugin ──────────────────────────────────────────


def test_validate_staged_plugin_accepts_matching_name(tmp_path):
    from apps.api.src.routes.plugins import _validate_staged_plugin

    (tmp_path / "plugin.yaml").write_text("name: foo\nversion: 1.0.0\n")
    meta = _validate_staged_plugin("foo", tmp_path)
    assert meta["name"] == "foo"
    assert meta["version"] == "1.0.0"


def test_validate_staged_plugin_rejects_mismatched_name(tmp_path):
    from apps.api.src.routes.plugins import _validate_staged_plugin
    from fastapi import HTTPException

    (tmp_path / "plugin.yaml").write_text("name: bar\nversion: 1.0.0\n")
    with pytest.raises(HTTPException) as exc:
        _validate_staged_plugin("foo", tmp_path)
    assert exc.value.status_code == 500
    assert "name='bar'" in exc.value.detail


def test_validate_staged_plugin_rejects_missing_manifest(tmp_path):
    from apps.api.src.routes.plugins import _validate_staged_plugin
    from fastapi import HTTPException

    # No plugin.yaml in tmp_path
    with pytest.raises(HTTPException) as exc:
        _validate_staged_plugin("foo", tmp_path)
    assert exc.value.status_code == 500
    assert "missing plugin.yaml" in exc.value.detail


def test_validate_staged_plugin_rejects_invalid_yaml(tmp_path):
    from apps.api.src.routes.plugins import _validate_staged_plugin
    from fastapi import HTTPException

    (tmp_path / "plugin.yaml").write_text("name: foo\n  bad indent: ::\n")
    with pytest.raises(HTTPException) as exc:
        _validate_staged_plugin("foo", tmp_path)
    assert exc.value.status_code == 500
    assert "invalid" in exc.value.detail.lower()


def test_validate_staged_plugin_allows_unnamed_manifest(tmp_path):
    """A manifest without explicit `name:` is accepted (we only fail on
    explicit mismatch). Some plugins omit name and rely on the dir name."""
    from apps.api.src.routes.plugins import _validate_staged_plugin

    (tmp_path / "plugin.yaml").write_text("version: 1.0.0\ndescription: test\n")
    meta = _validate_staged_plugin("foo", tmp_path)
    assert meta["version"] == "1.0.0"


# ── _stage_plugin_clone (first-party path) ────────────────────────────


def test_stage_first_party_from_utilities(tmp_path):
    """Plugin in plugins/utilities/<slug>/ → copied verbatim to staging dir."""
    from apps.api.src.routes import plugins as plugins_module

    # Set up a fake catalog
    utilities = tmp_path / "plugins" / "utilities"
    utilities.mkdir(parents=True)
    (utilities / "test-plug").mkdir()
    (utilities / "test-plug" / "plugin.yaml").write_text("name: test-plug\nversion: 2.0.0\n")
    (utilities / "test-plug" / "extra.txt").write_text("payload")

    staging_dir = tmp_path / "plugins" / "installed" / "test-plug.staging.123"

    with patch.object(plugins_module, "UTILITIES_DIR", utilities), \
         patch.object(plugins_module, "OFFICIAL_DIR", tmp_path / "plugins" / "official"):
        version = plugins_module._stage_plugin_clone(
            "test-plug", "first_party", None, staging_dir
        )

    assert version == "2.0.0"
    assert staging_dir.exists()
    assert (staging_dir / "plugin.yaml").exists()
    assert (staging_dir / "extra.txt").read_text() == "payload"


def test_stage_first_party_falls_back_to_official(tmp_path):
    """If utilities/ is empty, official/ is searched next."""
    from apps.api.src.routes import plugins as plugins_module

    utilities = tmp_path / "plugins" / "utilities"
    utilities.mkdir(parents=True)
    official = tmp_path / "plugins" / "official"
    official.mkdir(parents=True)
    (official / "test-plug").mkdir()
    (official / "test-plug" / "plugin.yaml").write_text("name: test-plug\nversion: 1.5.0\n")

    staging_dir = tmp_path / "plugins" / "installed" / "test-plug.staging.123"

    with patch.object(plugins_module, "UTILITIES_DIR", utilities), \
         patch.object(plugins_module, "OFFICIAL_DIR", official):
        version = plugins_module._stage_plugin_clone(
            "test-plug", "first_party", None, staging_dir
        )

    assert version == "1.5.0"
    assert staging_dir.exists()


def test_stage_first_party_raises_when_no_catalog_source(tmp_path):
    from apps.api.src.routes import plugins as plugins_module
    from fastapi import HTTPException

    utilities = tmp_path / "plugins" / "utilities"
    utilities.mkdir(parents=True)
    official = tmp_path / "plugins" / "official"
    official.mkdir(parents=True)

    staging_dir = tmp_path / "plugins" / "installed" / "ghost.staging.123"

    with patch.object(plugins_module, "UTILITIES_DIR", utilities), \
         patch.object(plugins_module, "OFFICIAL_DIR", official):
        with pytest.raises(HTTPException) as exc:
            plugins_module._stage_plugin_clone(
                "ghost", "first_party", None, staging_dir
            )

    assert exc.value.status_code == 404
    assert "no bundled catalog source" in exc.value.detail


# ── _stage_plugin_clone (rejected source classes) ────────────────────


def test_stage_rejects_unknown_source_class(tmp_path):
    from apps.api.src.routes import plugins as plugins_module
    from fastapi import HTTPException

    staging_dir = tmp_path / "staging"
    with pytest.raises(HTTPException) as exc:
        plugins_module._stage_plugin_clone(
            "test", "unknown", None, staging_dir
        )
    assert exc.value.status_code == 400


def test_stage_git_rejects_missing_url(tmp_path):
    from apps.api.src.routes import plugins as plugins_module
    from fastapi import HTTPException

    staging_dir = tmp_path / "staging"
    with pytest.raises(HTTPException) as exc:
        plugins_module._stage_plugin_clone(
            "test", "git", None, staging_dir
        )
    assert exc.value.status_code == 400


# ── Atomic swap semantics: filesystem rename behaviour ───────────────


def test_atomic_swap_preserves_data_on_rename_failure(tmp_path):
    """Direct filesystem test: when staging→live rename fails, the backup
    can be restored. This isn't a test of update_plugin itself — it's a
    test of the assumption that pathlib renames preserve the source dir
    if the target doesn't exist (so we can rename .backup back)."""

    live = tmp_path / "live"
    live.mkdir()
    (live / "marker").write_text("v1")

    # Simulate the rename live → backup
    backup = tmp_path / "backup"
    live.rename(backup)
    assert not live.exists()
    assert backup.exists()
    assert (backup / "marker").read_text() == "v1"

    # Simulate restore: backup → live
    backup.rename(live)
    assert live.exists()
    assert not backup.exists()
    assert (live / "marker").read_text() == "v1"


# ── B161 (v0.9.4.10): update_plugin triggers pm2 reload ──────────────
# Pre-v0.9.4.10, update_plugin atomically swapped the plugin directory
# but never triggered any reload. The plugin's new routes.py was on disk
# but Python's module cache still held the old import, so FastAPI kept
# dispatching to the old route handlers until the next hourly cron_restart
# (up to 60 min). Same Popen pattern uninstall already uses (plugins.py:1822).
#
# Full integration of update_plugin requires async + Request + an installed
# plugin on disk + git operations. Instead, these contract tests assert
# the source code of update_plugin contains the reload trigger and the
# response note matches reality.


def _read_update_plugin_source() -> str:
    import inspect
    from apps.api.src.routes.plugins import update_plugin
    return inspect.getsource(update_plugin)


def test_b161_update_plugin_triggers_pm2_reload():
    """update_plugin must call subprocess.Popen(["pm2", "reload", "api", ...])
    after the swap completes. Without this, the file swap is on disk but
    plugin module imports stay cached until the next cron_restart."""
    src = _read_update_plugin_source()
    assert "pm2" in src and "reload" in src and "api" in src, (
        "update_plugin must trigger pm2 reload after a successful update (B161)"
    )
    # Specifically the 4-arg form used by the uninstall path
    assert '"pm2", "reload", "api", "--update-env"' in src, (
        "update_plugin must use the same pm2 reload args as the uninstall path"
    )
    # Popen — fire-and-forget so the response returns before the worker reload
    assert "Popen" in src, (
        "update_plugin must use subprocess.Popen (not run/check_output) so the "
        "reload is non-blocking and the operator gets a clean 200"
    )


def test_b161_update_plugin_reload_failure_is_non_fatal():
    """If pm2 isn't on PATH (e.g. local dev without pm2), the update must
    still succeed — the file swap is the real success criterion."""
    src = _read_update_plugin_source()
    # The Popen call must be wrapped in try/except so a missing pm2 binary
    # doesn't 500 the update.
    assert "except Exception" in src, (
        "pm2 reload trigger must be wrapped in try/except (B161 — non-fatal)"
    )
    # And on failure, log a warning rather than swallowing silently
    assert "could not trigger PM2 reload" in src or "could not trigger pm2 reload" in src.lower(), (
        "pm2 reload failure must be logged at warning level, not silently swallowed"
    )


def test_b161_update_plugin_response_note_matches_reality():
    """The response 'note' field used to claim 'API will reload to pick up
    new routes' but nothing actually reloaded. Now that we trigger the
    reload, the note must reflect what actually happens."""
    src = _read_update_plugin_source()
    # Old aspirational copy must be gone
    assert "API will reload to pick up new routes" not in src, (
        "response note must reflect actual behavior, not the pre-B161 aspirational copy"
    )
    # New copy must mention the active reload
    assert "reloading" in src, (
        "response note must tell the operator a reload is in progress"
    )


# ── B163 (v0.9.4.11): uninstall_plugin purges DB rows ────────────────
# Pre-v0.9.4.11, uninstall removed the on-disk plugin directory + ran
# down-migrations + revoked grants — but left orphaned rows in five
# tables (connections-via-cascade, plugin_settings, plugin_registry,
# plugin_update_status, sync_schedule_registry). Reinstalling silently
# inherited prior trust consent, credentials, and settings. v0.9.4.11
# adds _purge_plugin_db_rows() and calls it from uninstall_plugin.


def _read_uninstall_plugin_source() -> str:
    import inspect
    from apps.api.src.routes.plugins import uninstall_plugin
    return inspect.getsource(uninstall_plugin)


def _read_purge_helper_source() -> str:
    import inspect
    from apps.api.src.routes.plugins import _purge_plugin_db_rows
    return inspect.getsource(_purge_plugin_db_rows)


def test_b163_uninstall_purges_db_rows():
    """uninstall_plugin must call _purge_plugin_db_rows for both the
    target plugin and any cascaded dependents."""
    src = _read_uninstall_plugin_source()
    assert "_purge_plugin_db_rows(" in src, (
        "uninstall_plugin must call _purge_plugin_db_rows (B163)"
    )
    # Should be invoked at least twice — once in the cascade loop, once
    # for the target plugin. Source-level count is a proxy.
    occurrences = src.count("_purge_plugin_db_rows(")
    assert occurrences >= 2, (
        f"_purge_plugin_db_rows must be called for both target and cascade "
        f"(found {occurrences} occurrences in uninstall_plugin source)"
    )


def test_b163_purge_helper_targets_all_five_tables():
    """The helper must DELETE from all five orphaned tables, plus use
    the 'plugin:<slug>' name pattern for the connections delete (so we
    don't accidentally delete unrelated connection rows)."""
    src = _read_purge_helper_source()
    for table in [
        "connections",
        "plugin_settings",
        "plugin_registry",
        "plugin_update_status",
        "sync_schedule_registry",
    ]:
        assert f"DELETE FROM {table}" in src, (
            f"_purge_plugin_db_rows must DELETE from {table} (B163)"
        )
    # The connections delete must be scoped to the plugin's synthetic
    # connection row — never delete arbitrary connections.
    assert 'name = %s' in src and 'plugin:' in src, (
        "connections DELETE must scope by name = 'plugin:<slug>' (B163 — "
        "deleting all connections would wipe the host's data sources)"
    )


def test_b163_purge_uses_correct_columns():
    """plugin_registry uses `slug`, not `plugin_id` — schema mismatch
    would silently no-op the delete and leave registry rows orphaned."""
    src = _read_purge_helper_source()
    # plugin_registry filter must use `slug = `
    assert "plugin_registry WHERE slug = %s" in src, (
        "plugin_registry's primary key column is `slug`, not `plugin_id` (B163)"
    )
    # Other tables use plugin_id
    for table in ["plugin_settings", "plugin_update_status", "sync_schedule_registry"]:
        assert f"{table} WHERE plugin_id = %s" in src, (
            f"{table} should be filtered by plugin_id column (B163)"
        )
