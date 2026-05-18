"""B208 (v0.9.6.1) — tests for app_logs column promotion.

Covers helper signatures (named-kwarg discipline, positional-misuse
catches, propagation through log_plugin_event), without exercising
the DB layer. DB-touching paths (column writes, JSONB fallback
filtering, keyset pagination) are covered by the integration smoke
during deploy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── log_job_event signature + DB write contract ─────────────────────


def test_log_job_event_writes_promoted_columns(monkeypatch):
    """When the caller passes plugin_id / actor_user_id / run_id as
    kwargs, those values are passed to the INSERT params for the
    dedicated columns."""
    from apps.api.src import log_events

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_get_pg_conn():
        return FakeConn()

    monkeypatch.setattr(
        "apps.api.src.db.get_pg_conn", fake_get_pg_conn
    )

    log_events.log_job_event(
        "info",
        "test event",
        {"extra": "context"},
        source="sync",
        plugin_id="myplugin",
        actor_user_id="abc-123",
        run_id=42,
    )

    # SQL should have all 7 columns in the INSERT.
    assert "plugin_id" in captured["sql"]
    assert "actor_user_id" in captured["sql"]
    assert "run_id" in captured["sql"]
    # Last 3 params are the promoted columns.
    params = captured["params"]
    assert params[-3] == "myplugin"
    assert params[-2] == "abc-123"
    assert params[-1] == 42


def test_log_job_event_keyword_only_for_promoted_fields():
    """Passing plugin_id / actor_user_id / run_id positionally raises
    TypeError. Prevents typo'd args silently landing as detail."""
    from apps.api.src import log_events

    # The signature is (level, message, detail=None, source="sync", *,
    # plugin_id=None, actor_user_id=None, run_id=None). Passing a fifth
    # positional argument should fail.
    with pytest.raises(TypeError):
        log_events.log_job_event(
            "info", "msg", {}, "sync", "myplugin"  # 5th positional — illegal
        )


def test_log_job_event_writes_null_columns_when_kwargs_omitted(monkeypatch):
    """Helper still works when kwargs aren't provided. Columns are NULL,
    detail unchanged. Preserves back-compat with ~50 existing call sites
    that don't pass the kwargs."""
    from apps.api.src import log_events

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["params"] = params

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "apps.api.src.db.get_pg_conn", lambda: FakeConn()
    )

    log_events.log_job_event("info", "msg", {"key": "val"})
    params = captured["params"]
    # Last 3 params are the promoted columns — all None.
    assert params[-3] is None
    assert params[-2] is None
    assert params[-1] is None


def test_log_job_event_merges_kwargs_into_detail(monkeypatch):
    """Promoted kwargs are also written into detail JSONB (setdefault)
    so legacy `detail->>'plugin_id'` queries keep working."""
    import json
    from apps.api.src import log_events

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["params"] = params

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "apps.api.src.db.get_pg_conn", lambda: FakeConn()
    )

    log_events.log_job_event(
        "info",
        "msg",
        None,
        plugin_id="myplugin",
        run_id=99,
    )
    # detail param is the 4th in the INSERT — index 3.
    detail_json = captured["params"][3]
    detail = json.loads(detail_json)
    assert detail["plugin_id"] == "myplugin"
    assert detail["run_id"] == 99


def test_log_job_event_preserves_existing_detail_keys(monkeypatch):
    """If a caller already put plugin_id in detail AND passed it as a
    kwarg, the kwarg wins for the column but the existing detail key
    is preserved (setdefault, not unconditional set). Edge-case-safe."""
    import json
    from apps.api.src import log_events

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["params"] = params

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "apps.api.src.db.get_pg_conn", lambda: FakeConn()
    )

    log_events.log_job_event(
        "info",
        "msg",
        {"plugin_id": "from-detail"},
        plugin_id="from-kwarg",
    )
    params = captured["params"]
    # Column gets the kwarg value.
    assert params[-3] == "from-kwarg"
    # detail keeps the original detail value (setdefault no-op).
    detail = json.loads(params[3])
    assert detail["plugin_id"] == "from-detail"


# ── log_plugin_event propagation ────────────────────────────────────


