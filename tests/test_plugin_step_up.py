"""B348: plugin routes with `step_up: true` and the `reveal_secrets` level.

Covers the automated cases in nousviz-docs 1.0/testing/B348-test-plan.md:

- manifest validation (`step_up`, `reveal_secrets` on POST / GET / default)
- default grants (none, for every role) and the sensitive flag
- runtime enforcement through the real AuthMiddleware and the real
  plugin loader wiring (`_auto_register_plugin_routes`), using the fixture
  plugin in tests/fixtures/plugins/b348-reveal-test
- the real `POST /api/auth/step-up` handler and core's `requires_step_up`
- the `credential_audit_log` `revealed` row (only on 2xx)

No live database: an in-memory fake answers the handful of SQL statements
these code paths run.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.plugin_manifest import (  # noqa: E402
    ALL_LEVELS,
    LEVELS,
    ManifestPermissionsError,
    PermissionRule,
    is_sensitive_plugin_permission,
    parse,
    uses_b348_fields,
)

FIXTURE_DIR = REPO / "tests" / "fixtures" / "plugins" / "b348-reveal-test"
SLUG = "b348-reveal-test"
REVEAL = f"/api/plugins/{SLUG}/secret/reveal"
REVEAL_TEMPLATED = f"/api/plugins/{SLUG}/accounts/acct-42/reveal"
STEP_UP_ONLY = f"/api/plugins/{SLUG}/settings/check"
STATUS = f"/api/plugins/{SLUG}/status"
PASSWORD = "correct horse battery staple"
STEPUP_BODY = {
    "detail": {
        "error": "stepup_required",
        "message": "This action requires re-authentication. Please confirm your password.",
    },
}


# ── Manifest validation ─────────────────────────────────────────────────


def test_rule_with_step_up_true_validates():
    cfg = parse({
        "default": "read",
        "routes": [{"method": "POST", "path": "/api/plugins/foo/x", "level": "write", "step_up": True}],
    })
    assert cfg.route_rules[0].step_up is True
    assert cfg.resolve_rule("POST", "/api/plugins/foo/x").step_up is True


def test_step_up_defaults_to_false_and_rule_shape_is_unchanged():
    cfg = parse({"routes": [{"method": "POST", "level": "write"}]})
    rule = cfg.route_rules[0]
    assert rule.step_up is False
    # Constructing a rule without step_up (as B247 code does) still works
    # and compares equal.
    assert rule == PermissionRule(method="POST", path_glob=None, level="write")


@pytest.mark.parametrize("bad", ["yes", "true", 1, 0, None, [], {}])
def test_step_up_must_be_boolean(bad):
    with pytest.raises(ManifestPermissionsError, match=r"routes\[0\]\.step_up"):
        parse({"routes": [{"method": "POST", "path": "/api/plugins/foo/x", "level": "write", "step_up": bad}]})


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "post"])
def test_reveal_secrets_on_non_get_rule_validates(method):
    cfg = parse({
        "default": "read",
        "routes": [{"method": method, "path": "/api/plugins/foo/a/*/reveal",
                    "level": "reveal_secrets", "step_up": True}],
    })
    assert cfg.route_rules[0].level == "reveal_secrets"


def test_reveal_secrets_on_get_rule_is_rejected_naming_the_rule():
    with pytest.raises(ManifestPermissionsError) as exc:
        parse({
            "default": "read",
            "routes": [
                {"method": "POST", "path": "/api/plugins/foo/ok", "level": "write"},
                {"method": "GET", "path": "/api/plugins/foo/a/*/reveal", "level": "reveal_secrets"},
            ],
        })
    msg = str(exc.value)
    assert "routes[1]" in msg
    assert "GET /api/plugins/foo/a/*/reveal" in msg
    assert "reveal_secrets" in msg and "non-GET" in msg


def test_reveal_secrets_without_method_is_rejected():
    """A rule with no `method` also matches GET, so it's refused too."""
    with pytest.raises(ManifestPermissionsError, match="non-GET"):
        parse({"routes": [{"path": "/api/plugins/foo/reveal", "level": "reveal_secrets"}]})


