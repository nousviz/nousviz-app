"""Regression: GET /api/plugins is in PUBLIC_GET_PATTERNS, so unauthenticated
callers must NOT receive 401 from inside the handler.

Pre-fix bug: `list_plugins` invoked `get_me(request)` to apply the B305 per-
user allowlist filter. When the request had no session token (share-viewer
bootstrap, plugin-frontend-component loader race, etc.), `get_me` raised
HTTPException(401). The handler's `except HTTPException: raise` then bubbled
that up — turning a route the middleware classifies as public into a 401.

Fix: an HTTPException with status 401 from get_me means "no authenticated
user" — return the unfiltered list rather than masquerading as auth-required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


@pytest.fixture
def stub_list_plugins_deps(monkeypatch: pytest.MonkeyPatch):
    """Stub out the heavy work in list_plugins (plugin-dir scan, catalog
    lookups, sync lookups, RBAC filter) so the test stays focused on the
    auth/exception path."""
    import apps.api.src.routes.plugins as plugins_mod
    import apps.api.src.rbac as rbac_mod
    import apps.api.src.catalog as catalog_mod

    monkeypatch.setattr(plugins_mod, "ACTIVE_PLUGIN_DIRS", [])
    monkeypatch.setattr(
        catalog_mod, "tables_and_drift_for_plugins", lambda ids: {}
    )
    monkeypatch.setattr(plugins_mod, "_fetch_last_sync_batch", lambda ids: {})
    monkeypatch.setattr(
        rbac_mod, "filter_plugins_for_user", lambda plugins, user: plugins
    )


def _patch_get_me_unauthenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force get_me to raise 401 (the in-handler shape that triggered the bug)."""
    import apps.api.src.routes.auth as auth_mod
    import apps.api.src.routes.plugins as plugins_mod

    def _raise_401(request: Request, *args, **kwargs):
        raise HTTPException(401, "Not authenticated")

    monkeypatch.setattr(auth_mod, "get_me", _raise_401)
    monkeypatch.setattr(plugins_mod, "get_me", _raise_401)


def test_list_plugins_returns_200_when_get_me_raises_401(
    monkeypatch: pytest.MonkeyPatch,
    stub_list_plugins_deps,
):
    """GET /api/plugins must succeed (200, empty filtered list) when the
    request carries no valid session, because the middleware whitelists
    this path as public."""
    _patch_get_me_unauthenticated(monkeypatch)

    from apps.api.src.routes.plugins import router as plugins_router

    app = FastAPI()
    app.include_router(plugins_router, prefix="/api")
    client = TestClient(app)

    resp = client.get("/api/plugins")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "plugins" in body
    assert isinstance(body["plugins"], list)


def test_list_plugins_propagates_non_401_http_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    stub_list_plugins_deps,
):
    """A non-401 HTTPException out of get_me (e.g. a 503 from a DB outage
    surfaced as HTTPException) should still propagate — we only swallow
    the 'no auth on a public route' case."""
    import apps.api.src.routes.auth as auth_mod
    import apps.api.src.routes.plugins as plugins_mod

    def _raise_503(request: Request, *args, **kwargs):
        raise HTTPException(503, "DB unavailable")

    monkeypatch.setattr(auth_mod, "get_me", _raise_503)
    monkeypatch.setattr(plugins_mod, "get_me", _raise_503)

    from apps.api.src.routes.plugins import router as plugins_router

    app = FastAPI()
    app.include_router(plugins_router, prefix="/api")
    client = TestClient(app)

    resp = client.get("/api/plugins")
    assert resp.status_code == 503, resp.text