def test_log_plugin_event_propagates_actor_and_run(monkeypatch):
    """The wrapper now accepts actor_user_id and run_id and forwards
    them to log_job_event. plugin_id is auto-promoted from the
    positional argument."""
    from apps.api.src import log_events

    captured: list[dict] = []

    def fake_log_job_event(level, message, detail=None, source="sync", **kwargs):
        captured.append(
            {
                "level": level,
                "message": message,
                "detail": detail,
                "source": source,
                **kwargs,
            }
        )

    monkeypatch.setattr(log_events, "log_job_event", fake_log_job_event)

    log_events.log_plugin_event(
        "info",
        "myplugin",
        "install",
        "plugin installed",
        detail={"version": "1.2.3"},
        source="plugin_install",
        actor_user_id="user-uuid",
        run_id=42,
    )

    assert len(captured) == 1
    e = captured[0]
    assert e["plugin_id"] == "myplugin"
    assert e["actor_user_id"] == "user-uuid"
    assert e["run_id"] == 42
    assert e["source"] == "plugin_install"
    # Wrapper still prefixes the message and merges plugin_id/action.
    assert "[myplugin] install:" in e["message"]
    assert e["detail"]["plugin_id"] == "myplugin"
    assert e["detail"]["action"] == "install"
    assert e["detail"]["version"] == "1.2.3"


def test_log_plugin_event_works_without_actor_or_run(monkeypatch):
    """Existing call sites that don't supply actor/run continue to work —
    those columns end up NULL, which is correct."""
    from apps.api.src import log_events

    captured: list[dict] = []

    def fake_log_job_event(level, message, detail=None, source="sync", **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(log_events, "log_job_event", fake_log_job_event)

    log_events.log_plugin_event(
        "warning",
        "myplugin",
        "update_check",
        "no-op",
    )

    assert len(captured) == 1
    e = captured[0]
    assert e["plugin_id"] == "myplugin"
    assert e["actor_user_id"] is None
    assert e["run_id"] is None


def test_log_plugin_event_keyword_only_actor_and_run():
    """actor_user_id and run_id are keyword-only on log_plugin_event
    too. Prevents misuse if someone tries to pass them positionally
    after source."""
    from apps.api.src import log_events

    # Positional args after source should not be accepted.
    with pytest.raises(TypeError):
        log_events.log_plugin_event(
            "info",
            "myplugin",
            "install",
            "msg",
            None,
            "plugin_install",
            "actor-uuid",  # 7th positional — illegal
        )


# ── B212: actor propagation through enqueue ─────────────────────────


def test_enqueue_async_run_stamps_actor_in_details(monkeypatch):
    """B212 (v0.9.6.3): actor_user_id kwarg passed at enqueue ends up in
    job_runs.details JSONB so the worker can read it back when it logs
    sync lifecycle events."""
    import json
    from apps.api.src.routes import sync as sync_module

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params

        def fetchone(self):
            return [42]

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "apps.api.src.routes.sync.get_pg_conn", lambda: FakeConn()
    )

    sync_module._enqueue_async_run(
        "myplugin", "incremental", actor_user_id="abc-123"
    )

    # Second positional in the INSERT is the JSONB details payload.
    details = json.loads(captured["params"][1])
    assert details["mode"] == "incremental"
    assert details["actor_user_id"] == "abc-123"


def test_enqueue_async_run_omits_actor_when_none(monkeypatch):
    """run_scheduler.py and other autonomous callers don't pass actor.
    The key is omitted from details rather than written as null — keeps
    the column NULL in the eventual log entries, which is correct for
    autonomous runs."""
    import json
    from apps.api.src.routes import sync as sync_module

    captured: dict = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["params"] = params

        def fetchone(self):
            return [42]

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        "apps.api.src.routes.sync.get_pg_conn", lambda: FakeConn()
    )

    sync_module._enqueue_async_run("myplugin", "incremental")

    details = json.loads(captured["params"][1])
    assert "actor_user_id" not in details
    assert details["mode"] == "incremental"


def test_enqueue_async_run_actor_keyword_only():
    """actor_user_id is keyword-only so a future caller passing it
    positionally fails loudly instead of being placed in mode_label."""
    from apps.api.src.routes import sync as sync_module
    import pytest as _pytest

    with _pytest.raises(TypeError):
        sync_module._enqueue_async_run("myplugin", "incremental", "actor-positional")
