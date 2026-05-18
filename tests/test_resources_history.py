"""Tests for B273 (v0.9.11.19) — system-resources history pipeline.

Covers:
  - compact_snapshot truncates to top-N per section, preserves findings
  - get_metric_history validates whitelist + plugin requirement
  - get_finding_history validates input
  - days param is clamped to MAX_HISTORY_DAYS
  - DB writes/reads mocked through the same _FakeConn pattern used by
    the retention + dashboard tests
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Fake DB ─────────────────────────────────────────────────────────


class _FakeCursor:
    def __init__(self, results: list[list[tuple]]):
        self._results = list(results)
        self._current: list[tuple] = []
        self.rowcount = 0
        self.executed: list[tuple] = []

    def execute(self, sql, params=None):
        self.executed.append((str(sql), params))
        if self._results:
            self._current = self._results.pop(0)
            # Simulate DELETE rowcount via the first tuple's first element
            if isinstance(self._current, int):
                self.rowcount = self._current
                self._current = []
            elif self._current and isinstance(self._current[0], tuple) and len(self._current[0]) == 1:
                # Single-value result, fine for fetchall
                pass
        else:
            self._current = []

    def fetchall(self):
        return list(self._current)

    def fetchone(self):
        return self._current[0] if self._current else None


class _FakeConn:
    def __init__(self, results: list[list[tuple]]):
        self._cursor = _FakeCursor(results)

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _fake_pg(results):
    def _factory():
        return _FakeConn(results)
    return _factory


# ── compact_snapshot ────────────────────────────────────────────────


def test_compact_snapshot_truncates_to_top_n():
    from apps.api.src.services.resources_history import compact_snapshot

    snap = {
        "server": {"foo": 1},
        "postgres": {"db_size_mb": 100},
        "plugins": [{"id": f"p{i}", "total_size_mb": float(i)} for i in range(50)],
        "syncs": [{"plugin_id": f"p{i}"} for i in range(50)],
    }
    findings = [{"id": "rule_a", "severity": "warn"}]
    out = compact_snapshot(snap, findings, max_per_section=20)
    assert len(out["plugins"]) == 20
    assert len(out["syncs"]) == 20
    assert out["server"] == {"foo": 1}
    assert out["postgres"] == {"db_size_mb": 100}
    assert out["findings"] == [{"id": "rule_a", "severity": "warn"}]


def test_compact_snapshot_preserves_first_n_in_order():
    """Top-N slice must keep the input order — postgres_resources
    returns plugins/syncs already sorted by size/load DESC, so [:N]
    is the correct 'top'."""
    from apps.api.src.services.resources_history import compact_snapshot

    snap = {
        "server": {},
        "postgres": {},
        "plugins": [{"id": f"p{i}", "total_size_mb": float(50 - i)} for i in range(50)],
        "syncs": [],
    }
    out = compact_snapshot(snap, [], max_per_section=5)
    # First 5 entries preserved in input order.
    assert [p["id"] for p in out["plugins"]] == ["p0", "p1", "p2", "p3", "p4"]


def test_compact_snapshot_strips_finding_extras():
    """Finding entries reduce to {id, severity} — keeps row size bounded
    even if the finding itself carries large evidence text."""
    from apps.api.src.services.resources_history import compact_snapshot

    findings = [
        {"id": "rule_a", "severity": "warn",
         "title": "long title…", "evidence": "x" * 10_000,
         "recommendation": "y" * 5_000,
         "affected": [{"type": "table", "name": "z"}]},
    ]
    out = compact_snapshot({"server": {}, "postgres": {}, "plugins": [], "syncs": []}, findings)
    assert out["findings"] == [{"id": "rule_a", "severity": "warn"}]


# ── Whitelist validation ────────────────────────────────────────────


def test_get_metric_history_rejects_unknown_metric():
    from apps.api.src.services import resources_history as rh

    raised = False
    try:
        rh.get_metric_history("garbage")
    except ValueError as e:
        raised = True
        assert "Unsupported metric" in str(e)
    assert raised


def test_get_metric_history_requires_plugin_for_plugin_size():
    from apps.api.src.services import resources_history as rh

    raised = False
    try:
        rh.get_metric_history("plugin_size")
    except ValueError as e:
        raised = True
        assert "plugin" in str(e).lower()
    assert raised


def test_get_finding_history_rejects_garbage_id():
    from apps.api.src.services import resources_history as rh

    bad_inputs = ["", " ", "a; DROP TABLE x;", "x" * 200]
    for bad in bad_inputs:
        raised = False
        try:
            rh.get_finding_history(bad)
        except ValueError:
            raised = True
        assert raised, f"expected rejection for {bad!r}"


def test_clamp_days_caps_at_max():
    from apps.api.src.services.resources_history import _clamp_days, MAX_HISTORY_DAYS
    assert _clamp_days(1000) == MAX_HISTORY_DAYS
    assert _clamp_days(0) == 1
    assert _clamp_days(-5) == 1
    assert _clamp_days(45) == 45


# ── DB queries (mocked) ─────────────────────────────────────────────


def test_get_metric_history_postgres_scalar(monkeypatch):
    from apps.api.src.services import resources_history as rh

    rows = [(datetime(2026, 5, 1, 3, 30, 0, tzinfo=timezone.utc), 100.0),
            (datetime(2026, 5, 2, 3, 30, 0, tzinfo=timezone.utc), 110.5),
            (datetime(2026, 5, 3, 3, 30, 0, tzinfo=timezone.utc), None)]  # gap
    monkeypatch.setattr(rh, "get_pg_conn", _fake_pg([rows]))

    out = rh.get_metric_history("db_size", days=30)
    assert len(out) == 3
    assert out[0].value == 100.0
    assert out[2].value is None  # gap preserved as None, not 0


def test_get_finding_history_returns_present_and_severity(monkeypatch):
    from apps.api.src.services import resources_history as rh

    rows = [
        (datetime(2026, 5, 1, 3, 30, 0, tzinfo=timezone.utc), True, "warn"),
        (datetime(2026, 5, 2, 3, 30, 0, tzinfo=timezone.utc), False, None),
        (datetime(2026, 5, 3, 3, 30, 0, tzinfo=timezone.utc), True, "critical"),
    ]
    monkeypatch.setattr(rh, "get_pg_conn", _fake_pg([rows]))

    out = rh.get_finding_history("sync_overlapping_schedule", days=30)
    assert len(out) == 3
    assert out[0].present is True and out[0].severity == "warn"
    assert out[1].present is False and out[1].severity is None
    assert out[2].present is True and out[2].severity == "critical"


# ── Snapshot writer / purger ────────────────────────────────────────


def test_purge_old_snapshots_returns_count(monkeypatch):
    """purge_old_snapshots issues one DELETE and returns rowcount."""
    from apps.api.src.services import resources_history as rh

    class _CountingCursor:
        def __init__(self):
            self.rowcount = 7
            self.executed = []

        def execute(self, sql, params=None):
            self.executed.append((str(sql), params))

    class _CountingConn:
        def __init__(self):
            self._cur = _CountingCursor()
        def cursor(self):
            return self._cur
        def commit(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(rh, "get_pg_conn", lambda: _CountingConn())
    n = rh.purge_old_snapshots(retention_days=90)
    assert n == 7


def test_json_default_handles_decimal_and_datetime():
    """v0.9.11.19.1 hotfix: psycopg2 returns NUMERIC as Decimal and
    timestamps as datetime; both must serialize through the snapshot
    JSON encoder without raising."""
    from apps.api.src.services.resources_history import _json_default
    from decimal import Decimal
    from datetime import datetime as _dt, timezone as _tz
    from uuid import UUID
    import json

    payload = {
        "pct": Decimal("99.85"),
        "ts": _dt(2026, 5, 4, 3, 30, 0, tzinfo=_tz.utc),
        "id": UUID("12345678-1234-5678-1234-567812345678"),
    }
    body = json.dumps(payload, default=_json_default)
    parsed = json.loads(body)
    assert parsed["pct"] == 99.85
    assert "2026-05-04T03:30:00" in parsed["ts"]
    assert parsed["id"] == "12345678-1234-5678-1234-567812345678"


def test_insert_snapshot_uses_upsert(monkeypatch):
    """insert_snapshot composes ON CONFLICT DO UPDATE so re-running the
    worker on the same day overwrites rather than failing."""
    from apps.api.src.services import resources_history as rh

    captured: list[tuple] = []

    class _Cur:
        def execute(self, sql, params=None):
            captured.append((str(sql), params))

    class _Conn:
        def cursor(self):
            return _Cur()
        def commit(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(rh, "get_pg_conn", lambda: _Conn())
    payload = {
        "server": {"foo": 1},
        "postgres": {"db_size_mb": 100},
        "plugins": [],
        "syncs": [],
        "findings": [],
    }
    rh.insert_snapshot(payload, snapshot_at=datetime(2026, 5, 4, 3, 30, 0, tzinfo=timezone.utc))
    assert len(captured) == 1
    sql, _ = captured[0]
    assert "ON CONFLICT (snapshot_at) DO UPDATE" in sql
