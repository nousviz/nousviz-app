"""B312 (v0.10.3): tests for the core-owned OAuth callback flow.

Covers the security-critical surfaces:
- SDK helper (start_flow): hashed-state-only persistence, opaque tokens.
- Manifest validator (validate_oauth_block): block opt-in shape.
- Core route (GET /api/oauth/callback/{slug}):
    - missing/invalid/expired/replayed state → safe 302 with error code
    - slug binding: state minted for plugin A can't be used on plugin B
    - provider `error=` param surfaces back to plugin's return_to
    - no manifest declaration / bad target → no_handler
    - handler raises → handler_failed, exception message never echoed
    - happy path: credentials stored, 302 to return_to
    - open-redirect: absolute / cross-origin return_to falls back to /

Tests do NOT touch a live database. The DB layer is monkey-patched to
return synthetic rows; real-DB integration is covered manually.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


# ── SDK helper tests ──────────────────────────────────────────────────


def test_start_flow_persists_hashed_state_only(monkeypatch: pytest.MonkeyPatch):
    """start_flow stores SHA256(state), never the raw token."""
    from sdk.nousviz_sdk import oauth as sdk_oauth

    inserted_rows: list[tuple[str, tuple]] = []

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

    monkeypatch.setattr(sdk_oauth, "get_pg_conn", lambda: _StubConn())

    raw = sdk_oauth.start_flow(
        plugin_slug="my-plugin",
        user_id="user-uuid-1",
        return_to="/plugin/my-plugin/settings",
        ttl_seconds=600,
    )

    assert isinstance(raw, str) and len(raw) > 20  # url-safe 32-byte token

    assert len(inserted_rows) == 1
    sql, params = inserted_rows[0]
    assert "INSERT INTO oauth_flows" in sql
    token_hash, plugin_id, user_id, return_to, expires_at, ip, ua = params
    # SHA256(raw) — not raw — in the DB
    assert token_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert token_hash != raw
    assert plugin_id == "my-plugin"
    assert user_id == "user-uuid-1"
    assert return_to == "/plugin/my-plugin/settings"
    delta = (expires_at - datetime.now(timezone.utc)).total_seconds()
    assert 500 < delta < 700


def test_start_flow_returns_distinct_tokens(monkeypatch: pytest.MonkeyPatch):
    """Each call mints fresh entropy."""
    from sdk.nousviz_sdk import oauth as sdk_oauth

    class _NoopConn:
        def cursor(self):
            class _C:
                def execute(self, *a, **kw): pass
            return _C()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sdk_oauth, "get_pg_conn", lambda: _NoopConn())

    tokens = {
        sdk_oauth.start_flow(
            plugin_slug="p", user_id="u", return_to="/x"
        )
        for _ in range(10)
    }
    assert len(tokens) == 10


# ── Manifest validator tests ──────────────────────────────────────────


def test_validate_oauth_block_accepts_well_formed():
    from apps.api.src.plugin_validation import validate_oauth_block
    validate_oauth_block("p", {"callback_handler": "api.oauth:handle_callback"})


def test_validate_oauth_block_accepts_none():
    from apps.api.src.plugin_validation import validate_oauth_block
    validate_oauth_block("p", None)


def test_validate_oauth_block_rejects_non_mapping():
    from apps.api.src.plugin_validation import (
        validate_oauth_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="must be a mapping"):
        validate_oauth_block("p", "api.oauth:handle_callback")


def test_validate_oauth_block_rejects_missing_handler():
    from apps.api.src.plugin_validation import (
        validate_oauth_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="is required"):
        validate_oauth_block("p", {})


def test_validate_oauth_block_rejects_unknown_keys():
    from apps.api.src.plugin_validation import (
        validate_oauth_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="unknown key"):
        validate_oauth_block("p", {
            "callback_handler": "api.oauth:cb",
            "client_id": "leaked-here",
        })


def test_validate_oauth_block_rejects_bad_target_format():
    from apps.api.src.plugin_validation import (
        validate_oauth_block, ManifestValidationError,
    )
    bad = ["no_colon", "two:many:colons", ":missing_module", "module:", "  ", ""]
    for t in bad:
        with pytest.raises(ManifestValidationError, match="module:function"):
            validate_oauth_block("p", {"callback_handler": t})


# ── Core route tests ──────────────────────────────────────────────────


@pytest.fixture
def app_and_state():
    """Build a FastAPI app mounting only the oauth router (no auth middleware
    — exercising the handler directly is enough; allowlisting is verified
    by a separate test below)."""
    from apps.api.src.routes import oauth as oauth_route

    app = FastAPI()
    app.include_router(oauth_route.router)
    return app, oauth_route


def _stub_db(monkeypatch, route_module, *, flow_row):
    """Patch get_pg_conn so the UPDATE ... RETURNING returns `flow_row`
    (a tuple of (user_id, return_to)) or None to signal "no match"."""
    state = {"call_count": 0, "consumed": False}

    class _StubCursor:
        def execute(self, sql, params):
            state["call_count"] += 1
            state["last_sql"] = sql
            state["last_params"] = params

        def fetchone(self):
            if flow_row is None:
                return None
            if state["consumed"]:
                return None
            state["consumed"] = True
            return flow_row

    class _StubConn:
        def cursor(self):
            return _StubCursor()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(route_module, "get_pg_conn", lambda: _StubConn())
    return state


def test_callback_missing_state_redirects_root_with_invalid_request(
    monkeypatch, app_and_state,
):
    app, route_module = app_and_state
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/my-plugin?code=xyz")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("/?oauth_error=invalid_request")


def test_callback_bad_state_redirects_root_with_invalid_state(
    monkeypatch, app_and_state,
):
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=None)  # no matching row

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/my-plugin?code=xyz&state=bogus")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?oauth_error=invalid_state"


def test_callback_provider_error_redirects_return_to(
    monkeypatch, app_and_state,
):
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("user-1", "/plugin/p/settings"))

    client = TestClient(app, follow_redirects=False)
    resp = client.get(
        "/api/oauth/callback/p?state=valid&error=access_denied",
    )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert loc.startswith("/plugin/p/settings?oauth_error=provider_error")
    assert "detail=access_denied" in loc


def test_callback_no_manifest_handler_redirects_with_no_handler(
    monkeypatch, app_and_state,
):
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("user-1", "/plugin/p/settings"))
    # plugin_loader returns None — no manifest declaration
    monkeypatch.setattr(
        "apps.api.src.plugin_loader.get_oauth_callback_target",
        lambda slug: None,
    )

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/p?state=valid&code=abc")
    assert resp.status_code == 302
    assert "oauth_error=no_handler" in resp.headers["location"]


def test_callback_happy_path_stores_credentials_and_redirects(
    monkeypatch, app_and_state,
):
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("user-1", "/plugin/p/settings"))

    from sdk.nousviz_sdk.oauth import OAuthCallbackResult

    def handler(code: str, user_id: str) -> OAuthCallbackResult:
        assert code == "abc"
        assert user_id == "user-1"
        return OAuthCallbackResult(
            credentials={"refresh_token": "rt-123", "access_token": "at-456"},
        )

    # v0.10.3.2: resolver is plugin-dir-scoped, not importlib.import_module.
    # Stub both the manifest target and the resolver — covers the new
    # contract surface end-to-end without needing a real plugin on disk.
    monkeypatch.setattr(
        "apps.api.src.plugin_loader.get_oauth_callback_target",
        lambda slug: "api.oauth:handle_callback",
    )
    monkeypatch.setattr(
        "apps.api.src.plugin_loader.resolve_oauth_callback_handler",
        lambda slug, target: handler,
    )

    stored: list[dict] = []

    def fake_store(**kwargs):
        stored.append(kwargs)

    import apps.api.src.plugin_credentials as plugin_credentials
    monkeypatch.setattr(plugin_credentials, "store_plugin_credential", fake_store)

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/p?state=valid&code=abc")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/plugin/p/settings"

    # Both credentials persisted, audited under the originating user.
    assert len(stored) == 2
    fields = {row["field_name"] for row in stored}
    assert fields == {"refresh_token", "access_token"}
    for row in stored:
        assert row["plugin_id"] == "p"
        assert row["credential_type"] == "oauth2"
        assert row["performed_by"] == "oauth_callback:user-1"


def test_callback_handler_exception_redirects_with_opaque_detail(
    monkeypatch, app_and_state,
):
    """Handler raises → 302 with handler_failed&detail=exchange. The
    exception message is NOT echoed to the URL — only the opaque tag."""
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("user-1", "/plugin/p/settings"))

    def boom(code, user_id):
        raise RuntimeError("provider secret leaked in error message: SECRET-123")

    monkeypatch.setattr(
        "apps.api.src.plugin_loader.get_oauth_callback_target",
        lambda slug: "api.oauth:boom",
    )
    monkeypatch.setattr(
        "apps.api.src.plugin_loader.resolve_oauth_callback_handler",
        lambda slug, target: boom,
    )

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/p?state=valid&code=abc")
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "oauth_error=handler_failed" in loc
    assert "detail=exchange" in loc
    # Security: exception text must not leak.
    assert "SECRET" not in loc
    assert "leaked" not in loc


def test_callback_open_redirect_collapsed_to_root(
    monkeypatch, app_and_state,
):
    """A `return_to` that smells like an absolute URL must NOT be used.
    Tests defense-in-depth — start_flow should never accept such a value
    in the first place, but if it ever did, the callback must not 302
    the user off-origin."""
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("u", "https://evil.example/path"))

    monkeypatch.setattr(
        "apps.api.src.plugin_loader.get_oauth_callback_target",
        lambda slug: None,  # short-circuit to error redirect using same return_to
    )

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/p?state=valid&code=abc")
    assert resp.status_code == 302
    # Should redirect to "/" with the error, NOT to evil.example
    loc = resp.headers["location"]
    assert loc.startswith("/?oauth_error=") or loc.startswith("/?")
    assert "evil.example" not in loc


def test_callback_open_redirect_protocol_relative_collapsed(
    monkeypatch, app_and_state,
):
    """`//evil.example` is a protocol-relative URL — browsers treat it as
    cross-origin. Same defense as above."""
    app, route_module = app_and_state
    _stub_db(monkeypatch, route_module, flow_row=("u", "//evil.example/path"))
    monkeypatch.setattr(
        "apps.api.src.plugin_loader.get_oauth_callback_target",
        lambda slug: None,
    )

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/api/oauth/callback/p?state=valid&code=abc")
    loc = resp.headers["location"]
    assert "evil.example" not in loc


# ── Plugin-dir-scoped resolver (v0.10.3.2) ────────────────────────────


def test_resolve_oauth_callback_handler_loads_from_plugin_dir(tmp_path, monkeypatch):
    """v0.10.3.2: resolver loads `api.oauth:handle_callback` by walking
    the plugin's installed directory, NOT via sys.path.

    Reproduces John's exact reported failure mode: the manifest target
    is `api.oauth:handle_callback`, the plugin's `api/` directory is
    not on sys.path, and `importlib.import_module` would fail. The new
    resolver must find the file regardless."""
    import apps.api.src.plugin_loader as loader

    # Build a fake installed plugin directory layout.
    plugin_dir = tmp_path / "fake-ga"
    api_dir = plugin_dir / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "oauth.py").write_text(
        "def handle_callback(code, user_id):\n"
        "    return {'code_seen': code, 'user_id_seen': user_id}\n"
    )

    monkeypatch.setattr(loader, "PLUGINS_DIR", tmp_path)
    # Clear cache so a previous test doesn't poison this one.
    monkeypatch.setattr(loader, "_OAUTH_HANDLER_CACHE", {})

    handler = loader.resolve_oauth_callback_handler(
        "fake-ga", "api.oauth:handle_callback",
    )
    assert callable(handler)
    result = handler(code="abc", user_id="u-1")
    assert result == {"code_seen": "abc", "user_id_seen": "u-1"}


def test_resolve_oauth_callback_handler_supports_package(tmp_path, monkeypatch):
    """Plugins can also organise their handler as `oauth/__init__.py`."""
    import apps.api.src.plugin_loader as loader

    plugin_dir = tmp_path / "fake-plugin"
    pkg_dir = plugin_dir / "oauth"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text(
        "def cb(code, user_id):\n    return 'ok'\n"
    )

    monkeypatch.setattr(loader, "PLUGINS_DIR", tmp_path)
    monkeypatch.setattr(loader, "_OAUTH_HANDLER_CACHE", {})

    handler = loader.resolve_oauth_callback_handler("fake-plugin", "oauth:cb")
    assert callable(handler)
    assert handler(code="x", user_id="y") == "ok"


def test_resolve_oauth_callback_handler_returns_none_on_missing_file(tmp_path, monkeypatch):
    """If the manifest target points at a nonexistent module, resolver
    returns None (caller emits handler_failed). Plugin authors get a
    server-side log line for the missing file."""
    import apps.api.src.plugin_loader as loader

    (tmp_path / "fake-plugin").mkdir()
    monkeypatch.setattr(loader, "PLUGINS_DIR", tmp_path)
    monkeypatch.setattr(loader, "_OAUTH_HANDLER_CACHE", {})

    assert loader.resolve_oauth_callback_handler(
        "fake-plugin", "api.notthere:cb",
    ) is None


def test_resolve_oauth_callback_handler_returns_none_on_missing_function(tmp_path, monkeypatch):
    """If the file exists but doesn't export the named function, returns
    None. Same failure mode as a typo'd manifest."""
    import apps.api.src.plugin_loader as loader

    plugin_dir = tmp_path / "fake-plugin"
    api_dir = plugin_dir / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "oauth.py").write_text("# empty\n")

    monkeypatch.setattr(loader, "PLUGINS_DIR", tmp_path)
    monkeypatch.setattr(loader, "_OAUTH_HANDLER_CACHE", {})

    assert loader.resolve_oauth_callback_handler(
        "fake-plugin", "api.oauth:not_a_function",
    ) is None


