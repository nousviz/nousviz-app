"""P230 / B345: alerts on any database — dialects, mapping, periods, verdicts.

No live database is touched: a fake driver returns canned columns and rows.
The live checks are in nousviz-docs 1.0/testing/P230-test-plan.md.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src import alert_engine as ae  # noqa: E402
from apps.api.src.query_drivers import (  # noqa: E402
    ClickHouseDriver, ColumnInfo, QueryDriver, QueryError, TableRef, _ch_param, column_kind, dialect_for,
)

TODAY = date(2026, 11, 11)   # a Wednesday

COLS = {c.name: c for c in [
    ColumnInfo("day", "Date", "date"),
    ColumnInfo("ts", "DateTime", "datetime"),
    ColumnInfo("net_rev", "Float64", "number"),
    ColumnInfo("rs_com", "Float64", "number"),
    ColumnInfo("clicks", "UInt64", "number"),
    ColumnInfo("program", "String", "text"),
    ColumnInfo("account", "String", "text"),
    ColumnInfo("currency", "LowCardinality(String)", "text"),
]}


def alert(**kw):
    base = {"label": "t", "db_engine": "postgres", "dataset": "facts", "date_column": "day", "metric": "net_rev",
            "aggregation": "sum", "condition_type": "absolute_above", "threshold": 10, "check_period": "yesterday",
            "compare_to": "7d_avg"}
    base.update(kw)
    return base


class FakeDriver(QueryDriver):
    def __init__(self, engine="postgres", rows=None, table_engine=None):
        self.engine = engine
        super().__init__({})
        self.rows = rows or []
        self.table_engine = table_engine
        self.sent = []

    def run(self, sql, params=None, **kw):
        self.sent.append((sql, params))
        return self.rows

    def locate(self, name, database=None):
        return TableRef(name=name, database=database or ("plugdb" if self.engine == "clickhouse" else None),
                        engine_name=self.table_engine)

    def columns(self, table):
        return list(COLS.values())


def factory(drv):
    return lambda engine, connection_id=None, pg_cursor=None: drv


# ── Types and dates ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("t,kind", [
    ("Nullable(DateTime64(3))", "datetime"), ("LowCardinality(Nullable(String))", "text"), ("Date32", "date"),
    ("timestamp with time zone", "datetime"), ("numeric", "number"), ("Decimal(18, 4)", "number"),
    ("UInt64", "number"), ("double precision", "number"), ("character varying", "text"), ("bool", "bool"),
    ("tinyint(1)", "bool"), ("jsonb", "other"),
])
def test_column_kinds(t, kind):
    assert column_kind(t) == kind


def test_periods():
    assert ae.period_bounds("yesterday", TODAY) == (date(2026, 11, 10), date(2026, 11, 11))
    assert ae.period_bounds("this_week", TODAY) == (date(2026, 11, 9), date(2026, 11, 12))
    assert ae.period_bounds("this_month", TODAY) == (date(2026, 11, 1), date(2026, 11, 12))
    assert ae.period_bounds("last_month", TODAY) == (date(2026, 10, 1), date(2026, 11, 1))
    assert ae.period_bounds("last_month", date(2026, 1, 5)) == (date(2025, 12, 1), date(2026, 1, 1))
    assert ae.period_bounds("rolling_7d", TODAY) == (date(2026, 11, 4), date(2026, 11, 12))


def test_comparisons():
    s, e = date(2026, 10, 1), date(2026, 11, 1)
    assert ae.baseline_bounds("previous_period", s, e) == (date(2026, 8, 31), date(2026, 10, 1), None)
    assert ae.baseline_bounds("same_period_last_month", s, e) == (date(2026, 9, 1), date(2026, 10, 1), None)
    assert ae.baseline_bounds("7d_avg", s, e) == (date(2026, 9, 24), date(2026, 10, 1), 7)
    # Month-end clamp: 31 March -> 28/29 February.
    assert ae.baseline_bounds("same_period_last_month", date(2026, 3, 31), date(2026, 4, 1))[0] == date(2026, 2, 28)


# ── SQL per dialect ─────────────────────────────────────────────────────────

def build(engine, table_engine=None, **kw):
    spec = ae.spec_from_alert(alert(db_engine=engine, **kw))
    t = TableRef("facts", "plugdb" if engine == "clickhouse" else None, table_engine)
    return ae.build_query(spec, t, COLS, today=TODAY)


def test_postgres_sql():
    q = build("postgres", group_by_columns=["program"], filters=[{"column": "program", "op": "neq", "value": "x"}])
    assert 'sum("net_rev") FILTER (WHERE "day" >= %(p_start)s AND "day" < %(p_end)s) AS current_value' in q.sql
    assert 'FROM "facts"' in q.sql and '"program" <> %(f_0)s' in q.sql and "GROUP BY g_0" in q.sql
    assert q.params["p_start"] == date(2026, 11, 10) and q.params["f_0"] == "x"


def test_clickhouse_sql_final_and_types():
    q = build("clickhouse", table_engine="ReplacingMergeTree(updated_at)", group_by_columns=["program"],
              filters=[{"column": "clicks", "op": "gte", "value": "5"}, {"column": "program", "op": "in",
                                                                         "value": "a, b"}])
    assert "FROM `plugdb`.`facts` FINAL" in q.sql
    assert "sumIf(`net_rev`, `day` >= {p_start:Date} AND `day` < {p_end:Date})" in q.sql
    assert "`clicks` >= {f_0:Float64}" in q.sql and "has({f_1:Array(String)}, `program`)" in q.sql
    assert q.params["f_0"] == 5.0 and q.params["f_1"] == ["a", "b"]


def test_clickhouse_plain_mergetree_has_no_final():
    q = build("clickhouse", table_engine="MergeTree")
    assert "FINAL" not in q.sql


def test_mysql_sql():
    q = build("mysql", date_column="ts", value_kind="count", metric="*",
              filters=[{"column": "program", "op": "not_in", "value": ["a"]}])
    assert "COUNT(CASE WHEN DATE(`ts`) >= %(p_start)s AND DATE(`ts`) < %(p_end)s THEN 1 END)" in q.sql
    assert "`program` NOT IN %(f_0)s" in q.sql


def test_ratio_and_currency_split():
    q = build("clickhouse", value_kind="ratio", metric="rs_com", denominator="net_rev", currency_column="currency",
              group_by_columns=["account"])
    assert "nullIf(toFloat64(sumIf(`net_rev`" in q.sql
    assert "`account` AS g_0, `currency` AS g_1" in q.sql and q.group_aliases == ["g_0", "g_1"]


def test_min_volume_having():
    q = build("postgres", group_by_columns=["account"], min_volume_column="net_rev", min_volume=100)
    assert 'HAVING sum("net_rev") FILTER (WHERE "day" >= %(p_start)s' in q.sql and q.params["min_volume"] == 100.0


def test_datetime_date_column_in_clickhouse():
    q = build("clickhouse", date_column="ts")
    assert "toDate(`ts`) >= {w_start:Date}" in q.sql


# ── Validation (identifiers come only from real columns) ────────────────────

@pytest.mark.parametrize("kw,msg", [
    ({"metric": "nope"}, "not a column"),
    ({"metric": "program"}, "must be a number"),
    ({"date_column": "net_rev"}, "date or datetime"),
    ({"group_by_columns": ["program", "account", "currency", "day"]}, "at most 3"),
    ({"filters": [{"column": "x) OR 1=1 --", "op": "eq", "value": 1}]}, "not a column"),
    ({"filters": [{"column": "program", "op": "drop", "value": 1}]}, "Unknown filter"),
    ({"value_kind": "ratio", "metric": "rs_com", "denominator": "net_rev", "aggregation": "avg"}, "never two averages"),
    ({"check_period": "forever"}, "Unknown period"),
    ({"dataset": "facts; DROP TABLE x"}, None),
])
def test_validation_rejects(kw, msg):
    spec = ae.spec_from_alert(alert(**kw))
    with pytest.raises((ae.AlertConfigError, QueryError)) as e:
        if kw.get("dataset"):
            ae.resolve_table(FakeDriver(), spec)
        ae.build_query(spec, TableRef("facts"), COLS, today=TODAY)
    if msg:
        assert msg.lower() in str(e.value).lower()


def test_filter_values_are_bound_not_pasted():
    q = build("postgres", filters=[{"column": "program", "op": "eq", "value": "'; DROP TABLE facts; --"}])
    assert "DROP" not in q.sql and q.params["f_0"] == "'; DROP TABLE facts; --"


def test_legacy_alert_still_builds():
    # A pre-P230 row: group_by + scope_filters, date column `date`.
    cols = dict(COLS, date=ColumnInfo("date", "date", "date"))
    spec = ae.spec_from_alert({"label": "old", "dataset": "facts", "metric": "net_rev", "aggregation": "sum",
                               "condition_type": "threshold_drop", "threshold": -20, "group_by": "program",
                               "scope_filters": {"account": "a1"}, "check_period": "yesterday"})
    q = ae.build_query(spec, TableRef("facts"), cols, today=TODAY)
    assert '"date" >= %(p_start)s' in q.sql and '"account" = %(f_0)s' in q.sql and "GROUP BY g_0" in q.sql


# ── Verdicts (B345: Test must match the scheduled run) ──────────────────────

def test_evaluate_alert_verdicts_and_scaling():
    rows = [{"g_0": "A", "current_value": 50, "baseline_value": 700},   # 7-day sum 700 -> 100/day
            {"g_0": "B", "current_value": 120, "baseline_value": 700}]
    drv = FakeDriver(rows=rows)
    ev = ae.evaluate_alert(alert(group_by_columns=["program"], condition_type="threshold_drop", threshold=-30),
                           today=TODAY, driver_factory=factory(drv))
    assert ev.status == "ok" and ev.error is None
    by = {r["group"]: r for r in ev.rows}
    assert by["A"]["baseline"] == 100 and by["A"]["change_pct"] == -50.0 and by["A"]["fired"] is True
    assert by["B"]["fired"] is False and ev.fired_rows == [by["A"]]
    assert ev.sql == drv.sent[0][0]


def test_zero_check_fires_on_a_silent_group():
    drv = FakeDriver(rows=[{"g_0": "A", "current_value": None, "baseline_value": 70}])
    ev = ae.evaluate_alert(alert(group_by_columns=["program"], condition_type="zero_check"), today=TODAY,
                           driver_factory=factory(drv))
    assert ev.rows[0]["fired"] is True


def test_no_rows_is_no_data_not_error():
    ev = ae.evaluate_alert(alert(), today=TODAY, driver_factory=factory(FakeDriver(rows=[])))
    assert ev.status == "no_data" and ev.error is None


def test_errors_are_reported_not_raised():
    ev = ae.evaluate_alert(alert(metric="missing"), today=TODAY, driver_factory=factory(FakeDriver()))
    assert ev.status == "error" and "missing" in ev.error


# ── ClickHouse request: read-only GET, credentials in headers ───────────────

def test_clickhouse_request_is_get_with_header_credentials():
    d = ClickHouseDriver({"host": "ch", "port": 8123, "user": "u", "password": "s3cret", "database": "default"})
    req = d._request("SELECT {a:String}", {"a": "x'y", "l": ["a", "b'c"]}, {"max_execution_time": 30})
    assert req.get_method() == "GET"
    assert "s3cret" not in req.full_url and req.headers.get("X-clickhouse-key") == "s3cret"
    assert "param_a=x%27y" in req.full_url and "max_execution_time=30" in req.full_url
    assert _ch_param(["a", "b'c"]) == "['a','b\\'c']"


def test_dialects_exist():
    for e in ("postgres", "clickhouse", "mysql"):
        assert dialect_for(e).engine == e
    with pytest.raises(QueryError):
        dialect_for("oracle")
