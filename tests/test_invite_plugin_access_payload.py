"""B305 (v0.10.0.6): unit tests for the invite-time plugin_access
payload validator and the POST /api/auth/users/invite shape contract.

Pure validator tests — `_validate_plugin_access_payload` lives in
routes/auth.py. We monkeypatch `_installed_slugs` to control the
installed-plugin universe so tests don't depend on plugin filesystem
state.

End-to-end invite + invite-acceptance round-trips live in the test
plan's Section 4 (staging walkthrough); they require a live DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


import apps.api.src.routes.auth as auth_mod  # noqa: E402
from apps.api.src.routes.auth import _validate_plugin_access_payload  # noqa: E402


@pytest.fixture
def fake_installed(monkeypatch: pytest.MonkeyPatch):
    """Pin the installed-plugin universe for the validator."""
    universe: set[str] = {"alerts", "webhooks", "sdi-admin", "clickhouse"}

    import apps.api.src.routes.plugins as plugins_mod

    monkeypatch.setattr(plugins_mod, "_installed_slugs", lambda: universe)
    return universe


# ── Shape errors ──────────────────────────────────────────────────────


def test_rejects_non_dict_payload(fake_installed):
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_access_payload("not a dict")  # type: ignore[arg-type]
    assert exc.value.status_code == 400
    assert "object" in str(exc.value.detail).lower()


def test_rejects_missing_mode(fake_installed):
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_access_payload({"plugin_ids": ["alerts"]})
    assert exc.value.status_code == 400
    assert "mode" in str(exc.value.detail).lower()


def test_rejects_unknown_mode(fake_installed):
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_access_payload({"mode": "everything", "plugin_ids": []})
    assert exc.value.status_code == 400


def test_rejects_non_list_plugin_ids(fake_installed):
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_access_payload({"mode": "specific", "plugin_ids": "alerts"})
    assert exc.value.status_code == 400


# ── mode='all' ────────────────────────────────────────────────────────


def test_mode_all_returns_empty_list(fake_installed):
    mode, slugs = _validate_plugin_access_payload({"mode": "all", "plugin_ids": []})
    assert mode == "all"
    assert slugs == []


def test_mode_all_ignores_plugin_ids(fake_installed):
    """mode='all' is unrestricted — plugin_ids is irrelevant. We don't
    even validate it against the installed universe."""
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "all", "plugin_ids": ["does-not-exist"]}
    )
    assert mode == "all"
    assert slugs == []


# ── mode='specific' ───────────────────────────────────────────────────


def test_mode_specific_with_known_slugs(fake_installed):
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "specific", "plugin_ids": ["alerts", "webhooks"]}
    )
    assert mode == "specific"
    assert sorted(slugs) == ["alerts", "webhooks"]


def test_mode_specific_with_unknown_slug_rejects(fake_installed):
    with pytest.raises(HTTPException) as exc:
        _validate_plugin_access_payload(
            {"mode": "specific", "plugin_ids": ["alerts", "ghost-plugin"]}
        )
    assert exc.value.status_code == 400
    assert "ghost-plugin" in str(exc.value.detail)


def test_mode_specific_empty_collapses_to_all(fake_installed):
    """Invariant: zero ACL rows ⇔ unrestricted. So an empty 'specific'
    list collapses to 'all' to keep the resolver consistent."""
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "specific", "plugin_ids": []}
    )
    assert mode == "all"
    assert slugs == []


def test_mode_specific_strips_whitespace_and_blanks(fake_installed):
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "specific", "plugin_ids": ["  alerts  ", "", "webhooks", "   "]}
    )
    assert mode == "specific"
    assert sorted(slugs) == ["alerts", "webhooks"]


def test_mode_specific_with_only_blanks_collapses_to_all(fake_installed):
    """Blanks get stripped; if nothing survives, the payload collapses
    to 'all'."""
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "specific", "plugin_ids": ["  ", ""]}
    )
    assert mode == "all"


def test_mode_normalises_case(fake_installed):
    """Operators sending `Specific` from a JSON form should not 400."""
    mode, slugs = _validate_plugin_access_payload(
        {"mode": "SPECIFIC", "plugin_ids": ["alerts"]}
    )
    assert mode == "specific"
    assert slugs == ["alerts"]


# ── InviteRequest contract ────────────────────────────────────────────


def test_invite_request_accepts_plugin_access_field():
    """The Pydantic model must accept the new optional plugin_access
    field and default it to None (so older clients without the field
    keep working)."""
    req = auth_mod.InviteRequest(email="x@example.com", role="viewer")
    assert req.plugin_access is None


def test_invite_request_round_trip_plugin_access():
    req = auth_mod.InviteRequest(
        email="x@example.com",
        role="viewer",
        plugin_access={"mode": "specific", "plugin_ids": ["alerts"]},
    )
    assert req.plugin_access == {"mode": "specific", "plugin_ids": ["alerts"]}
