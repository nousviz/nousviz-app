"""Tests for B281 (v0.9.11.21) — auto-cleanup of orphan references on
plugin uninstall.

Covers:
  - Empty references list → no-op outcome
  - Annotation kind → DELETE; outcome lists it
  - Share kind → DELETE; outcome lists it
  - Fusion kind → UPDATE requires JSONB; outcome lists it
  - Alert kind → left alone; outcome lists it
  - Per-kind failure isolation: one bad item → captured in failed,
    others still cleaned
  - Connection-level failure → outcome.failed contains the connection error
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Fake DB ─────────────────────────────────────────────────────────


class _Cursor:
    """Records every executed statement; rowcount is configurable per
    statement via a callback the tests inject."""

    def __init__(self, rowcount_for=None, raise_on=None):
        self._rowcount_for = rowcount_for or (lambda sql, params: 1)
        self._raise_on = raise_on or (lambda sql, params: None)
        self.executed: list[tuple] = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((str(sql), params))
        err = self._raise_on(sql, params)
        if err is not None:
            raise err
        self.rowcount = self._rowcount_for(sql, params)


class _Conn:
    def __init__(self, *, rowcount_for=None, raise_on=None):
        self._cursor = _Cursor(rowcount_for=rowcount_for, raise_on=raise_on)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _patch_pg_conn(monkeypatch, conn_factory):
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module
    monkeypatch.setattr(db_module, "get_pg_conn", conn_factory)
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: getattr(_patch_pg_conn, "_refs", []))


# ── Tests ───────────────────────────────────────────────────────────


def test_no_references_returns_empty_outcome(monkeypatch):
    from apps.api.src.routes import plugins as plugins_module

    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: [])
    out = plugins_module._cleanup_plugin_references("ghost")
    assert out["annotations_deleted"] == []
    assert out["shares_deleted"] == []
    assert out["fusions_repointed"] == []
    assert out["alerts_left_alone"] == []
    assert out["failed"] == []


def test_annotation_kind_deletes_and_records(monkeypatch):
    from apps.api.src.routes import plugins as plugins_module

    refs = [
        {"kind": "annotation", "id": "abc-123", "display_name": "Sold CasinoBonusesNow"},
    ]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)

    conn = _Conn(rowcount_for=lambda sql, params: 1)
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)
    # also patch the db module path that the inner import uses
    from apps.api.src import db as db_module
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: conn)

    out = plugins_module._cleanup_plugin_references("X")
    assert len(out["annotations_deleted"]) == 1
    assert out["annotations_deleted"][0]["id"] == "abc-123"
    assert out["annotations_deleted"][0]["title"] == "Sold CasinoBonusesNow"
    assert out["failed"] == []
    # Verify SQL targeted annotations.
    sqls = [s.lower() for (s, _) in conn._cursor.executed]
    assert any("delete from annotations" in s for s in sqls)


def test_share_kind_deletes_and_records(monkeypatch):
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [{"kind": "share", "id": "share-1", "display_name": "shared link"}]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)
    conn = _Conn(rowcount_for=lambda sql, params: 1)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: conn)

    out = plugins_module._cleanup_plugin_references("X")
    assert len(out["shares_deleted"]) == 1
    sqls = [s.lower() for (s, _) in conn._cursor.executed]
    assert any("delete from shared_links" in s for s in sqls)


def test_fusion_kind_strips_plugin_from_requires(monkeypatch):
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [{"kind": "fusion", "id": "fus-1", "display_name": "Q4 dashboard"}]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)
    conn = _Conn(rowcount_for=lambda sql, params: 1)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: conn)

    out = plugins_module._cleanup_plugin_references("X")
    assert len(out["fusions_repointed"]) == 1
    assert out["fusions_repointed"][0]["id"] == "fus-1"
    sqls = [s.lower() for (s, _) in conn._cursor.executed]
    # Update, not delete — the fusion is preserved.
    assert any("update fusions" in s for s in sqls)
    assert not any("delete from fusions" in s for s in sqls)


def test_alert_kind_left_alone(monkeypatch):
    """Phase 1: alert rules pinned to the plugin are listed in
    `alerts_left_alone` but not deleted. Operator handles them via
    the alerts UI."""
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [{"kind": "alert", "id": "alert-9", "display_name": "Disk alert"}]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)
    conn = _Conn(rowcount_for=lambda sql, params: 0)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: conn)

    out = plugins_module._cleanup_plugin_references("X")
    assert len(out["alerts_left_alone"]) == 1
    assert out["annotations_deleted"] == []
    # No DELETE/UPDATE issued for alerts.
    sqls = [s.lower() for (s, _) in conn._cursor.executed]
    assert not any("delete from alert" in s for s in sqls)


def test_unknown_kind_lands_in_failed(monkeypatch):
    """A reference kind we don't know how to clean is captured in
    `failed` rather than silently dropped."""
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [{"kind": "mystery", "id": "x", "display_name": "?"}]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: _Conn())

    out = plugins_module._cleanup_plugin_references("X")
    assert len(out["failed"]) == 1
    assert "unknown reference kind" in out["failed"][0]["error"]


def test_per_item_failure_isolation(monkeypatch):
    """One failing DELETE doesn't prevent the other items from being
    cleaned. The failed one lands in `failed`."""
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [
        {"kind": "annotation", "id": "a-good", "display_name": "ok"},
        {"kind": "annotation", "id": "a-bad", "display_name": "fails"},
        {"kind": "annotation", "id": "a-also-good", "display_name": "ok2"},
    ]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)

    def raise_on(sql, params):
        if params and "a-bad" in (params if isinstance(params, tuple) else []):
            return RuntimeError("simulated DB error")
        return None

    conn = _Conn(rowcount_for=lambda sql, params: 1, raise_on=raise_on)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: conn)

    out = plugins_module._cleanup_plugin_references("X")
    deleted_ids = {a["id"] for a in out["annotations_deleted"]}
    assert deleted_ids == {"a-good", "a-also-good"}
    assert len(out["failed"]) == 1
    assert out["failed"][0]["id"] == "a-bad"
    assert "RuntimeError" in out["failed"][0]["error"]


def test_connection_failure_outer_recorded(monkeypatch):
    """Outer connection error returns the partial outcome with a
    `*` entry in `failed` rather than raising."""
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    refs = [{"kind": "annotation", "id": "x", "display_name": "x"}]
    monkeypatch.setattr(plugins_module, "_find_references", lambda pid: refs)

    def boom():
        raise RuntimeError("connection lost")

    monkeypatch.setattr(db_module, "get_pg_conn", boom)

    out = plugins_module._cleanup_plugin_references("X")
    # No items cleaned because connection failed before iteration.
    assert out["annotations_deleted"] == []
    assert any(f.get("kind") == "*" for f in out["failed"])


def test_helper_does_not_trust_caller_supplied_refs(monkeypatch):
    """The helper RE-fetches references via _find_references and ignores
    any caller-supplied list, so an operator can't craft a request to
    delete arbitrary IDs by spoofing the references list."""
    from apps.api.src.routes import plugins as plugins_module
    from apps.api.src import db as db_module

    seen_pid = []

    def fake_find_references(pid):
        seen_pid.append(pid)
        return []

    monkeypatch.setattr(plugins_module, "_find_references", fake_find_references)
    monkeypatch.setattr(db_module, "get_pg_conn", lambda: _Conn())

    plugins_module._cleanup_plugin_references("trusted-slug")
    assert seen_pid == ["trusted-slug"]
