"""B305.1 (v0.10.0.6.1): unit tests for `user_can_access_plugin`.

Pure truth-function tests; DB lookup is monkeypatched. Companion to
test_plugin_visibility_filter.py which covers the list-filtering path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


import apps.api.src.rbac.plugin_visibility as pv  # noqa: E402
from apps.api.src.rbac.plugin_visibility import user_can_access_plugin  # noqa: E402


@pytest.fixture
def acl_rows(monkeypatch: pytest.MonkeyPatch):
    """Inject per-user allowed slug sets without touching the DB.

    Mutates rows[user_id] = {"alerts", "webhooks", ...}.
    """
    rows: dict[str, set[str]] = {}

    def _fake_allowed(user_id: str, role: str):
        if (role or "").lower() in pv.UNRESTRICTED_ROLES:
            return None
        slugs = rows.get(str(user_id))
        return slugs if slugs else None

    monkeypatch.setattr(pv, "allowed_plugin_slugs_for_user", _fake_allowed)
    return rows


# ── Truth-function cases ──────────────────────────────────────────────


def test_admin_role_always_passes(acl_rows):
    acl_rows["u-admin"] = {"alerts"}  # rows exist but admin bypasses
    assert user_can_access_plugin("u-admin", "admin", "webhooks") is True


def test_superadmin_role_always_passes(acl_rows):
    acl_rows["u-super"] = {"alerts"}
    assert user_can_access_plugin("u-super", "superadmin", "anything") is True


def test_role_case_insensitive(acl_rows):
    acl_rows["u-admin"] = {"alerts"}
    assert user_can_access_plugin("u-admin", "ADMIN", "webhooks") is True


def test_viewer_with_no_rows_passes(acl_rows):
    # mode='all' for this user → unrestricted
    assert user_can_access_plugin("u-viewer", "viewer", "webhooks") is True


def test_viewer_with_allowlist_passes_in_list(acl_rows):
    acl_rows["u-viewer"] = {"alerts", "webhooks"}
    assert user_can_access_plugin("u-viewer", "viewer", "alerts") is True
    assert user_can_access_plugin("u-viewer", "viewer", "webhooks") is True


def test_viewer_with_allowlist_blocked_outside_list(acl_rows):
    acl_rows["u-viewer"] = {"alerts"}
    assert user_can_access_plugin("u-viewer", "viewer", "webhooks") is False
    assert user_can_access_plugin("u-viewer", "viewer", "sdi-admin") is False


def test_analyst_subject_to_same_rules(acl_rows):
    acl_rows["u-analyst"] = {"alerts"}
    assert user_can_access_plugin("u-analyst", "analyst", "webhooks") is False
    assert user_can_access_plugin("u-analyst", "analyst", "alerts") is True


def test_missing_plugin_slug_passes(acl_rows):
    """Defensive — no plugin named means no plugin-scoped check applies."""
    acl_rows["u-viewer"] = {"alerts"}
    assert user_can_access_plugin("u-viewer", "viewer", "") is True
    assert user_can_access_plugin("u-viewer", "viewer", None) is True


def test_feature_flag_off_always_passes(monkeypatch: pytest.MonkeyPatch, acl_rows):
    monkeypatch.setenv("NOUSVIZ_PER_USER_PLUGIN_FILTER", "false")
    acl_rows["u-viewer"] = {"alerts"}  # restrictive rows exist
    # Flag off ⇒ rollback parity: every call passes.
    assert user_can_access_plugin("u-viewer", "viewer", "webhooks") is True
    assert user_can_access_plugin("u-viewer", "viewer", "sdi-admin") is True


def test_missing_user_id_passes_through(acl_rows):
    """An unauthenticated-but-still-evaluated path (defensive) should
    not throw. Pre-B305.1 behaviour: pass."""
    assert user_can_access_plugin(None, "viewer", "webhooks") is True
