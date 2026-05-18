"""B304 (v0.10.0.5): tests for plugin admin-proxy auth path.

Covers the security-critical surfaces:
- SDK helper (issue_admin_session_cookie): cross-plugin minting blocked,
  env-var requirement, cookie shape.
- Middleware (_verify_admin_session_cookie + integration): opt-in is
  mandatory, slug-binding rejects cross-plugin reuse, expired/tampered
  cookies fail closed, non-admin paths ignore the cookie.

Tests do NOT touch a live database. The DB layer is monkey-patched to
return synthetic rows; real-DB integration is covered by the operator
walkthrough in todo/0.9.11/testing/B304-test-plan.md.
"""
from __future__ import annotations

import hashlib
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


# ── SDK helper tests ──────────────────────────────────────────────────


def test_issue_admin_session_cookie_works_without_env_var(
    monkeypatch: pytest.MonkeyPatch,
):
    """v0.10.0.5.2: SDK helper no longer requires NOUSVIZ_PLUGIN_ID env
    var. The api-process context (where plugin routes execute) doesn't
    set per-plugin env vars, so the original 'must be set' requirement
    broke every plugin's bridge route. Now: if env var unset, trust the
    caller's plugin_slug. (Slug-match check still runs when env var IS
    set — see next test.)"""
    from sdk.nousviz_sdk import auth as sdk_auth
    from sdk.nousviz_sdk.auth import issue_admin_session_cookie

    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)

    inserted_rows = []

    class _StubCursor:
        def execute(self, sql, params):
            inserted_rows.append((sql, params))

    class _StubConn:
        def cursor(self):
            return _StubCursor()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sdk_auth, "get_pg_conn", lambda: _StubConn())

    response = Response()
    # Should NOT raise — env var absent is now the normal api-process case.
    issue_admin_session_cookie(
        response, plugin_slug="some-plugin", user_id="u1"
    )
    # Cookie set + row inserted, just as in the happy path.
    assert "nv_admin_some-plugin=" in response.headers.get("set-cookie", "")
    assert len(inserted_rows) == 1


def test_issue_admin_session_cookie_rejects_cross_plugin_minting(
    monkeypatch: pytest.MonkeyPatch,
):
    """A plugin running as `plugin-a` cannot mint a cookie for `plugin-b`.
    SDK-level guard before any DB write or cookie set."""
    from sdk.nousviz_sdk.auth import issue_admin_session_cookie

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "plugin-a")
    response = Response()
    with pytest.raises(ValueError, match="cannot mint cookies for another plugin"):
        issue_admin_session_cookie(
            response, plugin_slug="plugin-b", user_id="u1"
        )


def test_issue_admin_session_cookie_happy_path_sets_cookie_with_correct_attrs(
    monkeypatch: pytest.MonkeyPatch,
):
    """Happy path: cookie set with HttpOnly, Secure, SameSite=Strict,
    Path=/api/plugins/<slug>/admin, Max-Age=ttl. DB row inserted with
    SHA256 hash (raw token NOT in DB)."""
    from sdk.nousviz_sdk import auth as sdk_auth
    from sdk.nousviz_sdk.auth import issue_admin_session_cookie

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "plugin-a")

    inserted_rows = []

    class _StubCursor:
        def execute(self, sql, params):
            inserted_rows.append((sql, params))

    class _StubConn:
        def cursor(self):
            return _StubCursor()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sdk_auth, "get_pg_conn", lambda: _StubConn())

    response = Response()
    issue_admin_session_cookie(
        response,
        plugin_slug="plugin-a",
        user_id="user-uuid-1",
        ttl_seconds=1800,
    )

    # Cookie attrs
    set_cookie = response.headers.get("set-cookie", "")
    assert "nv_admin_plugin-a=" in set_cookie
    assert "Path=/api/plugins/plugin-a/admin" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=strict" in set_cookie.lower()
    assert "Max-Age=1800" in set_cookie

    # DB row: hash, not raw token
    assert len(inserted_rows) == 1
    sql, params = inserted_rows[0]
    assert "INSERT INTO plugin_admin_sessions" in sql
    plugin_id, user_id, token_hash, path_scope, expires_at, ip, ua = params
    assert plugin_id == "plugin-a"
    assert user_id == "user-uuid-1"
    assert path_scope == "/api/plugins/plugin-a/admin"
    # token_hash must be SHA256 hex (64 chars), not the raw token
    assert len(token_hash) == 64
    assert all(c in "0123456789abcdef" for c in token_hash)
    # Expiry roughly 1800s out
    delta = (expires_at - datetime.now(timezone.utc)).total_seconds()
    assert 1700 < delta < 1900


