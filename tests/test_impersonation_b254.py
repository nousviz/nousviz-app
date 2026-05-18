"""B254 (v0.9.10.0.5): tests for the session-flag impersonation refactor.

These are unit tests that don't require a running database — they
exercise the rank logic, env-var configurability, and the auto-expire
SQL shape. Full integration walkthrough (impersonate → page reload →
exit → page reload, all without re-login) is in the test plan
(todo/0.9.10/testing/B254-test-plan.md), run by the operator against
production.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "apps" / "api"))


# ── Env-var configurability ────────────────────────────────────────────

def test_impersonation_session_minutes_default_is_ten(monkeypatch):
    """IMPERSONATION_SESSION_MINUTES defaults to 10. The constant is
    captured at import time so we have to reload the module to pick up
    a different env value — that's fine for the production deploy
    path (env is set before the module imports), and we can't reload
    here without breaking other tests' module state. Just verify the
    default value when the env var isn't set."""
    monkeypatch.delenv("IMPERSONATION_SESSION_MINUTES", raising=False)
    # Re-import via importlib to pick up the env
    import importlib
    if "src.routes.auth" in sys.modules:
        del sys.modules["src.routes.auth"]
    auth_module = importlib.import_module("src.routes.auth")
    assert auth_module.IMPERSONATION_SESSION_MINUTES == 10


def test_impersonation_session_minutes_env_override(monkeypatch):
    """IMPERSONATION_SESSION_MINUTES env var is read at module import."""
    monkeypatch.setenv("IMPERSONATION_SESSION_MINUTES", "30")
    import importlib
    if "src.routes.auth" in sys.modules:
        del sys.modules["src.routes.auth"]
    auth_module = importlib.import_module("src.routes.auth")
    assert auth_module.IMPERSONATION_SESSION_MINUTES == 30


# ── Auto-expire SQL is parameterized correctly ────────────────────────

def test_clear_expired_impersonation_helper_exists():
    """The helper from middleware/auth.py should be importable and callable
    with a token_hash argument, and never raise."""
    from src.middleware.auth import _clear_expired_impersonation
    # With an arbitrary unknown token_hash, the function should no-op
    # gracefully (no DB row matches; no audit fires; no exception).
    # We can't actually run it here because there's no DB connection in
    # the unit-test env — but we verify the function signature.
    import inspect
    sig = inspect.signature(_clear_expired_impersonation)
    params = list(sig.parameters.keys())
    assert params == ["token_hash"]


# ── Rank check (B236 logic, preserved by B254) ────────────────────────

def test_actor_must_strictly_outrank_target_for_impersonation():
    """B254 doesn't change the rank rule — verify it still holds."""
    from src.rbac.permissions import role_rank
    # superadmin (4) outranks admin (3): allowed
    assert role_rank("superadmin") > role_rank("admin")
    # admin (3) outranks analyst (2): allowed
    assert role_rank("admin") > role_rank("analyst")
    # admin doesn't outrank admin: not allowed (strict greater)
    assert not (role_rank("admin") > role_rank("admin"))
    # superadmin doesn't outrank superadmin: not allowed
    assert not (role_rank("superadmin") > role_rank("superadmin"))


# ── Token continuity (the headline acceptance, structural check) ───────

def test_impersonate_does_not_create_new_session_row():
    """The B254 impersonate endpoint UPDATEs the caller's existing session
    rather than INSERTing a new one. We verify the source-level pattern
    here as a defensive structural test — production walkthrough
    confirms the runtime behavior."""
    auth_path = REPO / "apps" / "api" / "src" / "routes" / "auth.py"
    src = auth_path.read_text()

    # B216 (v0.9.10.3) made decorators multi-line for OpenAPI metadata —
    # find the handler by its def signature instead of by decorator string.
    start = src.find("def impersonate(user_id: str, request: Request):")
    assert start != -1, "impersonate handler not found"
    end = src.find("@router.", start)  # next decorator
    body = src[start:end]

    # The B254 model uses UPDATE user_sessions, not INSERT.
    assert "UPDATE user_sessions" in body, (
        "impersonate endpoint should UPDATE the existing session"
    )
    # And the response should NOT include a 'token' field.
    assert '"token": raw_token' not in body, (
        "impersonate endpoint should not return a new token (B254 model)"
    )
    assert "raw_token = secrets.token_urlsafe" not in body, (
        "impersonate endpoint should not generate a new token"
    )


def test_impersonate_exit_clears_flags_not_session():
    """Exit clears acting_as_user_id and acting_as_until on the existing
    session row; it does NOT mutate expires_at."""
    auth_path = REPO / "apps" / "api" / "src" / "routes" / "auth.py"
    src = auth_path.read_text()

    # B216 (v0.9.10.3) made decorators multi-line — find by handler def.
    start = src.find("def impersonate_exit(request: Request):")
    assert start != -1, "impersonate_exit handler not found"
    end = src.find("def impersonate(user_id: str, request: Request):", start)
    assert end != -1, "impersonate handler not found after impersonate_exit"
    body = src[start:end]

    # Old behavior: UPDATE user_sessions SET expires_at = now() — kills the session
    # New behavior: UPDATE user_sessions SET acting_as_user_id = NULL, acting_as_until = NULL
    assert "acting_as_user_id = NULL" in body, "exit should clear acting_as_user_id"
    assert "acting_as_until = NULL" in body, "exit should clear acting_as_until"
    # And the old kill-session pattern should NOT be in the exit handler.
    # (It's allowed elsewhere — logout, auto-expiry — but not here.)
    assert "expires_at = now()" not in body, (
        "exit should not kill the session — actor stays logged in (B254)"
    )
