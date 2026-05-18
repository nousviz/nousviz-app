"""B247 (v0.9.10.6): tests for runtime per-plugin permission enforcement.

Mirrors what _auto_register_plugin_routes does: registers a
`plugin.<slug>.<level>` permission, registers the route, hits it
through the actual middleware via TestClient, and asserts that:
- A user holding the permission gets 200.
- A user not holding the permission gets 403 with a permission-deny detail.

These tests don't go through the live database — they monkey-patch
get_me to return synthetic identities. That keeps them fast (<0.1s)
and CI-runnable without a Postgres requirement.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _build_test_app(slug: str, level: str) -> FastAPI:
    """Build a fresh FastAPI app with one plugin-style route registered
    under `plugin.<slug>.<level>`. Mirrors what the real loader does
    end-to-end so the middleware sees ROUTE_PERMISSIONS the same way
    it does in production.
    """
    from apps.api.src.middleware.auth import AuthMiddleware
    from apps.api.src.rbac import register_route
    from apps.api.src.rbac.plugin_permissions import register_all_plugin_levels

    register_all_plugin_levels(slug)

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    plugin_path = f"/api/plugins/{slug}/data"
    perm = f"plugin.{slug}.{level}"
    register_route("GET", plugin_path, perm)

    @app.get(plugin_path)
    def _handler():
        return {"ok": True, "slug": slug}

    return app


def _patch_get_me(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    """Override routes.auth.get_me to return a synthetic user with the
    given role. The middleware reads role via get_me — patching this
    sidesteps the DB.
    """
    from apps.api.src import routes  # noqa: F401  — ensure routes pkg imported
    import apps.api.src.routes.auth as auth_mod
    import apps.api.src.middleware.auth as middleware_mod

    fake_user = {"id": "test-user", "role": role, "email": "test@example.com"}

    def _fake_get_me(request, *args, **kwargs):
        return fake_user

    monkeypatch.setattr(auth_mod, "get_me", _fake_get_me)
    # The middleware imports get_me lazily inside its helper —
    # we still need to patch the routes.auth attribute since that's
    # the import target.

    # Auth middleware also calls get_authenticated_identity to decide
    # whether the request is authenticated. Patch that to return a
    # truthy session marker so the rbac check actually runs.
    monkeypatch.setattr(
        middleware_mod, "get_authenticated_identity",
        lambda request: f"session:{fake_user['id']}",
    )

    # AUTH_REQUIRED must be true for the middleware to enforce — the
    # default in dev is false.
    monkeypatch.setenv("AUTH_REQUIRED", "true")


def test_plugin_read_route_allows_viewer(monkeypatch: pytest.MonkeyPatch):
    """A `read`-level route is granted to viewer+ by default."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = _build_test_app(slug, "read")
    _patch_get_me(monkeypatch, "viewer")
    client = TestClient(app)
    resp = client.get(f"/api/plugins/{slug}/data")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True, "slug": slug}


def test_plugin_admin_route_denies_viewer(monkeypatch: pytest.MonkeyPatch):
    """An `admin`-level route is granted to superadmin only by default —
    a viewer attempting to call it gets 403 with the permission name."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = _build_test_app(slug, "admin")
    _patch_get_me(monkeypatch, "viewer")
    client = TestClient(app)
    resp = client.get(f"/api/plugins/{slug}/data")
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert "Permission denied" in body["detail"]
    assert f"plugin.{slug}.admin" in body["detail"]


def test_plugin_admin_route_allows_superadmin(monkeypatch: pytest.MonkeyPatch):
    """Same admin-level route grants superadmin."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = _build_test_app(slug, "admin")
    _patch_get_me(monkeypatch, "superadmin")
    client = TestClient(app)
    resp = client.get(f"/api/plugins/{slug}/data")
    assert resp.status_code == 200, resp.text


def test_plugin_configure_route_denies_analyst(monkeypatch: pytest.MonkeyPatch):
    """`configure`-level is admin+ — analyst doesn't hold it."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = _build_test_app(slug, "configure")
    _patch_get_me(monkeypatch, "analyst")
    client = TestClient(app)
    resp = client.get(f"/api/plugins/{slug}/data")
    assert resp.status_code == 403


def test_plugin_write_route_allows_analyst(monkeypatch: pytest.MonkeyPatch):
    """`write`-level is analyst+."""
    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = _build_test_app(slug, "write")
    _patch_get_me(monkeypatch, "analyst")
    client = TestClient(app)
    resp = client.get(f"/api/plugins/{slug}/data")
    assert resp.status_code == 200
