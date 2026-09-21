"""B201: core-owned keys must not make a plugin's settings unsaveable.

`plugin_settings` holds core's own `_trust_frontend` consent flag and
`_conn.*` rows alongside the plugin-declared settings. The settings form
seeds itself from GET /settings and posts back what it was given, so once
frontend trust was granted the form submitted `_trust_frontend`,
`save_plugin_settings` validated it against the plugin manifest — where a
reserved key can never be declared — and rejected the whole batch with
422. Every legitimate change in that submission was discarded, and the
plugin's settings became permanently unsaveable through the UI.

These tests don't touch Postgres: `get_pg_conn` is monkey-patched with a
recording fake, which is what lets them assert exactly which rows a save
would write.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.routes import plugins as plugins_routes  # noqa: E402


class _FakeCursor:
    def __init__(self, sink, rows):
        self._sink = sink
        self._rows = rows

    def execute(self, sql, params=None):
        self._sink.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, sink, rows):
        self._sink = sink
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._sink, self._rows)

    def commit(self):
        self._sink.append(("COMMIT", None))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def recorder(monkeypatch):
    """Capture every statement the route would run, with no database."""
    sink: list[tuple[str, object]] = []
    rows: list[tuple[str, object]] = []

    import apps.api.src.db as db

    monkeypatch.setattr(db, "get_pg_conn", lambda *a, **k: _FakeConn(sink, rows))
    monkeypatch.setattr(
        plugins_routes,
        "_load_plugin",
        lambda plugin_id, installed_only=False: {
            "id": plugin_id,
            "settings": [{"name": "backfill_start"}, {"name": "earliest_valid_date"}],
        },
    )
    monkeypatch.setattr(plugins_routes, "_log_plugin_action", lambda *a, **k: None)
    return sink, rows


def _save(keys_values):
    body = plugins_routes.PluginSettingsBody(
        settings=[{"key": k, "value": v} for k, v in keys_values]
    )
    return asyncio.run(
        plugins_routes.save_plugin_settings("demo-plugin", body, None, None)
    )


def _written(sink):
    return [p[1] for s, p in sink if s.startswith("INSERT INTO plugin_settings")]


def test_reserved_key_does_not_discard_the_batch(recorder):
    """The exact repro: trust granted, one real edit, save must persist it."""
    sink, _ = recorder
    result = _save([("_trust_frontend", True), ("backfill_start", "2025-01-01")])
    assert result == {"ok": True}
    assert _written(sink) == ["backfill_start"], (
        "the declared setting must be written even when a reserved key rides along"
    )


def test_reserved_keys_are_never_stored(recorder):
    """Ignored, not persisted — a save must not rewrite core's consent flag."""
    sink, _ = recorder
    _save([("_trust_frontend", False), ("_conn.host", "evil"), ("backfill_start", "x")])
    assert "_trust_frontend" not in _written(sink)
    assert "_conn.host" not in _written(sink)


def test_a_save_of_only_reserved_keys_writes_nothing_and_succeeds(recorder):
    sink, _ = recorder
    assert _save([("_trust_frontend", True)]) == {"ok": True}
    assert _written(sink) == []


def test_undeclared_ordinary_key_is_still_rejected(recorder):
    """The validator's actual purpose must survive the fix."""
    with pytest.raises(HTTPException) as exc:
        _save([("backfill_start", "2025-01-01"), ("nonsense", 1)])
    assert exc.value.status_code == 422
    assert "nonsense" in str(exc.value.detail)


def test_undeclared_key_rejects_before_any_write(recorder):
    sink, _ = recorder
    with pytest.raises(HTTPException):
        _save([("backfill_start", "2025-01-01"), ("nonsense", 1)])
    assert _written(sink) == [], "validation must run to completion before writing"


def test_get_settings_does_not_return_core_owned_keys(recorder):
    """The round-trip's source: the form can only post back what GET hands it."""
    sink, rows = recorder
    rows.extend([("backfill_start", "2025-01-01")])
    out = asyncio.run(plugins_routes.get_plugin_settings("demo-plugin", None))
    assert out == {"settings": [{"key": "backfill_start", "value": "2025-01-01"}]}
    select = [s for s, _ in sink if s.startswith("SELECT key, value")][0]
    assert "left(key, 1) <> '_'" in select, (
        "underscore-prefixed core keys must be excluded in SQL, not in Python"
    )
