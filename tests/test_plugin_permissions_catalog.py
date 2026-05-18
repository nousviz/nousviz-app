"""B247 (v0.9.10.6): tests for the dynamic plugin permissions catalog.

These tests mutate the live PERMISSIONS / ROLE_PERMISSIONS dicts. To
keep them isolated:
- Each test registers a plugin with a fresh slug (uuid-derived).
- Tests don't unregister — the registered set is monotonic by design
  (operators expect plugin permissions to persist between calls).
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.rbac.permissions import PERMISSIONS, ROLE_PERMISSIONS  # noqa: E402
from apps.api.src.rbac.plugin_permissions import (  # noqa: E402
    register_all_plugin_levels,
    register_plugin_permissions,
    registered_plugin_permissions,
)


def _fresh_slug() -> str:
    """Return a deterministic but unique slug for the test."""
    return f"test-{uuid.uuid4().hex[:8]}"


def test_register_all_levels_adds_to_permissions_dict():
    slug = _fresh_slug()
    out = register_all_plugin_levels(slug)

    assert out == [
        f"plugin.{slug}.read",
        f"plugin.{slug}.write",
        f"plugin.{slug}.configure",
        f"plugin.{slug}.admin",
    ]
    for perm in out:
        assert perm in PERMISSIONS
        assert PERMISSIONS[perm].startswith("Per-plugin")


def test_register_grants_default_role_permissions():
    slug = _fresh_slug()
    register_all_plugin_levels(slug)

    read_perm = f"plugin.{slug}.read"
    write_perm = f"plugin.{slug}.write"
    configure_perm = f"plugin.{slug}.configure"
    admin_perm = f"plugin.{slug}.admin"

    # read → viewer+ (everyone)
    for role in ("viewer", "analyst", "admin", "superadmin"):
        assert read_perm in ROLE_PERMISSIONS[role], (
            f"{role} should hold {read_perm}"
        )

    # write → analyst+
    assert write_perm not in ROLE_PERMISSIONS["viewer"]
    for role in ("analyst", "admin", "superadmin"):
        assert write_perm in ROLE_PERMISSIONS[role]

    # configure → admin+
    for role in ("viewer", "analyst"):
        assert configure_perm not in ROLE_PERMISSIONS[role]
    for role in ("admin", "superadmin"):
        assert configure_perm in ROLE_PERMISSIONS[role]

    # admin → superadmin only
    for role in ("viewer", "analyst", "admin"):
        assert admin_perm not in ROLE_PERMISSIONS[role]
    assert admin_perm in ROLE_PERMISSIONS["superadmin"]


def test_register_idempotent():
    slug = _fresh_slug()
    out1 = register_all_plugin_levels(slug)
    # Snapshot ROLE_PERMISSIONS sizes BEFORE the second call.
    sizes_before = {role: len(ROLE_PERMISSIONS[role]) for role in ROLE_PERMISSIONS}
    out2 = register_all_plugin_levels(slug)
    sizes_after = {role: len(ROLE_PERMISSIONS[role]) for role in ROLE_PERMISSIONS}
    # Re-registering is a no-op for both PERMISSIONS and ROLE_PERMISSIONS.
    assert out1 == out2
    assert sizes_before == sizes_after


def test_register_partial_levels():
    """Registering only `read` registers the read perm and grants but
    nothing else."""
    slug = _fresh_slug()
    out = register_plugin_permissions(slug, ["read"])
    assert out == [f"plugin.{slug}.read"]
    assert f"plugin.{slug}.read" in PERMISSIONS
    assert f"plugin.{slug}.write" not in PERMISSIONS


def test_register_invalid_level_logs_and_skips():
    """Invalid levels are logged and skipped (don't raise) — the loader
    shouldn't crash on a bad manifest."""
    slug = _fresh_slug()
    out = register_plugin_permissions(slug, ["read", "rwx", "write"])
    # rwx skipped; read + write registered.
    assert out == [f"plugin.{slug}.read", f"plugin.{slug}.write"]


def test_registered_set_includes_recent_registrations():
    slug = _fresh_slug()
    register_all_plugin_levels(slug)
    snapshot = registered_plugin_permissions()
    for level in ("read", "write", "configure", "admin"):
        assert f"plugin.{slug}.{level}" in snapshot


def test_static_permissions_unaffected():
    """Re-affirm that registering plugin permissions doesn't remove or
    replace any static catalog entries."""
    slug = _fresh_slug()
    register_all_plugin_levels(slug)
    # Sample of static perms that must still be present.
    for static in ("system.audit", "plugins.read", "users.manage", "rbac.edit"):
        assert static in PERMISSIONS
