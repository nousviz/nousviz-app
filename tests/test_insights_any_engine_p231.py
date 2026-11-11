"""P231: insights.yaml queries on any database — no live database."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src import query_drivers as qd  # noqa: E402
from apps.api.src.routes import insights  # noqa: E402


class _Driver:
    def __init__(self, rows=None, fail=None):
        self.rows, self.fail, self.calls = rows or [], fail, []

    def run(self, sql, params=None, **kw):
        self.calls.append((sql, kw))
        if self.fail:
            raise self.fail
        return self.rows


def test_clickhouse_query_runs_read_only_with_limits(monkeypatch):
    drv = _Driver(rows=[{"n": 3}])
    seen = {}

    def fake_get_driver(engine, connection_id=None, pg_cursor=None):
        seen.update(engine=engine, connection_id=connection_id)
        return drv

    monkeypatch.setattr(qd, "get_driver", fake_get_driver)
    out = insights._run_external_insights("p", [{"id": "a", "label": "A", "db": "clickhouse", "sql": "SELECT 3 AS n"}])
    assert out[0]["rows"] == [{"n": 3}] and seen == {"engine": "clickhouse", "connection_id": None}
    assert drv.calls[0][1] == {"timeout_s": insights.INSIGHT_TIMEOUT_S, "max_rows": insights.INSIGHT_MAX_ROWS}


def test_missing_connection_falls_back_or_shows_a_card(monkeypatch):
    def no_conn(*a, **k):
        raise qd.ConnectionMissing("No clickhouse connection.")

    monkeypatch.setattr(qd, "get_driver", no_conn)
    qs = [{"id": "quiet", "db": "clickhouse", "sql": "SELECT 1", "fallback_empty": True},
          {"id": "loud", "db": "clickhouse", "sql": "SELECT 1"}]
    out = insights._run_external_insights("p", qs)
    assert [c["id"] for c in out] == ["loud"]
    assert out[0]["severity"] == "warning" and "No clickhouse connection" in out[0]["description"]


def test_engine_default_is_postgres():
    assert insights._engine_of({"sql": "x"}) == "postgres"
    assert insights._engine_of({"db": "ClickHouse"}) == "clickhouse"
