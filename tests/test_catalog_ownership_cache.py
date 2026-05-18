"""
Unit tests for the plugin-ownership-map cache (Keystone A — Phase 12 perf).

Before the cache, `_build_plugin_ownership_map()` was called ~34 times per
`/api/plugins` request at N=17 plugins on prod, each walking every
plugin.yaml from disk. That made the endpoint take 6.5–7s. With the
cache, repeated calls reuse the result until a manifest file's mtime
changes — which happens on plugin install, update, or uninstall.

These tests verify:
  - First call populates the cache and increments the `builds` counter.
  - Subsequent calls with unchanged mtimes hit the cache (no rebuild).
  - Touching a plugin.yaml triggers a rebuild on the next call.
  - Adding a new plugin dir triggers a rebuild on the next call.
  - Removing a plugin dir triggers a rebuild on the next call.
  - `invalidate_plugin_ownership_cache()` forces a rebuild on the next call.

The tests build a real temporary plugin layout on disk rather than mocking
the file IO — that way the mtime detection is exercised end-to-end.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src import catalog


# ── Fixture: temporary plugin layout ─────────────────────────────────


def _write_manifest(plugin_dir: Path, slug: str, tables: list[str]) -> None:
    """Drop a minimal plugin.yaml into ``plugin_dir`` claiming ``tables``."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    tables_block = "\n".join(f"      - {t}" for t in tables)
    (plugin_dir / "plugin.yaml").write_text(
        f"name: {slug}\n"
        f"version: 0.0.1\n"
        f"databases:\n"
        f"  postgres:\n"
        f"    tables:\n"
        f"{tables_block}\n"
    )


@pytest.fixture
def plugin_layout(tmp_path, monkeypatch):
    """Build a fake installed-plugins tree under ``tmp_path`` and point
    `ACTIVE_PLUGIN_DIRS` at it. Yields the installed base dir so tests
    can mutate it (add/remove/touch plugins).

    Also: invalidates the catalog cache before AND after each test so
    no test bleeds module state into the next.
    """
    installed = tmp_path / "installed"
    community = tmp_path / "community"
    installed.mkdir()
    community.mkdir()

    _write_manifest(installed / "alpha", "alpha", ["alpha_events", "alpha_users"])
    _write_manifest(installed / "beta", "beta", ["beta_things"])

    from apps.api.src.routes import plugins as plugins_module

    monkeypatch.setattr(
        plugins_module, "ACTIVE_PLUGIN_DIRS", [installed, community]
    )

    catalog.invalidate_plugin_ownership_cache()
    try:
        yield installed
    finally:
        catalog.invalidate_plugin_ownership_cache()


# ── Tests ────────────────────────────────────────────────────────────


def test_first_call_populates_cache(plugin_layout):
    """First call → builds counter goes up by 1, hits counter unchanged."""
    before = catalog.get_ownership_cache_stats()

    result = catalog._build_plugin_ownership_map()

    after = catalog.get_ownership_cache_stats()
    assert result == {
        "alpha_events": "alpha",
        "alpha_users": "alpha",
        "beta_things": "beta",
    }
    assert after["builds"] == before["builds"] + 1
    assert after["hits"] == before["hits"]


def test_second_call_hits_cache(plugin_layout):
    """Second call with no file changes → hits counter goes up, builds doesn't."""
    catalog._build_plugin_ownership_map()  # warm the cache
    mid = catalog.get_ownership_cache_stats()

    result = catalog._build_plugin_ownership_map()

    after = catalog.get_ownership_cache_stats()
    assert result == {
        "alpha_events": "alpha",
        "alpha_users": "alpha",
        "beta_things": "beta",
    }
    assert after["builds"] == mid["builds"]  # no rebuild
    assert after["hits"] == mid["hits"] + 1


