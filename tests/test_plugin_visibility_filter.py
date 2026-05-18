"""B305 (v0.10.0.6): unit tests for the per-user plugin visibility filter.

Pure-logic tests for `filter_plugins_for_user`, `allowed_plugin_slugs_for_user`,
and the feature flag. The DB-touching helpers are monkeypatched so these
run without Postgres. Live-DB validation lives in the test plan's
Section 2-3 staging checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


import apps.api.src.rbac.plugin_visibility as pv  # noqa: E402
from apps.api.src.rbac.plugin_visibility import (  # noqa: E402
    UNRESTRICTED_ROLES,
    allowed_plugin_slugs_for_user,
    filter_plugins_for_user,
    is_per_user_filter_enabled,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def acl_rows(monkeypatch: pytest.MonkeyPatch):
    """Lets each test inject the set of plugin-type ACL rows for a user.

    Test mutates `rows[user_id] = {"alerts", "webhooks"}`; the resolver
    reads that instead of hitting the DB.
    """
    rows: dict[str, set[str]] = {}

    class _FakeCursor:
        def __init__(self, principal_id: str):
            self._principal_id = principal_id
            self._rows: list[tuple[str]] = []

        def execute(self, sql: str, params=None):
            # Single SELECT shape used by allowed_plugin_slugs_for_user
            # and get_user_plugin_access.
            if not params:
                self._rows = []
                return
            pid = params[0] if isinstance(params, (list, tuple)) else None
            slugs = rows.get(str(pid), set())
            self._rows = [(s,) for s in sorted(slugs)]

        def fetchall(self):
            return list(self._rows)

        def fetchone(self):
            return self._rows[0] if self._rows else None

    class _FakeConn:
        def __init__(self):
            self._cursor: _FakeCursor | None = None

        def cursor(self):
            self._cursor = _FakeCursor("")
            return self._cursor

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_get_pg_conn():
        return _FakeConn()

    monkeypatch.setattr(pv, "get_pg_conn", _fake_get_pg_conn)
    return rows


# ── Feature flag ──────────────────────────────────────────────────────


def test_filter_default_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NOUSVIZ_PER_USER_PLUGIN_FILTER", raising=False)
    assert is_per_user_filter_enabled() is True


@pytest.mark.parametrize("val", ["false", "FALSE", "0", "no", "off", "  False  "])
def test_filter_off_by_env(monkeypatch: pytest.MonkeyPatch, val: str):
    monkeypatch.setenv("NOUSVIZ_PER_USER_PLUGIN_FILTER", val)
    assert is_per_user_filter_enabled() is False


@pytest.mark.parametrize("val", ["true", "1", "yes", "on", "anything-else"])
def test_filter_on_for_truthy(monkeypatch: pytest.MonkeyPatch, val: str):
    monkeypatch.setenv("NOUSVIZ_PER_USER_PLUGIN_FILTER", val)
    assert is_per_user_filter_enabled() is True


# ── allowed_plugin_slugs_for_user ─────────────────────────────────────


def test_admin_role_bypasses_filter(acl_rows):
    acl_rows["u-admin"] = {"alerts"}  # rows exist, but admin bypasses
    assert allowed_plugin_slugs_for_user("u-admin", "admin") is None


def test_superadmin_role_bypasses_filter(acl_rows):
    acl_rows["u-super"] = {"alerts"}
    assert allowed_plugin_slugs_for_user("u-super", "superadmin") is None


def test_zero_rows_returns_none(acl_rows):
    # No entry for u-viewer → no restriction.
    assert allowed_plugin_slugs_for_user("u-viewer", "viewer") is None


def test_one_row_returns_singleton(acl_rows):
    acl_rows["u-viewer"] = {"alerts"}
    result = allowed_plugin_slugs_for_user("u-viewer", "viewer")
    assert result == {"alerts"}


def test_multiple_rows_returns_set(acl_rows):
    acl_rows["u-viewer"] = {"alerts", "webhooks", "sdi-admin"}
    result = allowed_plugin_slugs_for_user("u-viewer", "viewer")
    assert result == {"alerts", "webhooks", "sdi-admin"}


def test_role_case_insensitive(acl_rows):
    acl_rows["u-admin"] = {"alerts"}
    # Mixed case admin role still bypasses.
    assert allowed_plugin_slugs_for_user("u-admin", "Admin") is None
    assert allowed_plugin_slugs_for_user("u-admin", "SUPERADMIN") is None


def test_missing_user_id_returns_none(acl_rows):
    assert allowed_plugin_slugs_for_user("", "viewer") is None


# ── filter_plugins_for_user ───────────────────────────────────────────


def _plugins(*entries: dict) -> list[dict]:
    return list(entries)


def test_filter_admin_returns_everything(acl_rows):
    acl_rows["u-admin"] = {"alerts"}  # restrictive rows exist
    plugins = _plugins(
        {"id": "alerts", "type": None},
        {"id": "webhooks", "type": None},
        {"id": "clickhouse", "type": "utility"},
    )
    user = {"id": "u-admin", "role": "admin"}
    assert filter_plugins_for_user(plugins, user) == plugins


def test_filter_viewer_unrestricted_returns_everything(acl_rows):
    plugins = _plugins(
        {"id": "alerts", "type": None},
        {"id": "webhooks", "type": None},
    )
    user = {"id": "u-viewer", "role": "viewer"}
    # zero rows → unrestricted
    assert filter_plugins_for_user(plugins, user) == plugins


def test_filter_viewer_restricted_returns_allowed_plus_utilities(acl_rows):
    acl_rows["u-viewer"] = {"alerts"}
    plugins = _plugins(
        {"id": "alerts", "type": None},
        {"id": "webhooks", "type": None},
        {"id": "sdi-admin", "type": None},
        {"id": "clickhouse", "type": "utility"},
        {"id": "postgres", "type": "utility"},
    )
    user = {"id": "u-viewer", "role": "viewer"}
    result = filter_plugins_for_user(plugins, user)
    ids = {p["id"] for p in result}
    assert ids == {"alerts", "clickhouse", "postgres"}


def test_filter_returns_full_list_when_flag_off(
    monkeypatch: pytest.MonkeyPatch, acl_rows
):
    monkeypatch.setenv("NOUSVIZ_PER_USER_PLUGIN_FILTER", "false")
    acl_rows["u-viewer"] = {"alerts"}
    plugins = _plugins(
        {"id": "alerts", "type": None},
        {"id": "webhooks", "type": None},
    )
    user = {"id": "u-viewer", "role": "viewer"}
    assert filter_plugins_for_user(plugins, user) == plugins


def test_filter_analyst_restricted(acl_rows):
    """Analyst sees the same restriction as viewer — role isn't in
    UNRESTRICTED_ROLES."""
    acl_rows["u-analyst"] = {"webhooks"}
    plugins = _plugins(
        {"id": "alerts", "type": None},
        {"id": "webhooks", "type": None},
    )
    user = {"id": "u-analyst", "role": "analyst"}
    result = filter_plugins_for_user(plugins, user)
    assert [p["id"] for p in result] == ["webhooks"]


def test_filter_empty_plugin_list_returns_empty(acl_rows):
    acl_rows["u-viewer"] = {"alerts"}
    user = {"id": "u-viewer", "role": "viewer"}
    assert filter_plugins_for_user([], user) == []


def test_filter_user_with_missing_id(acl_rows):
    """Defensive: no id on the user dict → no restriction (no DB lookup
    possible). Matches the "fail open" behaviour of the resolver."""
    plugins = _plugins({"id": "alerts", "type": None})
    user = {"role": "viewer"}  # no id
    assert filter_plugins_for_user(plugins, user) == plugins


# ── Sanity ────────────────────────────────────────────────────────────


def test_unrestricted_roles_contract():
    """UNRESTRICTED_ROLES is the public surface — pin both members so
    future role additions don't silently leak."""
    assert UNRESTRICTED_ROLES == frozenset({"admin", "superadmin"})