# ── Middleware tests ──────────────────────────────────────────────────


def _build_admin_proxy_app(opted_in_slugs: set[str]):
    """Build a FastAPI app with auth middleware and a stub /admin/* plugin route.
    `opted_in_slugs` lists plugins whose manifest says admin_proxy: true."""
    from apps.api.src.middleware.auth import AuthMiddleware

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/plugins/{slug}/admin/echo")
    def _admin(slug: str):
        return {"slug": slug, "ok": True}

    @app.get("/api/plugins/{slug}/dashboards/{name}")
    def _dash(slug: str, name: str):
        # NB: this matches PUBLIC_GET_PATTERNS so middleware doesn't enforce.
        return {"slug": slug, "name": name}

    @app.get("/api/plugins/{slug}/non-admin")
    def _other(slug: str):
        return {"slug": slug}

    return app


def _patch_admin_proxy_state(
    monkeypatch: pytest.MonkeyPatch,
    opted_in_slugs: set[str],
    valid_token_for: dict | None = None,
):
    """Patch is_admin_proxy_enabled + get_pg_conn so the middleware sees
    a synthetic state.

    valid_token_for: optional dict of {raw_token_hash: (user_id, plugin_id)}
    to simulate a valid plugin_admin_sessions row.
    """
    import apps.api.src.middleware.auth as mw

    monkeypatch.setattr(
        "apps.api.src.plugin_loader.is_admin_proxy_enabled",
        lambda slug: slug in opted_in_slugs,
    )

    valid_token_for = valid_token_for or {}

    class _StubCursor:
        def __init__(self):
            self._row = None

        def execute(self, sql, params):
            if "FROM plugin_admin_sessions" in sql:
                token_hash, plugin_id = params
                entry = valid_token_for.get(token_hash)
                if entry and entry[1] == plugin_id:
                    self._row = (entry[0],)
                else:
                    self._row = None
            elif "api_keys" in sql:
                self._row = None  # No API key matches in these tests
            elif "FROM user_sessions" in sql or "user_sessions" in sql:
                self._row = None  # No session token matches
            else:
                self._row = None

        def fetchone(self):
            return self._row

    class _StubConn:
        def cursor(self):
            return _StubCursor()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _stub_get_pg_conn():
        return _StubConn()

    # Patch every db helper the middleware reaches into.
    monkeypatch.setattr("apps.api.src.db.get_pg_conn", _stub_get_pg_conn)

    monkeypatch.setenv("AUTH_REQUIRED", "true")


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def test_middleware_accepts_valid_admin_cookie_for_opted_in_plugin(
    monkeypatch: pytest.MonkeyPatch,
):
    """Happy path: opted-in plugin + valid cookie → 200."""
    raw = "test-token-1"
    _patch_admin_proxy_state(
        monkeypatch,
        opted_in_slugs={"plugin-a"},
        valid_token_for={_hash_token(raw): ("user-1", "plugin-a")},
    )
    app = _build_admin_proxy_app({"plugin-a"})
    client = TestClient(app)

    resp = client.get(
        "/api/plugins/plugin-a/admin/echo",
        cookies={"nv_admin_plugin-a": raw},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"slug": "plugin-a", "ok": True}


def test_middleware_rejects_admin_cookie_for_non_opted_in_plugin(
    monkeypatch: pytest.MonkeyPatch,
):
    """Regression: a plugin without admin_proxy: true gets 401 even with
    a cookie. Opt-in is mandatory; cookie alone never grants access."""
    raw = "test-token-2"
    _patch_admin_proxy_state(
        monkeypatch,
        opted_in_slugs=set(),  # no plugins opted in
        valid_token_for={_hash_token(raw): ("user-1", "plugin-a")},
    )
    app = _build_admin_proxy_app(set())
    client = TestClient(app)

    resp = client.get(
        "/api/plugins/plugin-a/admin/echo",
        cookies={"nv_admin_plugin-a": raw},
    )
    assert resp.status_code == 401