def test_reveal_secrets_cannot_be_the_default_level():
    with pytest.raises(ManifestPermissionsError, match="permissions.default"):
        parse({"default": "reveal_secrets"})


def test_levels_ladder_unchanged_and_reveal_secrets_is_extra():
    assert LEVELS == ("read", "write", "configure", "admin")
    assert ALL_LEVELS == LEVELS + ("reveal_secrets",)


def test_uses_b348_fields_detection():
    assert not uses_b348_fields(None)
    assert not uses_b348_fields({"default": "read", "routes": [{"method": "POST", "level": "write"}]})
    assert uses_b348_fields({"routes": [{"method": "POST", "level": "write", "step_up": "yes"}]})
    assert uses_b348_fields({"routes": [{"method": "GET", "level": "reveal_secrets"}]})
    assert uses_b348_fields({"default": "reveal_secrets"})


def test_install_validation_rejects_bad_b348_block_and_accepts_fixture():
    from apps.api.src.plugin_validation import (
        ManifestValidationError,
        validate_manifest_extensions,
    )
    meta = yaml.safe_load((FIXTURE_DIR / "plugin.yaml").read_text())
    validate_manifest_extensions(SLUG, meta)  # fixture is valid

    bad = {"permissions": {"routes": [
        {"method": "GET", "path": "/api/plugins/foo/reveal", "level": "reveal_secrets"},
    ]}}
    with pytest.raises(ManifestValidationError, match="non-GET"):
        validate_manifest_extensions("foo", bad)


def test_install_validation_unchanged_for_blocks_without_b348_fields():
    """An invalid block that doesn't use the new fields is left to the
    loader, exactly as before B348 (no new install failure)."""
    from apps.api.src.plugin_validation import validate_manifest_extensions
    validate_manifest_extensions("foo", {"permissions": {"default": "bogus"}})


# ── Catalog: default grants and the sensitive flag ──────────────────────


def test_reveal_secrets_has_no_default_grant_for_any_role():
    from apps.api.src.rbac.permissions import PERMISSIONS, ROLE_PERMISSIONS
    from apps.api.src.rbac.plugin_permissions import register_plugin_permissions

    slug = f"test-{uuid.uuid4().hex[:8]}"
    out = register_plugin_permissions(slug, ["reveal_secrets"])
    perm = f"plugin.{slug}.reveal_secrets"
    assert out == [perm]
    assert perm in PERMISSIONS
    for role in ("viewer", "analyst", "admin", "superadmin"):
        assert perm not in ROLE_PERMISSIONS[role], role


def test_reveal_secrets_is_sensitive():
    from apps.api.src.rbac import SENSITIVE_PERMISSIONS, is_sensitive_permission

    assert is_sensitive_permission("plugin.foo.reveal_secrets")
    assert is_sensitive_plugin_permission("plugin.foo-bar.reveal_secrets")
    for perm in ("plugin.foo.admin", "plugin.foo.read", "plugins.read", "plugin.reveal_secrets"):
        assert not is_sensitive_permission(perm), perm
    # Static set unchanged; existing sensitive permissions still flagged.
    assert "rbac.edit" in SENSITIVE_PERMISSIONS
    assert is_sensitive_permission("rbac.edit")


# ── Runtime: fake database ──────────────────────────────────────────────


