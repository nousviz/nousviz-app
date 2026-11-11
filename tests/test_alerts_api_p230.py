"""P230 / B345: alert sources, Test, preview and plugin alerts.yaml — no live database."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src import alert_engine as ae  # noqa: E402
from apps.api.src import alert_queries as aq  # noqa: E402
from apps.api.src import alert_sources as asrc  # noqa: E402
from apps.api.src.query_drivers import ColumnInfo, QueryDriver, TableRef, dialect_for  # noqa: E402
from apps.api.src.routes import alerts as routes  # noqa: E402


# ── Source resolution happens on the server ─────────────────────────────────

def test_pg_source():
    s = asrc.resolve("pg:app_logs")
    assert (s.engine, s.source_kind, s.table, s.connection_id) == ("postgres", "table", "app_logs", None)


@pytest.mark.parametrize("sid", ["pg:a;drop", "pg:", "plugin:x", "conn:not-a-uuid", "query:p:", "weird:1"])
def test_bad_source_ids(sid):
    with pytest.raises(asrc.SourceError):
        asrc.resolve(sid)


def _fake_dataset(monkeypatch, ds):
    monkeypatch.setattr(asrc, "plugin_dataset", lambda pid, name: ds if name == ds.get("name") else None)


def test_plugin_dataset_carries_engine_and_database(monkeypatch):
    _fake_dataset(monkeypatch, {"name": "facts", "db": "clickhouse", "database": "plugdb", "date_column": "day"})
    s = asrc.resolve("plugin:my-plugin:facts")
    assert (s.engine, s.database, s.dataset, s.date_column) == ("clickhouse", "plugdb", "plugdb.facts", "day")
    assert asrc.source_id_for_alert({"source_kind": "plugin_dataset", "plugin_id": "my-plugin",
                                     "dataset": "plugdb.facts"}) == "plugin:my-plugin:facts"


def test_alertable_false_is_refused(monkeypatch):
    _fake_dataset(monkeypatch, {"name": "facts", "db": "clickhouse", "alertable": False})
    with pytest.raises(HTTPException) as e:
        routes._apply_source({}, "plugin:my-plugin:facts", None)
    assert e.value.status_code == 422 and "out of direct alerts" in e.value.detail


def test_client_cannot_override_engine_or_dataset(monkeypatch):
    _fake_dataset(monkeypatch, {"name": "facts", "db": "clickhouse"})
    alert = {"db_engine": "postgres", "dataset": "users", "plugin_id": "core", "connection_id": "x"}
    routes._apply_source(alert, "plugin:my-plugin:facts", None)
    assert (alert["db_engine"], alert["dataset"], alert["plugin_id"], alert["connection_id"]) == \
        ("clickhouse", "facts", "my-plugin", None)


# ── B345: Test returns the scheduled run's verdicts ─────────────────────────

COLS = [ColumnInfo("date", "date", "date"), ColumnInfo("net_rev", "numeric", "number"),
        ColumnInfo("program", "text", "text")]


class FakeDriver(QueryDriver):
    engine = "postgres"

    def __init__(self, rows):
        super().__init__({})
        self.rows, self.sent = rows, []

    def run(self, sql, params=None, **kw):
        self.sent.append(sql)
        return self.rows

    def locate(self, name, database=None):
        return TableRef(name)

    def columns(self, table):
        return COLS


class _Cur:
    def __init__(self, row):
        self.row, self.executed = row, []

    def execute(self, sql, params=None):
        self.executed.append(sql)

    @property
    def description(self):
        return [(k,) for k in self.row]

    def fetchall(self):
        return [tuple(self.row.values())]


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_test_endpoint_matches_scheduled_verdict(monkeypatch):
    row = {"id": "a1", "label": "Drop", "dataset": "facts", "metric": "net_rev", "aggregation": "sum",
           "condition_type": "threshold_drop", "threshold": -30, "compare_to": "7d_avg", "check_period": "yesterday",
           "group_by_columns": ["program"], "db_engine": "postgres", "date_column": "date"}
    drv = FakeDriver([{"g_0": "A", "current_value": 50, "baseline_value": 700},
                      {"g_0": "B", "current_value": 120, "baseline_value": 700}])
    cur = _Cur(row)
    monkeypatch.setattr(routes, "get_pg_conn", lambda: _Conn(cur))
    monkeypatch.setattr(ae, "get_driver", lambda *a, **k: drv)
    import asyncio
    out = asyncio.run(routes.test_alert("a1", request=None, _=None))
    assert out["fired"] is True and out["rows_checked"] == 2 and out["status"] == "ok"
    assert [r["group"] for r in out["triggered_rows"]] == ["A"]
    # The same evaluation the worker runs:
    sched = ae.evaluate_alert(row, driver_factory=lambda *a, **k: drv)
    assert [r["group"] for r in sched.fired_rows] == ["A"]
    # Nothing recorded or sent: the only Postgres statement is the SELECT of the alert.
    assert all(s.lstrip().upper().startswith("SELECT") for s in cur.executed)


# ── alerts.yaml: plugin-written, validated, bound ───────────────────────────

YAML = """
queries:
  - id: low_rs
    label: Low RS
    db: postgres
    params:
      min_net: {type: number, default: 100, label: Minimum net}
      tier: {type: enum, options: [gold, silver], default: gold}
    default_condition: {type: absolute_below, threshold: 0.1}
    sql: |
      SELECT program AS group_name, sum(rs) / nullif(sum(net), 0) AS current_value
      FROM facts WHERE day >= {period_start} AND day < {period_end}
        AND tier = {tier} GROUP BY program HAVING sum(net) >= {min_net}
  - id: writes
    sql: "DELETE FROM facts"
  - id: two_statements
    sql: "SELECT 1 AS current_value; SELECT 2"
  - id: undeclared
    sql: "SELECT 1 AS current_value WHERE x = {nope}"
