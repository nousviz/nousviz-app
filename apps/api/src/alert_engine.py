"""
P230 / B345: one alert evaluator for the worker, Test and Preview.

An alert is stored in Postgres (`alert_rules`) and reads its data wherever
it lives: core Postgres, a ClickHouse plugin dataset or a table on a
registered connection. The user maps their own columns:

  date column · value (one column, a count, or a ratio of two sums) ·
  up to 3 group-by columns · filters · minimum volume · currency column

and picks a period, a comparison and a condition. This module turns that
mapping into one read-only query in the source's dialect, runs it through
`query_drivers`, and decides which groups fire.

Dates are computed here in Python and bound as parameters, so every engine
gets identical periods without dialect date arithmetic.

Money is never added across currencies: when a currency column is mapped it
becomes part of every group, so each currency is evaluated on its own.
"""

from __future__ import annotations

import calendar
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Optional

from .query_drivers import (
    AGGREGATIONS, ColumnInfo, ConnectionMissing, QueryDriver, QueryError, TableRef, dialect_for, get_driver,
    valid_ident,
)

MAX_GROUP_COLUMNS = 3
MAX_FILTERS = 20
GROUP_SEPARATOR = " · "

PERIODS: dict[str, str] = {
    "today": "today",
    "yesterday": "yesterday",
    "today_or_yesterday": "today or yesterday",
    "this_week": "this week",
    "rolling_7d": "last 7 days",
    "rolling_30d": "last 30 days",
    "this_month": "this month",
    "last_month": "last full month",
}

COMPARISONS: dict[str, str] = {
    "7d_avg": "7-day average",
    "14d_avg": "14-day average",
    "28d_avg": "28-day average",
    "30d_avg": "30-day average",
    "previous_period": "previous period",
    "same_period_last_month": "same period last month",
}

