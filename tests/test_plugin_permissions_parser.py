"""B247 (v0.9.10.6): unit tests for apps/api/src/plugin_manifest.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.plugin_manifest import (  # noqa: E402
    LEVELS,
    ManifestPermissionsError,
    PermissionRule,
    PermissionsConfig,
    all_permission_strings,
    parse,
    permission_string,
)


# ── parse() ────────────────────────────────────────────────────────────


def test_parse_returns_none_for_missing_block():
    assert parse(None) is None
    assert parse({}) is None


def test_parse_default_only():
    cfg = parse({"default": "read"})
    assert cfg is not None
    assert cfg.default_level == "read"
    assert cfg.route_rules == ()


def test_parse_implicit_default_is_read():
    """Operators can omit `default:` — read is the safe fallback."""
    cfg = parse({"routes": []})
    assert cfg is not None
    assert cfg.default_level == "read"


def test_parse_default_and_routes():
    cfg = parse({
        "default": "read",
        "routes": [
            {"path": "/api/plugins/foo/admin/*", "level": "admin"},
            {"method": "POST", "level": "write"},
        ],
    })
    assert cfg is not None
    assert cfg.default_level == "read"
    assert len(cfg.route_rules) == 2
    r0, r1 = cfg.route_rules
    assert r0.path_glob == "/api/plugins/foo/admin/*"
    assert r0.method is None
    assert r0.level == "admin"
    assert r1.method == "POST"
    assert r1.path_glob is None
    assert r1.level == "write"


def test_parse_uppercases_method():
    cfg = parse({"routes": [{"method": "post", "level": "write"}]})
    assert cfg.route_rules[0].method == "POST"


# ── parse() error cases ────────────────────────────────────────────────


def test_parse_rejects_non_mapping_block():
    with pytest.raises(ManifestPermissionsError, match="must be a mapping"):
        parse("read")


def test_parse_rejects_non_string_default():
    with pytest.raises(ManifestPermissionsError, match="default.*must be a string"):
        parse({"default": 7})


def test_parse_rejects_invalid_default_level():
    with pytest.raises(ManifestPermissionsError, match="must be one of"):
        parse({"default": "rwx"})


def test_parse_rejects_non_list_routes():
    with pytest.raises(ManifestPermissionsError, match="routes.*must be a list"):
        parse({"routes": {"a": 1}})


def test_parse_rejects_route_entry_without_level():
    with pytest.raises(ManifestPermissionsError, match=r"routes\[0\]\.level"):
        parse({"routes": [{"path": "/api/foo"}]})


def test_parse_rejects_invalid_level():
    with pytest.raises(ManifestPermissionsError, match=r"routes\[0\]\.level"):
        parse({"routes": [{"path": "/api/foo", "level": "rwx"}]})


def test_parse_rejects_non_string_path():
    with pytest.raises(ManifestPermissionsError, match=r"routes\[0\]\.path"):
        parse({"routes": [{"path": 7, "level": "read"}]})


def test_parse_rejects_invalid_method():
    with pytest.raises(ManifestPermissionsError, match=r"routes\[0\]\.method"):
        parse({"routes": [{"method": "TEAPOT", "level": "read"}]})


def test_parse_rejects_route_with_neither_path_nor_method():
    with pytest.raises(ManifestPermissionsError, match="must specify at least one"):
        parse({"routes": [{"level": "read"}]})


# ── PermissionsConfig.resolve() ────────────────────────────────────────


def test_resolve_falls_back_to_default():
    cfg = parse({"default": "read"})
    assert cfg.resolve("GET", "/api/plugins/foo/x") == "read"


def test_resolve_first_match_wins():
    cfg = parse({
        "default": "read",
        "routes": [
            {"path": "/api/plugins/foo/admin/*", "level": "admin"},
            {"path": "/api/plugins/foo/admin/users", "level": "configure"},
        ],
    })
    # The first rule fires for nested admin URLs.
    assert cfg.resolve("GET", "/api/plugins/foo/admin/users") == "admin"


def test_resolve_method_override():
    cfg = parse({
        "default": "read",
        "routes": [{"method": "DELETE", "level": "admin"}],
    })
    assert cfg.resolve("GET", "/api/plugins/foo/x") == "read"
    assert cfg.resolve("DELETE", "/api/plugins/foo/x") == "admin"


def test_resolve_method_and_path_combined():
    cfg = parse({
        "default": "read",
        "routes": [
            {"method": "POST", "path": "/api/plugins/foo/sync/*", "level": "configure"},
        ],
    })
    assert cfg.resolve("POST", "/api/plugins/foo/sync/run") == "configure"
    # Method matches but path doesn't — falls through.
    assert cfg.resolve("POST", "/api/plugins/foo/data") == "read"
    # Path matches but method doesn't — falls through.
    assert cfg.resolve("GET", "/api/plugins/foo/sync/run") == "read"


# ── permission_string() ───────────────────────────────────────────────


def test_permission_string_format():
    assert permission_string("foo", "read") == "plugin.foo.read"
    assert permission_string("cloudflare-analytics", "admin") == "plugin.cloudflare-analytics.admin"


def test_permission_string_rejects_bad_slug():
    with pytest.raises(ManifestPermissionsError, match="plugin slug"):
        permission_string("Foo", "read")
    with pytest.raises(ManifestPermissionsError, match="plugin slug"):
        permission_string("foo bar", "read")
    with pytest.raises(ManifestPermissionsError, match="plugin slug"):
        permission_string("123-foo", "read")


def test_permission_string_rejects_bad_level():
    with pytest.raises(ManifestPermissionsError, match="level"):
        permission_string("foo", "rwx")


def test_all_permission_strings_returns_one_per_level():
    out = all_permission_strings("foo")
    assert out == [
        "plugin.foo.read",
        "plugin.foo.write",
        "plugin.foo.configure",
        "plugin.foo.admin",
    ]


def test_levels_constant_in_privilege_order():
    """LEVELS is documented as increasing-privilege order — guard against
    accidental reorder."""
    assert LEVELS == ("read", "write", "configure", "admin")