def test_many_calls_hit_cache(plugin_layout):
    """The headline case: many consumers in one request → one build, N-1 hits."""
    catalog.invalidate_plugin_ownership_cache()
    before = catalog.get_ownership_cache_stats()

    # Simulate the `/api/plugins` request path which calls ~34 times.
    for _ in range(34):
        catalog._build_plugin_ownership_map()

    after = catalog.get_ownership_cache_stats()
    assert after["builds"] == before["builds"] + 1
    assert after["hits"] == before["hits"] + 33


def test_touching_manifest_invalidates_cache(plugin_layout):
    """Modifying plugin.yaml → next call rebuilds."""
    catalog._build_plugin_ownership_map()  # warm
    before = catalog.get_ownership_cache_stats()

    # Bump alpha's manifest mtime. Sleep so the OS reports a new mtime
    # even on filesystems with coarse mtime granularity.
    manifest = plugin_layout / "alpha" / "plugin.yaml"
    time.sleep(0.01)
    os.utime(manifest, None)

    catalog._build_plugin_ownership_map()

    after = catalog.get_ownership_cache_stats()
    assert after["builds"] == before["builds"] + 1


def test_adding_plugin_invalidates_cache(plugin_layout):
    """A new plugin dir → next call rebuilds and surfaces the new tables."""
    catalog._build_plugin_ownership_map()  # warm
    before = catalog.get_ownership_cache_stats()

    # Sleep so the parent dir's mtime change is detectable.
    time.sleep(0.01)
    _write_manifest(plugin_layout / "gamma", "gamma", ["gamma_new"])

    result = catalog._build_plugin_ownership_map()
    after = catalog.get_ownership_cache_stats()

    assert "gamma_new" in result
    assert result["gamma_new"] == "gamma"
    assert after["builds"] == before["builds"] + 1


def test_removing_plugin_invalidates_cache(plugin_layout):
    """A removed plugin dir → next call rebuilds and drops the gone plugin's tables."""
    catalog._build_plugin_ownership_map()  # warm
    before = catalog.get_ownership_cache_stats()

    # Remove beta entirely.
    time.sleep(0.01)
    (plugin_layout / "beta" / "plugin.yaml").unlink()
    (plugin_layout / "beta").rmdir()

    result = catalog._build_plugin_ownership_map()
    after = catalog.get_ownership_cache_stats()

    assert "beta_things" not in result
    assert "alpha_events" in result  # alpha still there
    assert after["builds"] == before["builds"] + 1


def test_invalidate_forces_rebuild(plugin_layout):
    """Explicit invalidate_plugin_ownership_cache() forces the next call to rebuild."""
    catalog._build_plugin_ownership_map()  # warm
    before = catalog.get_ownership_cache_stats()

    catalog.invalidate_plugin_ownership_cache()
    catalog._build_plugin_ownership_map()

    after = catalog.get_ownership_cache_stats()
    assert after["builds"] == before["builds"] + 1


def test_transient_listing_failure_does_not_poison_cache(plugin_layout):
    """If `_installed_slugs()` raises, we return empty and DON'T cache it —
    next call retries against the (recovered) file system.
    """
    from apps.api.src.routes import plugins as plugins_module

    catalog._build_plugin_ownership_map()  # warm with real data
    before = catalog.get_ownership_cache_stats()

    # Force a transient failure on the next call. Bust the mtime cache
    # so the function takes the rebuild path rather than the hit path.
    catalog.invalidate_plugin_ownership_cache()

    real_installed_slugs = plugins_module._installed_slugs

    def raise_oserr():
        raise OSError("transient")

    plugins_module._installed_slugs = raise_oserr
    try:
        result = catalog._build_plugin_ownership_map()
        after = catalog.get_ownership_cache_stats()

        assert result == {}
        # `builds` is incremented only on successful caching; transient
        # failures should NOT have incremented it.
        assert after["builds"] == before["builds"]
    finally:
        plugins_module._installed_slugs = real_installed_slugs

    # Recover and verify the next call works (the empty result was not cached).
    result2 = catalog._build_plugin_ownership_map()
    assert "alpha_events" in result2