CONDITIONS = ("threshold_drop", "threshold_rise", "absolute_above", "absolute_below", "zero_check")
FILTER_OPS = ("eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "contains", "empty", "not_empty")
VALUE_KINDS = ("column", "count", "ratio")
ADDITIVE = ("sum", "count", "count_distinct")


class AlertConfigError(ValueError):
    """The alert's mapping can't be evaluated. The message is shown to the user."""


# ── Dates ────────────────────────────────────────────────────────────────────

def _month_start(d: date, months_back: int = 0) -> date:
    y, m = d.year, d.month - months_back
    while m < 1:
        m += 12
        y -= 1
    return date(y, m, 1)


def _shift_month(d: date, months: int) -> date:
    y, m = d.year, d.month + months
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def period_bounds(period: str, today: date) -> tuple[date, date]:
    """[start, end) of the checked period."""
    tomorrow = today + timedelta(days=1)
    if period == "today":
        return today, tomorrow
    if period == "today_or_yesterday":
        return today - timedelta(days=1), tomorrow
    if period == "this_week":
        return today - timedelta(days=today.weekday()), tomorrow
    if period == "rolling_7d":
        return today - timedelta(days=7), tomorrow      # same rows as the pre-P230 `date >= current_date - 7`
    if period == "rolling_30d":
        return today - timedelta(days=30), tomorrow
    if period == "this_month":
        return _month_start(today), tomorrow
    if period == "last_month":
        return _month_start(today, 1), _month_start(today)
    # yesterday, and anything unknown (the old default)
    return today - timedelta(days=1), today


def baseline_bounds(compare_to: str, start: date, end: date) -> tuple[date, date, Optional[int]]:
    """[start, end) of the comparison window, and N when it is an N-day average."""
    m = re.fullmatch(r"(\d{1,3})d_avg", compare_to or "")
    if m:
        n = max(1, int(m.group(1)))
        return start - timedelta(days=n), start, n
    if compare_to == "same_period_last_month":
        return _shift_month(start, -1), _shift_month(end, -1), None
    # previous_period (and the fallback): the same length, just before
    length = (end - start).days or 1
    return start - timedelta(days=length), start, None


# ── Normalised spec ──────────────────────────────────────────────────────────

@dataclass
class AlertSpec:
    label: str
    engine: str
    connection_id: Optional[str]
    source_kind: str
    plugin_id: Optional[str]
    table: str
    database: Optional[str]
    date_column: str
    value_kind: str
    metric: Optional[str]
    aggregation: str
    denominator: Optional[str]
    denominator_aggregation: str
    group_by: list[str]
    filters: list[dict]
    min_volume_column: Optional[str]
    min_volume: Optional[float]
    currency_column: Optional[str]
    condition: str
    threshold: float
    compare_to: str
    period: str
    min_baseline: float
    query_id: Optional[str] = None
    query_params: dict = field(default_factory=dict)


def _split_table(dataset: str) -> tuple[Optional[str], str]:
    if "." in (dataset or ""):
        db, _, name = dataset.partition(".")
        return db, name
    return None, dataset


def spec_from_alert(alert: dict) -> AlertSpec:
    """Read an alert_rules row (or an unsaved alert body) into a spec."""
    group_by = list(alert.get("group_by_columns") or [])
    if not group_by and alert.get("group_by"):
        group_by = [alert["group_by"]]
    filters = alert.get("filters")
    if not filters:
        legacy = alert.get("scope_filters") or {}
        filters = [{"column": k, "op": "eq", "value": v} for k, v in legacy.items() if v not in (None, "")]
    database, table = _split_table(alert.get("dataset") or "")
    value_kind = alert.get("value_kind") or ("count" if alert.get("metric") == "*" else "column")
    threshold = alert.get("threshold")
    return AlertSpec(
        label=alert.get("label") or alert.get("name") or "alert",
        engine=(alert.get("db_engine") or "postgres").lower(),
        connection_id=str(alert["connection_id"]) if alert.get("connection_id") else None,
        source_kind=alert.get("source_kind") or "table",
        plugin_id=alert.get("plugin_id"),
        table=table,
        database=database,
        date_column=alert.get("date_column") or "date",
        value_kind=value_kind,
        metric=None if value_kind == "count" else alert.get("metric"),
        aggregation=(alert.get("aggregation") or "sum").lower(),
        denominator=alert.get("denominator"),
        denominator_aggregation=(alert.get("denominator_aggregation") or "sum").lower(),
        group_by=group_by,
        filters=list(filters or []),
        min_volume_column=alert.get("min_volume_column"),
        min_volume=float(alert["min_volume"]) if alert.get("min_volume") not in (None, "") else None,
        currency_column=alert.get("currency_column") or None,
        condition=alert.get("condition_type") or "absolute_above",
        threshold=float(threshold) if threshold not in (None, "") else 0.0,
        compare_to={"prev_period": "previous_period"}.get(alert.get("compare_to") or "", alert.get("compare_to") or "7d_avg"),
        period=alert.get("check_period") or "yesterday",
        min_baseline=float(alert.get("min_baseline") or 0),
        query_id=alert.get("query_id"),
        query_params=dict(alert.get("query_params") or {}),
    )


# ── Validation against the real columns ─────────────────────────────────────

def validate(spec: AlertSpec, columns: dict[str, ColumnInfo]) -> None:
    """Every identifier must be a real column of the right kind."""
    def need(col: Optional[str], what: str, kinds: Optional[tuple] = None) -> ColumnInfo:
        if not col:
            raise AlertConfigError(f"Choose a {what}.")
        if not valid_ident(col) or col not in columns:
            raise AlertConfigError(f"The {what} '{col}' is not a column of {spec.table}.")
        info = columns[col]
        if kinds and info.kind not in kinds:
            raise AlertConfigError(f"The {what} '{col}' is {info.type}; it must be a "
                                   f"{' or '.join(kinds)} column.")
        return info

    need(spec.date_column, "date column", ("date", "datetime"))
    if spec.value_kind not in VALUE_KINDS:
        raise AlertConfigError(f"Unknown value type '{spec.value_kind}'.")
    if spec.aggregation not in AGGREGATIONS:
        raise AlertConfigError(f"Unknown aggregation '{spec.aggregation}'.")
    numeric = ("number", "bool")
    if spec.value_kind == "column":
        need(spec.metric, "value column", None if spec.aggregation in ("count", "count_distinct") else numeric)
    if spec.value_kind == "ratio":
        need(spec.metric, "numerator column", numeric)
        need(spec.denominator, "denominator column", numeric)
        if spec.aggregation not in ADDITIVE or spec.denominator_aggregation not in ADDITIVE:
            raise AlertConfigError("A ratio divides two totals (sum or count), never two averages.")
    if len(spec.group_by) > MAX_GROUP_COLUMNS:
        raise AlertConfigError(f"Group by at most {MAX_GROUP_COLUMNS} columns.")
    for g in spec.group_by:
        need(g, "group-by column")
    if spec.currency_column:
        need(spec.currency_column, "currency column")
    if spec.min_volume_column:
        need(spec.min_volume_column, "minimum-volume column", numeric)
    if len(spec.filters) > MAX_FILTERS:
        raise AlertConfigError(f"At most {MAX_FILTERS} filters.")
    for f in spec.filters:
        need(f.get("column"), "filter column")
        if f.get("op", "eq") not in FILTER_OPS:
            raise AlertConfigError(f"Unknown filter operator '{f.get('op')}'.")
    if spec.condition not in CONDITIONS:
        raise AlertConfigError(f"Unknown condition '{spec.condition}'.")
    if spec.period not in PERIODS:
        raise AlertConfigError(f"Unknown period '{spec.period}'.")
    if not (spec.compare_to in COMPARISONS or re.fullmatch(r"\d{1,3}d_avg", spec.compare_to)):
        raise AlertConfigError(f"Unknown comparison '{spec.compare_to}'.")


# ── SQL ──────────────────────────────────────────────────────────────────────

@dataclass
class BuiltQuery:
    sql: str
    params: dict
    group_aliases: list[str]
    period: tuple[date, date]
    baseline: tuple[date, date]
    avg_days: Optional[int]


def _coerce(value: Any, kind: str) -> Any:
    if kind == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            raise AlertConfigError(f"'{value}' is not a number.") from None
    if kind in ("date", "datetime"):
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            raise AlertConfigError(f"'{value}' is not a date (YYYY-MM-DD).") from None
    if kind == "bool":
        return 1 if str(value).lower() in ("1", "true", "yes") else 0
    return str(value)


def build_query(spec: AlertSpec, table: TableRef, columns: dict[str, ColumnInfo], *, today: date,
                max_rows: int = 10_000) -> BuiltQuery:
    validate(spec, columns)
    d = dialect_for(spec.engine)
    params: dict[str, Any] = {}

    def ph(name: str, value: Any, kind: str) -> str:
        params[name] = value
        return d.placeholder(name, kind)

    date_kind = columns[spec.date_column].kind
    date_sql = d.as_date(d.quote(spec.date_column), date_kind)
    p_start, p_end = period_bounds(spec.period, today)
    b_start, b_end, avg_days = baseline_bounds(spec.compare_to, p_start, p_end)

    ps, pe = ph("p_start", p_start, "date"), ph("p_end", p_end, "date")
    bs, be = ph("b_start", b_start, "date"), ph("b_end", b_end, "date")
    lo, hi = ph("w_start", min(p_start, b_start), "date"), ph("w_end", max(p_end, b_end), "date")
    in_period = f"{date_sql} >= {ps} AND {date_sql} < {pe}"
    in_base = f"{date_sql} >= {bs} AND {date_sql} < {be}"

    def value(cond: str) -> str:
        if spec.value_kind == "count":
            return d.agg("count", None, cond)
        if spec.value_kind == "ratio":
            return d.safe_div(d.agg(spec.aggregation, d.quote(spec.metric), cond),
                              d.agg(spec.denominator_aggregation, d.quote(spec.denominator), cond))
        return d.agg(spec.aggregation, d.quote(spec.metric), cond)

    group_cols = list(spec.group_by)
    if spec.currency_column and spec.currency_column not in group_cols:
        group_cols.append(spec.currency_column)
    aliases = [f"g_{i}" for i in range(len(group_cols))]
    select = [f"{d.quote(c)} AS {a}" for c, a in zip(group_cols, aliases)]
    select += [f"{value(in_period)} AS current_value", f"{value(in_base)} AS baseline_value"]

    where = [f"{date_sql} >= {lo}", f"{date_sql} < {hi}"]
    for c in group_cols:
        where.append(d.text_not_empty(d.quote(c)) if columns[c].kind == "text" else f"{d.quote(c)} IS NOT NULL")
    for i, f in enumerate(spec.filters):
        col, op = f["column"], f.get("op", "eq")
        kind = columns[col].kind
        cs = d.quote(col)
        if op in ("empty", "not_empty"):
            where.append(d.is_empty(cs, negate=(op == "not_empty")))
            continue
        raw = f.get("value")
        if op in ("in", "not_in"):
            items = raw if isinstance(raw, list) else [x.strip() for x in str(raw or "").split(",") if x.strip()]
            if not items:
                raise AlertConfigError(f"The filter on {col} needs at least one value.")
            vals = [_coerce(x, "number" if kind == "number" else "text") for x in items]
            where.append(d.in_list(cs, ph(f"f_{i}", vals, "list_number" if kind == "number" else "list_text"),
                                   negate=(op == "not_in")))
            continue
        if op == "contains":
            where.append(d.contains(cs, ph(f"f_{i}", f"%{raw}%", "text")))
            continue
        if raw in (None, ""):
            raise AlertConfigError(f"The filter on {col} needs a value.")
        sym = {"eq": "=", "neq": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[op]
        vkind = "date" if kind in ("date", "datetime") else ("number" if kind == "number" else "text")
        where.append(f"{cs} {sym} {ph(f'f_{i}', _coerce(raw, vkind), vkind)}")

    having = ""
    if spec.min_volume_column and spec.min_volume is not None:
        having = (f"\nHAVING {d.agg('sum', d.quote(spec.min_volume_column), in_period)} >= "
                  f"{ph('min_volume', float(spec.min_volume), 'number')}")

    source = d.from_clause(d.table(table.database, table.name), table.needs_final)
    sql = (f"SELECT {', '.join(select)}\nFROM {source}\nWHERE " + "\n  AND ".join(where)
           + (f"\nGROUP BY {', '.join(aliases)}" if aliases else "")
           + having
           + (f"\nORDER BY current_value DESC\nLIMIT {int(max_rows)}" if aliases else ""))
    return BuiltQuery(sql=sql, params=params, group_aliases=aliases, period=(p_start, p_end),
                      baseline=(b_start, b_end), avg_days=avg_days)


# ── Verdicts ─────────────────────────────────────────────────────────────────

def evaluate_row(condition: str, threshold: float, current: float, baseline: float) -> tuple[bool, Optional[float]]:
    """(fired, change %). Same rules as the pre-P230 worker."""
    change = ((current - baseline) / baseline * 100) if baseline > 0 else None
    if condition == "threshold_drop":
        return (change is not None and change <= threshold), change
    if condition == "threshold_rise":
        return (change is not None and change >= threshold), change
    if condition == "absolute_above":
        return current > threshold, change
    if condition == "absolute_below":
        return current < threshold, change
    if condition == "zero_check":
        return current == 0 and baseline > 0, change
    return False, change


def _num(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def judge(spec: AlertSpec, built: BuiltQuery, rows: list[dict]) -> list[dict]:
    """One result per group, newest verdicts first (fired groups on top)."""
    out = []
    scale = 1.0
    if built.avg_days and (spec.value_kind == "count" or
                           (spec.value_kind == "column" and spec.aggregation in ADDITIVE)):
        # An N-day average, scaled to the checked period's length.
        period_days = max(1, (built.period[1] - built.period[0]).days)
        scale = period_days / built.avg_days
    # A ratio with a zero denominator, or an average/min/max over no rows, has
    # no value: it must not read as 0 and fire "falls below". Sums and counts
    # over no rows really are 0 (that is what "drops to zero" checks).
    no_value_is_zero = spec.value_kind == "count" or (spec.value_kind == "column" and spec.aggregation in ADDITIVE)
    for r in rows:
        group = GROUP_SEPARATOR.join(str(r.get(a)) for a in built.group_aliases) or "Total"
        if r.get("current_value") is None and not no_value_is_zero:
            continue
        current = _num(r.get("current_value"))
        baseline = _num(r.get("baseline_value")) * scale
        if spec.min_baseline and baseline < spec.min_baseline and spec.condition in ("threshold_drop", "threshold_rise"):
            continue
        fired, change = evaluate_row(spec.condition, spec.threshold, current, baseline)
        out.append({"group": group, "current_value": round(current, 6), "baseline": round(baseline, 6),
                    "change_pct": round(change, 1) if change is not None else None, "fired": bool(fired)})
    out.sort(key=lambda x: (not x["fired"],))
    return out


# ── Running one alert ────────────────────────────────────────────────────────

@dataclass
class Evaluation:
    status: str                      # ok | no_data | error
    rows: list[dict] = field(default_factory=list)
    sql: str = ""
    params: dict = field(default_factory=dict)
    engine: str = "postgres"
    elapsed_ms: int = 0
    rows_checked: int = 0
    error: Optional[str] = None
    period: Optional[tuple[date, date]] = None

    @property
    def fired_rows(self) -> list[dict]:
        return [r for r in self.rows if r["fired"]]

    def as_dict(self, limit: int = 200) -> dict:
        return {
            "status": self.status, "engine": self.engine, "sql": self.sql,
            "rows_checked": self.rows_checked, "elapsed_ms": self.elapsed_ms, "error": self.error,
            "fired": bool(self.fired_rows), "fired_count": len(self.fired_rows),
            "rows": self.rows[:limit],
            "period": [self.period[0].isoformat(), self.period[1].isoformat()] if self.period else None,
        }


def resolve_table(driver: QueryDriver, spec: AlertSpec) -> TableRef:
    if not valid_ident(spec.table) or (spec.database and not valid_ident(spec.database)):
        raise AlertConfigError(f"Invalid table name '{spec.table}'.")
    return driver.locate(spec.table, spec.database)


def evaluate_alert(alert: dict, *, today: Optional[date] = None, pg_cursor=None, timeout_s: int = 30,
                   max_rows: int = 10_000,
                   driver_factory: Optional[Callable[..., QueryDriver]] = None) -> Evaluation:
    """Evaluate an alert (saved or not). Never sends or records anything."""
    started = time.monotonic()
    spec = spec_from_alert(alert)
    ev = Evaluation(status="error", engine=spec.engine)
    try:
        if spec.source_kind == "plugin_query":
            from .alert_queries import evaluate_plugin_query
            return evaluate_plugin_query(alert, spec, today=today or date.today(), pg_cursor=pg_cursor,
                                         timeout_s=timeout_s, max_rows=max_rows, driver_factory=driver_factory)
        factory = driver_factory or get_driver
        driver = factory(spec.engine, connection_id=spec.connection_id, pg_cursor=pg_cursor)
        table = resolve_table(driver, spec)
        cols = {c.name: c for c in driver.columns(table)}
        if not cols:
            raise AlertConfigError(f"No columns found for {spec.table}.")
        built = build_query(spec, table, cols, today=today or date.today(), max_rows=max_rows)
        ev.sql, ev.params, ev.period = built.sql, _show_params(built.params), built.period
        rows = driver.run(built.sql, built.params, timeout_s=timeout_s, max_rows=max_rows)
        ev.rows_checked = len(rows)
        ev.rows = judge(spec, built, rows)
        ev.status = "ok" if rows else "no_data"
    except (AlertConfigError, ConnectionMissing, QueryError) as e:
        ev.error = str(e)
    except Exception as e:  # noqa: BLE001 — never let one alert take the run down
        ev.error = f"{e.__class__.__name__}: {str(e)[:200]}"
    ev.elapsed_ms = int((time.monotonic() - started) * 1000)
    return ev


def _show_params(params: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in params.items()}


__all__ = [
    "AlertConfigError", "AlertSpec", "BuiltQuery", "COMPARISONS", "CONDITIONS", "Evaluation", "FILTER_OPS",
    "PERIODS", "VALUE_KINDS", "baseline_bounds", "build_query", "evaluate_alert", "evaluate_row", "judge",
    "period_bounds", "spec_from_alert", "validate",
]