class FakeDB:
    """Answers the SQL issued by the step-up, permission and audit paths."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}   # token_hash -> row
        self.users: dict[str, dict] = {}      # user_id -> row
        self.overrides: list[tuple[str, str, str]] = []  # (role, permission, kind)
        self.audit: list[dict] = []
        self.connections: dict[str, str] = {}
        self.fail_audit = False

    def add_session(self, token: str, user_id: str, email: str, role: str, password: str):
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
        self.users[user_id] = {"id": user_id, "email": email, "role": role, "password_hash": pw_hash}
        self.sessions[hashlib.sha256(token.encode()).hexdigest()] = {
            "user_id": user_id, "acting_as_user_id": None, "step_up_until": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        }

    def session(self, token: str) -> dict:
        return self.sessions[hashlib.sha256(token.encode()).hexdigest()]

    @contextlib.contextmanager
    def conn(self):
        yield _FakeConn(self)


class _FakeConn:
    def __init__(self, db):
        self.db = db

    def cursor(self, *a, **kw):
        return _FakeCursor(self.db)

    def commit(self):
        pass

    def rollback(self):
        pass


class _FakeCursor:
    def __init__(self, db: FakeDB):
        self.db = db
        self.rows: list[tuple] = []
        self.description: list[tuple] = []
        self.rowcount = 0

    def _set(self, cols, rows):
        self.description = [(c,) for c in cols]
        self.rows = list(rows)
        self.rowcount = len(self.rows)

    def execute(self, sql, params=()):
        q = " ".join(sql.split())
        db = self.db
        if q.startswith("SELECT step_up_until FROM user_sessions"):
            row = db.sessions.get(params[0])
            self._set(["step_up_until"], [(row["step_up_until"],)] if row else [])
        elif q.startswith("SELECT user_id, acting_as_user_id, step_up_until, expires_at FROM user_sessions"):
            row = db.sessions.get(params[0])
            self._set(["user_id", "acting_as_user_id", "step_up_until", "expires_at"],
                      [(row["user_id"], row["acting_as_user_id"], row["step_up_until"], row["expires_at"])]
                      if row else [])
        elif q.startswith("SELECT user_id::text, acting_as_user_id::text FROM user_sessions"):
            row = db.sessions.get(params[0])
            self._set(["user_id", "acting_as_user_id"],
                      [(row["user_id"], row["acting_as_user_id"])] if row else [])
        elif q.startswith("SELECT password_hash FROM users"):
            u = db.users.get(params[0])
            self._set(["password_hash"], [(u["password_hash"],)] if u else [])
        elif q.startswith("UPDATE user_sessions SET step_up_until"):
            until, token_hash = params
            db.sessions[token_hash]["step_up_until"] = until
            self._set([], [])
        elif q.startswith("SELECT permission, kind FROM rbac_role_overrides"):
            role = params[0]
            self._set(["permission", "kind"],
                      [(p, k) for r, p, k in db.overrides if r == role])
        elif q.startswith("SELECT id FROM connections WHERE name"):
            cid = db.connections.get(params[0])
            self._set(["id"], [(cid,)] if cid else [])
        elif q.startswith("INSERT INTO connections"):
            db.connections[params[1]] = params[0]
            self._set(["id"], [(params[0],)])
        elif q.startswith("INSERT INTO credential_audit_log"):
            if db.fail_audit:
                raise RuntimeError("audit insert failed")
            assert "'revealed'" in q
            connection_id, performed_by, detail = params
            db.audit.append({"credential_id": None, "connection_id": connection_id,
                             "action": "revealed", "performed_by": performed_by, "detail": detail})
            self._set([], [])
        elif q.startswith("UPDATE users SET last_seen_at"):
            self._set([], [])
        else:  # pragma: no cover — surfaces an unexpected query loudly
            raise AssertionError(f"FakeDB: unexpected SQL: {q[:120]}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


# ── Runtime: app built from the fixture plugin ─────────────────────────


def _load_fixture_module():
    name = "b348_fixture_plugin_routes"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, FIXTURE_DIR / "api" / "routes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def plugin_app():
    """FastAPI app with the fixture plugin wired through the real loader
    (`_auto_register_plugin_routes`) and the real auth router."""
    from apps.api.src import plugin_loader
    from apps.api.src.middleware.auth import AuthMiddleware
    import apps.api.src.routes.auth as auth_mod

    mod = _load_fixture_module()
    manifest = yaml.safe_load((FIXTURE_DIR / "plugin.yaml").read_text())

    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.include_router(mod.router, prefix="/api")

    original = plugin_loader._load_plugin_manifests
    plugin_loader._load_plugin_manifests = lambda: {SLUG: manifest}
    try:
        plugin_loader._auto_register_plugin_routes(app)
    finally:
        plugin_loader._load_plugin_manifests = original

    # The step-up endpoint is added after registration so the loader
    # doesn't touch core's auth routes.
    app.include_router(auth_mod.router)
    return app, mod


@pytest.fixture
def env(monkeypatch, plugin_app):
    """Fake DB + identity resolution; returns a helper namespace."""
    import apps.api.src.db as db_mod
    import apps.api.src.credential_usage as cu_mod
    import apps.api.src.plugin_credentials as pc_mod
    import apps.api.src.routes.auth as auth_mod
    import apps.api.src.rbac.overrides as ov_mod
    import apps.api.src.middleware.auth as mw_mod
    from apps.api.src.rbac import invalidate_all_override_caches

    app, mod = plugin_app
    db = FakeDB()
    for m in (db_mod, cu_mod, pc_mod, auth_mod, ov_mod):
        monkeypatch.setattr(m, "get_pg_conn", db.conn)
    monkeypatch.setattr(auth_mod, "_check_login_rate", lambda ip: False)

    def _identity(request):
        if request.headers.get("X-API-Key"):
            return "apikey:test-key"
        token = request.headers.get("X-Session-Token")
        if token:
            row = db.sessions.get(hashlib.sha256(token.encode()).hexdigest())
            if row:
                return f"session:{db.users[row['user_id']]['email']}"
        return None

    def _get_me(request, *a, **kw):
        from fastapi import HTTPException
        token = request.headers.get("X-Session-Token")
        row = db.sessions.get(hashlib.sha256(token.encode()).hexdigest()) if token else None
        if not row:
            raise HTTPException(401, "Not authenticated")
        u = db.users[row["user_id"]]
        return {"id": u["id"], "email": u["email"], "role": u["role"]}

    monkeypatch.setattr(mw_mod, "get_authenticated_identity", _identity)
    monkeypatch.setattr(auth_mod, "get_me", _get_me)
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    invalidate_all_override_caches()
    mod.CALLS.clear()

    class Env:
        pass

    e = Env()
    e.db, e.app, e.calls = db, app, mod.CALLS
    e.client = TestClient(app)
    e.admin_token = "tok-admin-" + uuid.uuid4().hex
    db.add_session(e.admin_token, "u-admin", "admin@example.com", "admin", PASSWORD)

    def grant(role="admin", level="reveal_secrets"):
        db.overrides.append((role, f"plugin.{SLUG}.{level}", "grant"))
        invalidate_all_override_caches()

    def step_up(token=None, password=PASSWORD):
        return e.client.post("/api/auth/step-up", json={"password": password},
                             headers={"X-Session-Token": token or e.admin_token})

    def call(path=REVEAL, token=None, headers=None):
        h = {"X-Session-Token": token or e.admin_token}
        h.update(headers or {})
        return e.client.post(path, headers=h)

    e.grant, e.step_up, e.call = grant, step_up, call
    yield e
    invalidate_all_override_caches()


# ── Runtime: step-up ────────────────────────────────────────────────────


def test_loader_registers_guards_and_permission(env):
    from apps.api.src.rbac import PERMISSIONS, ROLE_PERMISSIONS, match_plugin_route_guard

    g = match_plugin_route_guard("POST", REVEAL)
    assert g and g.step_up and g.audit_reveal and g.permission == f"plugin.{SLUG}.reveal_secrets"
    g2 = match_plugin_route_guard("POST", REVEAL_TEMPLATED)
    assert g2 and g2.path == f"/api/plugins/{SLUG}/accounts/{{account_id}}/reveal"
    g3 = match_plugin_route_guard("POST", STEP_UP_ONLY)
    assert g3 and g3.step_up and not g3.audit_reveal
    assert match_plugin_route_guard("GET", STATUS) is None
    assert match_plugin_route_guard("GET", REVEAL) is None

    perm = f"plugin.{SLUG}.reveal_secrets"
    assert perm in PERMISSIONS
    for role in ("viewer", "analyst", "admin", "superadmin"):
        assert perm not in ROLE_PERMISSIONS[role], role


def test_step_up_route_without_recent_step_up_returns_core_401(env):
    env.grant()
    r = env.call()
    assert r.status_code == 401
    assert r.json() == STEPUP_BODY
    assert env.calls == []


def test_step_up_route_passes_within_ttl_after_post_step_up(env):
    env.grant()
    assert env.call().status_code == 401
    r = env.step_up()
    assert r.status_code == 200, r.text
    r = env.call()
    assert r.status_code == 200, r.text
    assert r.json() == {"value": "b348-fixed-secret"}
    assert env.calls == ["secret/reveal"]
    # Within the window: no new prompt.
    assert env.call().status_code == 200


def test_step_up_route_401_again_six_minutes_after_step_up(env):
    env.grant()
    assert env.step_up().status_code == 200
    # Six minutes later: move the stored deadline back by six minutes.
    s = env.db.session(env.admin_token)
    s["step_up_until"] = s["step_up_until"] - timedelta(minutes=6)
    r = env.call()
    assert r.status_code == 401
    assert r.json() == STEPUP_BODY


def test_wrong_password_does_not_open_the_route(env):
    env.grant()
    assert env.step_up(password="wrong").status_code == 401
    assert env.call().status_code == 401
    assert env.calls == []


def test_api_key_is_refused_on_step_up_route(env):
    env.grant()
    r = env.client.post(REVEAL, headers={"X-API-Key": "nv_live_whatever"})
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "session_required"
    # Even alongside a stepped-up session token, the API key identity wins
    # and is refused.
    env.step_up()
    r = env.call(headers={"X-API-Key": "nv_live_whatever"})
    assert r.status_code == 403
    assert env.calls == []
    assert env.db.audit == []


def test_unauthenticated_call_is_refused(env):
    r = env.client.post(REVEAL)
    assert r.status_code == 401
    assert env.calls == []


def test_guard_enforced_even_when_auth_required_is_off(env, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    assert env.client.post(REVEAL).status_code == 401
    assert env.call().status_code == 403  # no grant
    env.grant()
    assert env.call().status_code == 401  # no step-up
    assert env.calls == []


def test_step_up_on_ordinary_level_needs_permission_and_step_up_no_audit(env):
    # configure → admin by default; admin still has to step up.
    r = env.call(STEP_UP_ONLY)
    assert r.status_code == 401 and r.json() == STEPUP_BODY
    env.step_up()
    assert env.call(STEP_UP_ONLY).status_code == 200
    assert env.db.audit == []  # not a reveal_secrets route


# ── Runtime: reveal_secrets permission and audit ────────────────────────


def test_admin_without_grant_gets_403_and_handler_not_called(env):
    env.step_up()
    r = env.call()
    assert r.status_code == 403
    assert f"plugin.{SLUG}.reveal_secrets" in r.json()["detail"]
    assert env.calls == []
    assert env.db.audit == []


def test_superadmin_without_grant_gets_403(env):
    tok = "tok-super-" + uuid.uuid4().hex
    env.db.add_session(tok, "u-super", "super@example.com", "superadmin", PASSWORD)
    env.step_up(token=tok)
    assert env.call(token=tok).status_code == 403


def test_permission_checked_before_step_up(env):
    """No grant and no step-up: the answer is 403, not a password prompt."""
    assert env.call().status_code == 403


def test_admin_with_grant_and_step_up_gets_200_and_one_audit_row(env):
    env.grant()
    env.step_up()
    r = env.call()
    assert r.status_code == 200
    assert len(env.db.audit) == 1
    row = env.db.audit[0]
    assert row["action"] == "revealed"
    assert row["credential_id"] is None
    assert row["performed_by"] == "admin@example.com"
    assert f"plugin={SLUG}" in row["detail"]
    assert f"route=POST {REVEAL}" in row["detail"]
    assert "user_id=u-admin" in row["detail"]
    assert row["connection_id"] == env.db.connections[f"plugin:{SLUG}"]
    # A second successful call adds a second row.
    assert env.call().status_code == 200
    assert len(env.db.audit) == 2


def test_templated_reveal_route_is_guarded_and_audited(env):
    assert env.call(REVEAL_TEMPLATED).status_code == 403  # no grant
    env.grant()
    assert env.call(REVEAL_TEMPLATED).status_code == 401  # no step-up
    assert env.calls == []
    env.step_up()
    r = env.call(REVEAL_TEMPLATED)
    assert r.status_code == 200
    assert r.json()["account_id"] == "acct-42"
    assert len(env.db.audit) == 1
    assert f"route=POST /api/plugins/{SLUG}/accounts/{{account_id}}/reveal" in env.db.audit[0]["detail"]
    assert f"path={REVEAL_TEMPLATED}" in env.db.audit[0]["detail"]


def test_failed_calls_write_no_revealed_row(env):
    env.call()                      # 403
    env.grant()
    env.call()                      # 401
    env.client.post(REVEAL, headers={"X-API-Key": "k"})  # 403 session_required
    assert env.db.audit == []


def test_non_2xx_from_plugin_writes_no_row(env):
    """A plugin error response is not a reveal: no audit row."""
    env.grant()
    env.step_up()
    r = env.call(f"/api/plugins/{SLUG}/accounts/missing/reveal")
    assert r.status_code == 404
    assert env.calls == ["accounts/missing/reveal"]
    assert env.db.audit == []


def test_response_withheld_when_audit_write_fails(env):
    env.grant()
    env.step_up()
    env.db.fail_audit = True
    r = env.call()
    assert r.status_code == 500
    assert "b348-fixed-secret" not in r.text


def test_revoking_the_grant_refuses_again(env):
    env.grant()
    env.step_up()
    assert env.call().status_code == 200
    env.db.overrides.clear()
    from apps.api.src.rbac import invalidate_all_override_caches
    invalidate_all_override_caches()
    assert env.call().status_code == 403


# ── Unchanged behaviour ─────────────────────────────────────────────────


def test_get_route_of_same_plugin_is_unaffected(env):
    """The plugin's `default: read` GET route: no step-up, no audit."""
    viewer = "tok-viewer-" + uuid.uuid4().hex
    env.db.add_session(viewer, "u-viewer", "viewer@example.com", "viewer", PASSWORD)
    r = env.client.get(STATUS, headers={"X-Session-Token": viewer})
    assert r.status_code == 200
    assert env.db.audit == []


