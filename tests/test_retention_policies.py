"""Tests for B279 (v0.9.11.17) — retention policies.

Covers:
  - POLICIES registry — every entry has safe identifiers
  - Identifier safety net rejects malformed entries
  - WHERE composition (days > 0, days = 0, additional_where empty/non-empty)
  - retention_days = 0 with empty additional_where is refused
  - Paused policies are skipped by run_all_unpaused
  - Per-policy failure is contained (one bad policy doesn't abort the run)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Registry sanity ─────────────────────────────────────────────────


def test_policies_have_safe_identifiers():
    """Every POLICIES entry's table + field must match the safe-ident
    regex. Catches accidental edits that introduce SQL-quotable input."""
    from apps.api.src.services.retention import POLICIES, _SAFE_IDENT
    for p in POLICIES:
        assert _SAFE_IDENT.match(p.table), f"unsafe table in {p.key!r}: {p.table!r}"
        assert _SAFE_IDENT.match(p.field), f"unsafe field in {p.key!r}: {p.field!r}"


def test_policies_by_key_is_complete():
    """POLICIES_BY_KEY indexes every POLICY entry exactly once."""
    from apps.api.src.services.retention import POLICIES, POLICIES_BY_KEY
    assert len(POLICIES_BY_KEY) == len(POLICIES)
    for p in POLICIES:
        assert POLICIES_BY_KEY[p.key] is p


def test_validate_identifiers_rejects_garbage():
    from apps.api.src.services.retention import RetentionPolicy, _validate_identifiers
    bad = RetentionPolicy(
        key="evil",
        table="app_logs; DROP TABLE users",
        field="created_at",
        additional_where="",
        default_days=30,
        description="evil",
    )
    try:
        _validate_identifiers(bad)
    except ValueError:
        return
    raise AssertionError("expected ValueError for SQL-injectable table name")


# ── WHERE composition ──────────────────────────────────────────────


def test_build_where_days_gt_zero_no_additional():
    from apps.api.src.services.retention import POLICIES_BY_KEY, _build_where
    policy = POLICIES_BY_KEY["app_logs"]  # additional_where = ""
    sql, params = _build_where(policy, days=30)
    # Composed object holds the SQL fragments; verify params shape only —
    # SQL content is exercised end-to-end by the integration walkthrough.
    assert params == [30]
    assert sql is not None


def test_build_where_days_with_additional_where():
    from apps.api.src.services.retention import POLICIES_BY_KEY, _build_where
    policy = POLICIES_BY_KEY["job_runs:success"]
    sql, params = _build_where(policy, days=7)
    assert params == [7]
    assert sql is not None


def test_build_where_days_zero_with_additional_where():
    """retention_days=0 with additional_where='expires_at < now()' must
    produce a valid WHERE without a 'now() - interval 0 days' clause."""
    from apps.api.src.services.retention import POLICIES_BY_KEY, _build_where
    policy = POLICIES_BY_KEY["user_sessions:expired"]
    sql, params = _build_where(policy, days=0)
    assert params == []  # no days param when days=0
    assert sql is not None


def test_build_where_zero_days_no_predicate_refuses():
    """A policy with retention_days=0 and additional_where='' would
    match every row — must refuse rather than build a 'WHERE TRUE' DELETE."""
    from apps.api.src.services.retention import RetentionPolicy, _build_where
    p = RetentionPolicy(
        key="dangerous",
        table="app_logs",
        field="created_at",
        additional_where="",
        default_days=0,
        description="would delete everything",
    )
    raised = False
    try:
        _build_where(p, days=0)
    except ValueError:
        raised = True
    assert raised, "build_where must refuse a policy that would match every row"


# ── execute_policy / run_all_unpaused — DB mocked ───────────────────


class _Cur:
    """Minimal DB-API cursor for the policy executor.

    Tracks `executed` SQL strings. The test inspects them to assert
    that DELETE/SELECT statements composed without surprises.
    """
    def __init__(self):
        self.executed: list[tuple[Any, Any]] = []
        self.fetchone_q: list[Any] = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        # If this is a DELETE, advance the rowcount counter.
        sql_str = str(sql)
        if "DELETE FROM" in sql_str:
            # Pop a configured count if available, else 0.
            if self.fetchone_q:
                v = self.fetchone_q.pop(0)
                self.rowcount = v if isinstance(v, int) else 0
            else:
                self.rowcount = 0

    def fetchone(self):
        if self.fetchone_q:
            return self.fetchone_q.pop(0)
        return None


class _Conn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def test_execute_policy_unknown_key_raises():
    from apps.api.src.services import retention as r
    raised = False
    try:
        r.execute_policy("not-a-real-policy")
    except KeyError:
        raised = True
    assert raised


def test_execute_policy_paused_without_force_raises(monkeypatch):
    """A paused policy with force_run=False raises RuntimeError."""
    from apps.api.src.services import retention as r

    cur = _Cur()
    # First call: SELECT retention_days, paused — return (30, True) = paused.
    cur.fetchone_q = [(30, True)]
    monkeypatch.setattr(r, "get_pg_conn", lambda: _Conn(cur))

    raised = False
    try:
        r.execute_policy("app_logs", force_run=False)
    except RuntimeError:
        raised = True
    assert raised, "paused policy must refuse without force_run"
    # SELECT should have run; nothing else (no DELETE).
    delete_seen = any("DELETE FROM" in str(s[0]) for s in cur.executed)
    assert not delete_seen, "no DELETE should run when policy is paused"


def test_execute_policy_force_run_bypasses_paused(monkeypatch):
    """force_run=True allows a DELETE even when paused."""
    from apps.api.src.services import retention as r

    # First fetch: (30, True) paused. Subsequent DELETE batch returns 5 rows.
    # We model the DELETE rowcount via fetchone_q popping a sentinel int.
    # The execute method consumes from fetchone_q on DELETE (see _Cur).
    cur = _Cur()
    cur.fetchone_q = [(30, True), 5, 0]  # SELECT row, then DELETE rowcounts
    monkeypatch.setattr(r, "get_pg_conn", lambda: _Conn(cur))

    n = r.execute_policy("app_logs", force_run=True)
    assert n == 5
    delete_seen = any("DELETE FROM" in str(s[0]) for s in cur.executed)
    assert delete_seen


def test_run_all_unpaused_isolates_per_policy_failures(monkeypatch):
    """One policy raising shouldn't break the rest."""
    from apps.api.src.services import retention as r

    call_log: list[str] = []

    def fake_execute(key, force_run=False):
        from apps.api.src.services.retention import PolicyPausedError
        call_log.append(key)
        if key == "auth_audit":
            raise RuntimeError("simulated failure")
        if key == "health_log":
            raise PolicyPausedError("Policy 'health_log' is paused")
        return 42

    def fake_record(key, n, error=None):
        pass

    monkeypatch.setattr(r, "execute_policy", fake_execute)
    monkeypatch.setattr(r, "_record_last_run", fake_record)

    summary = r.run_all_unpaused()

    # Every policy attempted at least once.
    for p in r.POLICIES:
        assert p.key in summary
    # auth_audit reports an error string, others int or "paused".
    assert summary["auth_audit"].startswith("error:")
    assert summary["health_log"] == "paused"
    # At least one policy ran successfully.
    assert any(isinstance(v, int) and v == 42 for v in summary.values())


# ── Set / get helpers ──────────────────────────────────────────────


def test_set_policy_state_unknown_key_raises():
    from apps.api.src.services import retention as r
    raised = False
    try:
        r.set_policy_state("not-a-real-policy", paused=False)
    except KeyError:
        raised = True
    assert raised


def test_set_policy_state_validates_retention_days_bounds():
    from apps.api.src.services import retention as r
    raised_low = False
    try:
        r.set_policy_state("app_logs", retention_days=-1)
    except ValueError:
        raised_low = True
    assert raised_low

    raised_high = False
    try:
        r.set_policy_state("app_logs", retention_days=4000)
    except ValueError:
        raised_high = True
    assert raised_high