def test_middleware_rejects_cross_plugin_cookie_reuse(
    monkeypatch: pytest.MonkeyPatch,
):
    """Slug binding: cookie minted for plugin-a is rejected on plugin-b's
    admin path. This is the test that proves Option A eliminates Option
    B's first-administrator race."""
    raw = "test-token-3"
    # Cookie row exists for plugin-a; both plugins are opted in.
    _patch_admin_proxy_state(
        monkeypatch,
        opted_in_slugs={"plugin-a", "plugin-b"},
        valid_token_for={_hash_token(raw): ("user-1", "plugin-a")},
    )
    app = _build_admin_proxy_app({"plugin-a", "plugin-b"})
    client = TestClient(app)

    # Present plugin-a's cookie on plugin-b's admin path
    resp = client.get(
        "/api/plugins/plugin-b/admin/echo",
        cookies={"nv_admin_plugin-b": raw},
    )
    assert resp.status_code == 401


def test_middleware_rejects_tampered_cookie(monkeypatch: pytest.MonkeyPatch):
    """Tampered token → hash mismatch → no row found → 401."""
    raw = "real-token"
    _patch_admin_proxy_state(
        monkeypatch,
        opted_in_slugs={"plugin-a"},
        valid_token_for={_hash_token(raw): ("user-1", "plugin-a")},
    )
    app = _build_admin_proxy_app({"plugin-a"})
    client = TestClient(app)

    resp = client.get(
        "/api/plugins/plugin-a/admin/echo",
        cookies={"nv_admin_plugin-a": "tampered-token"},
    )
    assert resp.status_code == 401


def test_middleware_admin_cookie_ignored_on_non_admin_path(
    monkeypatch: pytest.MonkeyPatch,
):
    """A nv_admin_<slug> cookie attached on a non-admin path is IGNORED
    by the middleware (path doesn't match /admin/.*); the request gets
    the same 401 as without any cookie."""
    raw = "test-token-5"
    _patch_admin_proxy_state(
        monkeypatch,
        opted_in_slugs={"plugin-a"},
        valid_token_for={_hash_token(raw): ("user-1", "plugin-a")},
    )
    app = _build_admin_proxy_app({"plugin-a"})
    client = TestClient(app)

    # Path is /non-admin, not /admin/*
    resp = client.get(
        "/api/plugins/plugin-a/non-admin",
        cookies={"nv_admin_plugin-a": raw},
    )
    assert resp.status_code == 401


def test_middleware_no_cookie_no_header_returns_401(
    monkeypatch: pytest.MonkeyPatch,
):
    """B160 invariant preserved: every /api/plugins/* path still requires
    auth; no cookie + no header = 401, regardless of admin_proxy opt-in."""
    _patch_admin_proxy_state(monkeypatch, opted_in_slugs={"plugin-a"})
    app = _build_admin_proxy_app({"plugin-a"})
    client = TestClient(app)

    resp = client.get("/api/plugins/plugin-a/admin/echo")
    assert resp.status_code == 401


def test_middleware_dashboards_path_remains_public_get(
    monkeypatch: pytest.MonkeyPatch,
):
    """Regression: PUBLIC_GET_PATTERNS still works for the dashboards
    path even after the admin-proxy extension."""
    _patch_admin_proxy_state(monkeypatch, opted_in_slugs=set())
    app = _build_admin_proxy_app(set())
    client = TestClient(app)

    resp = client.get("/api/plugins/whatever/dashboards/main")
    # Should reach the route (no auth required) — this is part of B160's
    # explicit allowlist that B304 must not regress.
    assert resp.status_code == 200


# ── Manifest schema test ──────────────────────────────────────────────


def test_frontend_block_admin_proxy_defaults_to_false():
    """FrontendBlock.admin_proxy defaults to False so existing plugins
    (manifests without the field) parse cleanly without behavior change."""
    from apps.api.src.models.plugins import FrontendBlock

    fb = FrontendBlock(trusted=False, needs_consent=True)
    assert fb.admin_proxy is False


def test_frontend_block_accepts_admin_proxy_true():
    """FrontendBlock.admin_proxy accepts True when manifest opts in."""
    from apps.api.src.models.plugins import FrontendBlock

    fb = FrontendBlock(trusted=False, needs_consent=True, admin_proxy=True)
    assert fb.admin_proxy is True