def test_plugin_without_new_fields_registers_no_guards():
    """A B247 plugin (no step_up / reveal_secrets) and a plugin with no
    `permissions:` block get exactly the B247 / B229 registrations and no
    guards."""
    from fastapi import APIRouter
    from apps.api.src import plugin_loader
    from apps.api.src.rbac import ROUTE_PERMISSIONS, match_plugin_route_guard

    b247 = f"test-{uuid.uuid4().hex[:8]}"
    legacy = f"test-{uuid.uuid4().hex[:8]}"
    app = FastAPI()
    for slug in (b247, legacy):
        # Routes added directly so `app.routes` is flat on every FastAPI
        # version (the B247 loop doesn't descend into included routers).
        app.add_api_route(f"/api/plugins/{slug}/data", lambda: {}, methods=["GET"])
        app.add_api_route(f"/api/plugins/{slug}/save", lambda: {}, methods=["POST"])
        # And via a router, as real plugins do (B348's guard pass descends).
        r = APIRouter(prefix=f"/plugins/{slug}")
        r.add_api_route("/more", lambda: {}, methods=["POST"])
        app.include_router(r, prefix="/api")

    manifests = {
        b247: {"permissions": {"default": "read", "routes": [{"method": "POST", "level": "write"}]}},
        legacy: {},
    }
    original = plugin_loader._load_plugin_manifests
    plugin_loader._load_plugin_manifests = lambda: manifests
    try:
        plugin_loader._auto_register_plugin_routes(app)
    finally:
        plugin_loader._load_plugin_manifests = original

    assert ROUTE_PERMISSIONS[("GET", f"/api/plugins/{b247}/data")] == f"plugin.{b247}.read"
    assert ROUTE_PERMISSIONS[("POST", f"/api/plugins/{b247}/save")] == f"plugin.{b247}.write"
    assert ROUTE_PERMISSIONS[("GET", f"/api/plugins/{legacy}/data")] == "plugins.read"
    assert ROUTE_PERMISSIONS[("POST", f"/api/plugins/{legacy}/save")] == "plugins.configure"
    for slug in (b247, legacy):
        for m, p in (("GET", "data"), ("POST", "save"), ("POST", "more")):
            assert match_plugin_route_guard(m, f"/api/plugins/{slug}/{p}") is None
    from apps.api.src.rbac import PERMISSIONS
    assert f"plugin.{b247}.reveal_secrets" not in PERMISSIONS


