"""B248 (v0.9.10.7) phase 3: integration tests for `requires_resource()`.

Mounts a fresh FastAPI app with the AuthMiddleware + a dashboard-style
route that uses `requires_resource('dashboard', 'dashboards.read')`.
Monkey-patches the resolver to drive every branch of the resolution
order without needing a Postgres.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _build_app(slug: str):
    """Build a fresh FastAPI app with one dashboard-style route gated by
    `requires_resource('dashboard', 'dashboards.read')`."""
    from apps.api.src.middleware.auth import AuthMiddleware
    from apps.api.src.rbac import requires_resource

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/dashboards/{slug}")
    def _handler(
        slug: str,
        _: None = Depends(requires_resource("dashboard", "dashboards.read")),
    ):
        return {"ok": True, "slug": slug}

    return app


def _patch_get_me(monkeypatch: pytest.MonkeyPatch, *, role: str, user_id: str = "test-user") -> None:
    import apps.api.src.routes.auth as auth_mod
    import apps.api.src.middleware.auth as middleware_mod

    fake_user = {"id": user_id, "role": role, "email": f"{user_id}@example.com"}

    def _fake_get_me(request, *args, **kwargs):
        return fake_user

    monkeypatch.setattr(auth_mod, "get_me", _fake_get_me)
    monkeypatch.setattr(
        middleware_mod, "get_authenticated_identity",
        lambda request: f"session:{user_id}",
    )
    monkeypatch.setenv("AUTH_REQUIRED", "true")


def _patch_resolver(
    monkeypatch: pytest.MonkeyPatch,
    *,
    owner: str | None,
    acl_rows: set[tuple[str, str, str, str, str]],
    default_policy: str,
    role_perms: dict[str, frozenset[str]],
) -> None:
    """Patch the resource_acls helpers + role_has_permission to drive the
    resolver to a deterministic outcome without a DB."""
    import apps.api.src.rbac.resource_acls as acls_mod
    import apps.api.src.rbac.permissions as perms_mod

    monkeypatch.setattr(acls_mod, "_get_resource_owner", lambda rt, rid: owner)
    monkeypatch.setattr(acls_mod, "_get_default_policy", lambda rt: default_policy)
    monkeypatch.setattr(
        acls_mod, "_has_acl_row",
        lambda rt, rid, kind, pid, perm: (rt, rid, kind, pid, perm) in acl_rows,
    )
    monkeypatch.setattr(
        perms_mod, "role_has_permission",
        lambda role, perm: perm in role_perms.get(role, frozenset()),
    )


# ── Tests ─────────────────────────────────────────────────────────────


def test_default_allow_with_role_permission_returns_200(monkeypatch):
    """The pre-B248 default behaviour: viewer holds dashboards.read +
    default-allow on dashboard → 200."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="viewer", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner=None,
        acl_rows=set(),
        default_policy="allow",
        role_perms={"viewer": frozenset({"dashboards.read"})},
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 200, resp.text


def test_default_deny_no_grant_no_owner_returns_403(monkeypatch):
    """Default-deny + role permission alone is NOT enough → 403."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="viewer", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner="other-user",
        acl_rows=set(),
        default_policy="deny",
        role_perms={"viewer": frozenset({"dashboards.read"})},
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 403, resp.text
    assert "dashboards.read" in resp.json()["detail"]


def test_owner_implicit_grant_overrides_default_deny(monkeypatch):
    """Default-deny but the requesting user is the owner → 200."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="viewer", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner="user-1",          # ← matches the requesting user
        acl_rows=set(),
        default_policy="deny",
        role_perms={},            # no role permission needed
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 200


def test_explicit_user_grant_under_default_deny(monkeypatch):
    """Default-deny + explicit user ACL grant → 200."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="viewer", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner="other-user",
        acl_rows={("dashboard", slug, "user", "user-1", "dashboards.read")},
        default_policy="deny",
        role_perms={},
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 200


def test_explicit_role_grant_under_default_deny(monkeypatch):
    """Default-deny + explicit role ACL grant → every user with that role
    gets access."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="analyst", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner="other-user",
        acl_rows={("dashboard", slug, "role", "analyst", "dashboards.read")},
        default_policy="deny",
        role_perms={},
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 200


def test_no_role_no_grant_default_allow_returns_403(monkeypatch):
    """Default-allow but the user holds no role permission and has no
    grant → 403. Default-allow doesn't mean 'allow everyone'; it means
    'role permission is sufficient when held'."""
    slug = f"d-{uuid.uuid4().hex[:8]}"
    app = _build_app(slug)
    _patch_get_me(monkeypatch, role="viewer", user_id="user-1")
    _patch_resolver(
        monkeypatch,
        owner="other-user",
        acl_rows=set(),
        default_policy="allow",
        role_perms={},  # viewer doesn't actually hold dashboards.read here
    )
    client = TestClient(app)
    resp = client.get(f"/api/dashboards/{slug}")
    assert resp.status_code == 403
