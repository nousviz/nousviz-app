"""B248 (v0.9.10.7): unit tests for the resource-ACL resolver.

Covers `check_resource_access` resolution order (owner > user grant >
role grant > role permission > default policy). Monkeypatches the
DB-touching helpers so tests run without Postgres.

Migration round-trip is tested separately via the `installer` smoke
test on a real DB; here we focus on the resolver logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


import apps.api.src.rbac.resource_acls as acls_mod  # noqa: E402
from apps.api.src.rbac.resource_acls import (  # noqa: E402
    check_resource_access,
    known_resource_types,
)


@pytest.fixture
def acls_world(monkeypatch: pytest.MonkeyPatch):
    """Fixture that lets each test inject:
      - the resource's owner (or None)
      - the set of (kind, id, perm) ACL rows that exist
      - the default policy ('allow' or 'deny')

    Returns a `world` dict the test mutates; the resolver reads from it.
    """
    world = {
        "owner": None,
        "acl_rows": set(),  # set of (resource_type, resource_id, kind, id, permission)
        "default_policy": "allow",
        "role_perms": {},   # role → frozenset of perms
    }

    def _fake_get_owner(rt, rid):
        return world["owner"]

    def _fake_default(rt):
        return world["default_policy"]

    def _fake_has_acl(rt, rid, kind, pid, perm):
        return (rt, rid, kind, pid, perm) in world["acl_rows"]

    monkeypatch.setattr(acls_mod, "_get_resource_owner", _fake_get_owner)
    monkeypatch.setattr(acls_mod, "_get_default_policy", _fake_default)
    monkeypatch.setattr(acls_mod, "_has_acl_row", _fake_has_acl)

    # role_has_permission lives in .permissions; patch the import target.
    import apps.api.src.rbac.permissions as perms_mod

    def _fake_role_has(role, perm):
        return perm in world["role_perms"].get(role, frozenset())

    monkeypatch.setattr(perms_mod, "role_has_permission", _fake_role_has)
    return world


# ── Resolution order ──────────────────────────────────────────────────


def test_owner_implicit_grant_for_read(acls_world):
    """The resource's created_by user gets read + write implicitly,
    even with default-deny + no role permission + no ACL rows."""
    acls_world["owner"] = "user-1"
    acls_world["default_policy"] = "deny"
    acls_world["role_perms"] = {}  # no role permissions

    user = {"id": "user-1", "role": "viewer"}
    assert check_resource_access(user, "dashboards.read", "dashboard", "foo")
    assert check_resource_access(user, "dashboards.write", "dashboard", "foo")


def test_owner_implicit_grant_does_not_apply_to_unrelated_perms(acls_world):
    """The owner gets read + write only; not e.g. dashboards.delete
    (we don't have such a perm; using a sentinel here)."""
    acls_world["owner"] = "user-1"
    acls_world["default_policy"] = "deny"

    user = {"id": "user-1", "role": "viewer"}
    # `dashboards.delete` is not in the implicit-grant list — should fall
    # through to role/ACL/policy checks. Without role perm or grant: deny.
    assert not check_resource_access(user, "dashboards.delete", "dashboard", "foo")


def test_explicit_user_grant_works_under_default_deny(acls_world):
    """Explicit user grant lets a user without role perm read."""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "deny"
    acls_world["role_perms"] = {}
    acls_world["acl_rows"].add(("dashboard", "foo", "user", "user-1", "dashboards.read"))

    user = {"id": "user-1", "role": "viewer"}
    assert check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_explicit_role_grant_works_under_default_deny(acls_world):
    """Explicit role grant grants every user holding that role."""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "deny"
    acls_world["role_perms"] = {}
    acls_world["acl_rows"].add(("dashboard", "foo", "role", "analyst", "dashboards.read"))

    user = {"id": "user-1", "role": "analyst"}
    assert check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_role_permission_grants_under_default_allow(acls_world):
    """Default-allow + role permission = access. (Current behaviour
    pre-B248, preserved by the default-allow seed.)"""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "allow"
    acls_world["role_perms"] = {"viewer": frozenset({"dashboards.read"})}

    user = {"id": "user-1", "role": "viewer"}
    assert check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_role_permission_alone_not_enough_under_default_deny(acls_world):
    """Default-deny means a role permission alone is NOT sufficient —
    the user needs an explicit grant or to be the owner."""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "deny"
    acls_world["role_perms"] = {"viewer": frozenset({"dashboards.read"})}

    user = {"id": "user-1", "role": "viewer"}
    assert not check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_user_grant_overrides_default_deny(acls_world):
    """User grant trumps default-deny."""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "deny"
    acls_world["role_perms"] = {"viewer": frozenset({"dashboards.read"})}
    acls_world["acl_rows"].add(("dashboard", "foo", "user", "user-1", "dashboards.read"))

    user = {"id": "user-1", "role": "viewer"}
    assert check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_no_role_no_grant_no_owner_no_access(acls_world):
    """The base case: nothing matches, deny."""
    acls_world["owner"] = "owner-7"
    acls_world["default_policy"] = "allow"  # default behaviour
    acls_world["role_perms"] = {}  # no role permissions for this user

    user = {"id": "user-1", "role": "viewer"}
    assert not check_resource_access(user, "dashboards.read", "dashboard", "foo")


def test_empty_user_returns_false(acls_world):
    """Defensive: None user always denied."""
    assert not check_resource_access(None, "dashboards.read", "dashboard", "foo")
    assert not check_resource_access({}, "dashboards.read", "dashboard", "foo")


# ── Registry sanity ───────────────────────────────────────────────────


def test_known_resource_types_lists_5():
    types = known_resource_types()
    assert set(types) == {"dashboard", "fusion", "connection", "share", "plugin"}


# ── Default-policy validation ────────────────────────────────────────


def test_set_default_policy_rejects_invalid_policy(monkeypatch):
    from apps.api.src.rbac.resource_acls import set_default_policy
    with pytest.raises(ValueError, match="policy must be"):
        set_default_policy("dashboard", "rwx")


def test_set_default_policy_rejects_unknown_type():
    from apps.api.src.rbac.resource_acls import set_default_policy
    with pytest.raises(ValueError, match="unknown resource_type"):
        set_default_policy("teapot", "deny")