def test_invalid_b348_block_fails_closed_at_runtime():
    """A broken block that asks for step-up / reveal_secrets must not fall
    back to legacy defaults (which have neither): its routes answer 503."""
    from fastapi import APIRouter
    from apps.api.src import plugin_loader
    from apps.api.src.middleware.auth import AuthMiddleware
    from apps.api.src.rbac import match_plugin_route_guard

    slug = f"test-{uuid.uuid4().hex[:8]}"
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    calls = []
    r = APIRouter(prefix=f"/plugins/{slug}")
    r.add_api_route("/reveal", lambda: calls.append(1) or {"v": "x"}, methods=["GET"])
    app.include_router(r, prefix="/api")
    manifests = {slug: {"permissions": {"routes": [
        {"method": "GET", "path": f"/api/plugins/{slug}/reveal", "level": "reveal_secrets"},
    ]}}}
    original = plugin_loader._load_plugin_manifests
    plugin_loader._load_plugin_manifests = lambda: manifests
    try:
        plugin_loader._auto_register_plugin_routes(app)
    finally:
        plugin_loader._load_plugin_manifests = original

    assert match_plugin_route_guard("GET", f"/api/plugins/{slug}/reveal").blocked
    resp = TestClient(app).get(f"/api/plugins/{slug}/reveal")
    assert resp.status_code == 503
    assert calls == []


def test_manifest_default_grants_cannot_grant_reveal_secrets(env):
    """Nothing in a manifest grants the level: extra keys such as a
    `default_grants:` map are ignored by the parser."""
    cfg = parse({
        "default": "read",
        "default_grants": {"reveal_secrets": ["admin", "superadmin"]},
        "routes": [{"method": "POST", "path": "/api/plugins/x/r", "level": "reveal_secrets"}],
    })
    assert cfg is not None
    from apps.api.src.rbac.permissions import ROLE_PERMISSIONS
    perm = f"plugin.{SLUG}.reveal_secrets"
    for role in ROLE_PERMISSIONS:
        assert perm not in ROLE_PERMISSIONS[role]
    env.step_up()
    assert env.call().status_code == 403