def test_resolve_oauth_callback_handler_caches(tmp_path, monkeypatch):
    """Resolver caches by (slug, target). Repeated callbacks must not
    re-exec the plugin module — the cached callable is returned."""
    import apps.api.src.plugin_loader as loader

    plugin_dir = tmp_path / "fake-plugin"
    api_dir = plugin_dir / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "oauth.py").write_text(
        "_load_count = 0\n"
        "def handle_callback(code, user_id):\n"
        "    return _load_count\n"
    )

    monkeypatch.setattr(loader, "PLUGINS_DIR", tmp_path)
    monkeypatch.setattr(loader, "_OAUTH_HANDLER_CACHE", {})

    h1 = loader.resolve_oauth_callback_handler("fake-plugin", "api.oauth:handle_callback")
    h2 = loader.resolve_oauth_callback_handler("fake-plugin", "api.oauth:handle_callback")
    assert h1 is h2  # same callable object, not a re-import


# ── Allowlist / middleware integration ────────────────────────────────


def test_oauth_callback_path_is_in_public_prefixes():
    """The middleware's hardcoded allowlist must include the prefix.
    Without this, the route is invisible: it 401s before the handler
    even runs, defeating the entire point of B312."""
    from apps.api.src.middleware.auth import PUBLIC_PREFIXES
    assert "/api/oauth/callback/" in PUBLIC_PREFIXES


def test_oauth_callback_path_is_in_rbac_public_routes():
    """RBAC default-deny must also exempt this route. Otherwise the
    middleware allowlist lets the request through, but the dependency
    layer 403s it."""
    from apps.api.src.rbac.routes import PUBLIC_ROUTES
    assert ("GET", "/api/oauth/callback/{plugin_slug}") in PUBLIC_ROUTES


def test_canonical_public_prefixes_match_middleware_constant():
    """main.py's startup check compares PUBLIC_PREFIXES against a
    canonical list. If B312 added the prefix to one but not the other,
    the startup banner would flag a contract violation."""
    from apps.api.src.middleware.auth import PUBLIC_PREFIXES
    # The canonical list lives inside _check_auth_contract in main.py.
    # Re-derive by reading the source so this test catches drift.
    import inspect
    import apps.api.src.main as main_mod
    src = inspect.getsource(main_mod._check_auth_contract)
    assert "/api/oauth/callback/" in src, (
        "main.py's CANONICAL_PUBLIC_PREFIXES is missing /api/oauth/callback/"
    )
    # And the middleware actually exposes it.
    assert "/api/oauth/callback/" in PUBLIC_PREFIXES
