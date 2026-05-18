"""
Unit tests for the v0.10.0.6.2 /api/launchpad changes:
  - 30-second module-level response cache
  - pg_class.reltuples row estimates instead of per-table count(*)
  - Plugin manifest reads via the catalog cache (Keystone A)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.routes import launchpad


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the launchpad response cache before every test."""
    launchpad.invalidate_launchpad_cache()
    yield
    launchpad.invalidate_launchpad_cache()


def test_response_cache_returns_cached_data_within_ttl():
    """A second call within the TTL window returns the cached object,
    not a freshly-computed one."""
    sentinel = {"recent_activity": ["from-cache"]}
    launchpad._set_cached_response(sentinel)

    cached = launchpad._get_cached_response()
    assert cached is sentinel


def test_response_cache_returns_none_when_empty():
    """Initial state — no cache populated — returns None."""
    assert launchpad._get_cached_response() is None


def test_invalidate_cache_clears_stored_response():
    """Explicit invalidation drops the cached data."""
    launchpad._set_cached_response({"foo": "bar"})
    assert launchpad._get_cached_response() is not None

    launchpad.invalidate_launchpad_cache()
    assert launchpad._get_cached_response() is None


def test_response_cache_expires_after_ttl(monkeypatch):
    """When monotonic time passes the TTL boundary, the cache returns None."""
    import time as time_mod

    real_monotonic = time_mod.monotonic
    fake_now = [real_monotonic()]

    def fake_monotonic():
        return fake_now[0]

    monkeypatch.setattr(launchpad.time, "monotonic", fake_monotonic)

    launchpad._set_cached_response({"foo": "bar"})
    # Still fresh
    assert launchpad._get_cached_response() is not None

    # Advance past the TTL window
    fake_now[0] += launchpad._LAUNCHPAD_CACHE_TTL_SEC + 1.0

    assert launchpad._get_cached_response() is None


def test_build_plugin_tables_map_uses_catalog_cache(monkeypatch):
    """_build_plugin_tables_map() flips ownership map from
    {table: plugin_id} to {plugin_id: [tables]}."""
    from apps.api.src import catalog

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map",
                        lambda: {
                            "users_table": "auth-plugin",
                            "events_table": "auth-plugin",
                            "orders": "shop-plugin",
                        })

    result = launchpad._build_plugin_tables_map()

    assert sorted(result["auth-plugin"]) == ["events_table", "users_table"]
    assert result["shop-plugin"] == ["orders"]


def test_build_plugin_display_names_falls_back_to_plugin_id(monkeypatch):
    """A plugin whose manifest can't be read still gets an entry in the
    display-names dict — falling back to the plugin_id itself."""

    def fake_load_plugin(pid, installed_only=False):
        if pid == "good":
            return {"display_name": "Good Plugin"}
        return None  # simulate missing manifest

    monkeypatch.setattr(launchpad, "_load_plugin", fake_load_plugin)

    names = launchpad._build_plugin_display_names(["good", "missing"])
    assert names["good"] == "Good Plugin"
    assert names["missing"] == "missing"


def test_build_plugin_display_names_empty_input():
    """Empty plugin id list → empty dict, no exceptions."""
    assert launchpad._build_plugin_display_names([]) == {}