"""


@pytest.fixture
def plugin_root(tmp_path):
    d = tmp_path / "my-plugin"
    d.mkdir()
    (d / "alerts.yaml").write_text(YAML)
    return tmp_path


def test_alerts_yaml_validation(plugin_root):
    qs = {q.id: q for q in aq.list_queries(plugin_root)}
    assert qs["low_rs"].error is None
    assert "single SELECT" in qs["writes"].error
    assert "one statement" in qs["two_statements"].error
    assert "not a declared param" in qs["undeclared"].error


def test_alerts_yaml_binds_params(plugin_root):
    q = aq.find_query("my-plugin", "low_rs", plugin_root)
    sql, params = aq.render(q, dialect_for("clickhouse"), {"min_net": "250", "tier": "silver"},
                            {k: date(2026, 11, 1) for k in aq.BUILTINS})
    assert "{min_net:Float64}" in sql and "{tier:String}" in sql and "{period_start:Date}" in sql
    assert params["min_net"] == 250.0 and params["tier"] == "silver"
    with pytest.raises(ValueError):
        aq.render(q, dialect_for("postgres"), {"tier": "bronze"}, {k: date(2026, 11, 1) for k in aq.BUILTINS})
    with pytest.raises(ValueError):
        aq.render(q, dialect_for("postgres"), {"min_net": "lots"}, {k: date(2026, 11, 1) for k in aq.BUILTINS})


def test_plugin_query_evaluates_with_sandbox_role(plugin_root, monkeypatch):
    monkeypatch.setattr(aq, "PLUGINS_INSTALLED", plugin_root)
    calls = {}

    class D(FakeDriver):
        def run(self, sql, params=None, **kw):
            calls.update(kw)
            return [{"group_name": "A", "current_value": 0.02}, {"group_name": "B", "current_value": 0.3}]

    alert = {"label": "q", "source_kind": "plugin_query", "plugin_id": "my-plugin", "query_id": "low_rs",
             "db_engine": "postgres", "condition_type": "absolute_below", "threshold": 0.1,
             "check_period": "last_month", "query_params": {"tier": "gold"}}
    original = aq.find_query
    monkeypatch.setattr(aq, "find_query", lambda p, i, root=plugin_root: original(p, i, root))
    ev = ae.evaluate_alert(alert, today=date(2026, 11, 11), driver_factory=lambda *a, **k: D([]))
    assert ev.status == "ok", ev.error
    assert [r["group"] for r in ev.fired_rows] == ["A"]
    assert calls.get("sandbox_role") is True
    assert ev.params["period_start"] == "2026-10-01" and ev.params["min_net"] == 100.0
