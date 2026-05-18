"""B236 (v0.9.10.0): unit tests for the new RBAC pieces.

Step-up auth, impersonation, role-rank — the parts that DON'T require a
live DB go here. The full-flow integration tests (login → step-up →
RBAC write → impersonate → exit) are in the test plan
(todo/0.9.10/testing/B236-test-plan.md) and run against production by
the operator.
"""
from __future__ import annotations

import sys
from pathlib import Path

# tests/ is at repo root; add apps/api/ so `from src.* import ...` works
# from the same import path the running app uses.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "apps" / "api"))


# ── BUILTIN_ROLE_RANK ────────────────────────────────────────────────

def test_builtin_role_rank_strict_ordering():
    """superadmin > admin > analyst > viewer; ranks are positive integers."""
    from src.rbac.permissions import BUILTIN_ROLE_RANK

    assert BUILTIN_ROLE_RANK["superadmin"] > BUILTIN_ROLE_RANK["admin"]
    assert BUILTIN_ROLE_RANK["admin"] > BUILTIN_ROLE_RANK["analyst"]
    assert BUILTIN_ROLE_RANK["analyst"] > BUILTIN_ROLE_RANK["viewer"]
    assert BUILTIN_ROLE_RANK["viewer"] >= 1


def test_role_rank_unknown_role_returns_zero_no_db():
    """Unknown roles return 0 even when the DB lookup raises (DB unavailable
    in unit tests). The bare except in role_rank() is the relevant path."""
    from src.rbac.permissions import role_rank

    # Empty / None / unknown — first branch in role_rank, no DB hit.
    assert role_rank("") == 0
    assert role_rank(None) == 0  # type: ignore[arg-type]
    # 'custom-something' triggers a DB lookup which fails in test env;
    # the except returns 0.
    assert role_rank("nonexistent-custom-role") == 0


def test_role_rank_returns_builtin_for_known_roles():
    from src.rbac.permissions import role_rank, BUILTIN_ROLE_RANK

    for role, expected in BUILTIN_ROLE_RANK.items():
        assert role_rank(role) == expected


# ── Impersonation rank logic ────────────────────────────────────────

def test_impersonation_strict_greater_actor_must_outrank_target():
    """The rule is `actor > target` (strict). Equal ranks fail."""
    from src.rbac.permissions import role_rank

    # Built-in: superadmin can impersonate admin, but admin can't impersonate admin.
    assert role_rank("superadmin") > role_rank("admin")
    assert not (role_rank("admin") > role_rank("admin"))
    # Admin can impersonate analyst.
    assert role_rank("admin") > role_rank("analyst")
    # Viewer can impersonate nobody (rank 1; no built-in lower than 1).
    assert role_rank("viewer") > role_rank("")  # technically yes against unknown


# ── Sensitive permissions (B236 phase 4) ────────────────────────────

def test_sensitive_permissions_includes_rbac_edit():
    """rbac.edit must be in SENSITIVE_PERMISSIONS or revoke-block fails open."""
    from src.rbac import SENSITIVE_PERMISSIONS

    assert "rbac.edit" in SENSITIVE_PERMISSIONS
    # System-admin tier perms also sensitive
    assert "system.admin" in SENSITIVE_PERMISSIONS
    assert "users.manage_admins" in SENSITIVE_PERMISSIONS
    assert "admin.cli" in SENSITIVE_PERMISSIONS


def test_sensitive_permissions_does_not_include_user_self_read():
    """users.read_self is granted to every authenticated user — not sensitive."""
    from src.rbac import SENSITIVE_PERMISSIONS

    assert "users.read_self" not in SENSITIVE_PERMISSIONS
    assert "dashboards.read" not in SENSITIVE_PERMISSIONS


# ── requires_step_up dependency wiring (no DB) ──────────────────────

def test_requires_step_up_callable_from_rbac_package():
    """The dep should be importable both from .dependency and from the
    package root — same surface as `requires` itself."""
    from src.rbac import requires_step_up
    from src.rbac.dependency import requires_step_up as same_dep

    assert requires_step_up is same_dep


# ── log_decision accepts acting_as_user_id ──────────────────────────

def test_log_decision_signature_accepts_acting_as_user_id():
    """B236 added the optional acting_as_user_id kwarg. Verify it's in
    the signature so callers (rbac/dependency.py) don't TypeError."""
    import inspect
    from src.rbac.audit import log_decision

    sig = inspect.signature(log_decision)
    assert "acting_as_user_id" in sig.parameters
    p = sig.parameters["acting_as_user_id"]
    assert p.default is None  # optional with None default
