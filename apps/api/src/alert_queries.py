"""
P230 §5: ready-made alerts a plugin ships in `alerts.yaml`.

Some alerts need logic a column mapping can't express safely: currency
conversion, excluding data the plugin must never expose, the plugin's own
definitions. A plugin can ship named, read-only queries, like insights.yaml:

    queries:
      - id: zero_ers
        label: Accounts paid 0% revenue share
        description: Account-months with net revenue but no RS commission.
        db: clickhouse                  # postgres (default) | clickhouse | mysql
        value_label: RS commission ÷ net revenue
        params:
          min_net_revenue_usd: {type: number, default: 100, label: Minimum net revenue (USD)}
        default_condition: {type: absolute_below, threshold: 0.001}
        default_period: last_month
        sql: |
          SELECT account AS group_name, rs / net AS current_value
          FROM …
          WHERE day >= {period_start} AND day < {period_end}
            AND net >= {min_net_revenue_usd}

The query returns `group_name`, `current_value` and optionally
`baseline_value` (it can use {baseline_start} / {baseline_end}). The alert's
period and comparison fill {period_start}, {period_end}, {baseline_start}
and {baseline_end}; the user sets the declared params, the condition, the
schedule and the channels, never the SQL. Every placeholder is a bound,
typed parameter. Postgres queries run as the nousviz_query role, like
insights; every engine runs them read-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from .query_drivers import DRIVERS, valid_ident

PLUGINS_INSTALLED = Path(__file__).resolve().parents[3] / "plugins" / "installed"
PARAM_TYPES = ("number", "text", "enum")
BUILTINS = ("period_start", "period_end", "baseline_start", "baseline_end")
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_cache: dict[str, tuple[float, list["AlertQuery"]]] = {}


@dataclass
class AlertQuery:
    plugin_id: str
    id: str
    label: str
    description: str
    engine: str
    sql: str
    params: dict = field(default_factory=dict)
    default_condition: dict = field(default_factory=dict)
    default_period: str = "yesterday"
    value_label: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {"id": f"query:{self.plugin_id}:{self.id}", "query_id": self.id, "plugin_id": self.plugin_id,
                "label": self.label, "description": self.description, "engine": self.engine,
                "params": self.params, "default_condition": self.default_condition,
                "default_period": self.default_period, "value_label": self.value_label, "sql": self.sql,
                "error": self.error}


def _validate(q: AlertQuery) -> Optional[str]:
    if not valid_ident(q.id):
        return "id must be a plain identifier"
    if q.engine not in DRIVERS:
        return f"no driver for db '{q.engine}'"
    body = q.sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^(select|with)\b", body):
        return "sql must be a single SELECT (or WITH … SELECT)"
    if ";" in body:
        return "sql must be one statement"
    for name, p in q.params.items():
        if not valid_ident(name) or name in BUILTINS:
            return f"invalid param name '{name}'"
        if not isinstance(p, dict) or p.get("type", "number") not in PARAM_TYPES:
            return f"param '{name}' needs a type: number, text or enum"
        if p.get("type") == "enum" and not p.get("options"):
            return f"enum param '{name}' needs options"
    for name in _PLACEHOLDER.findall(body):
        if name not in BUILTINS and name not in q.params:
            return f"placeholder {{{name}}} is not a declared param"
    return None


def load_plugin_queries(plugin_dir: Path) -> list[AlertQuery]:
    path = plugin_dir / "alerts.yaml"
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    hit = _cache.get(str(path))
    if hit and hit[0] == mtime:
        return hit[1]
    out: list[AlertQuery] = []
    try:
        cfg = yaml.safe_load(path.read_text()) or {}
    except Exception as e:  # noqa: BLE001
        out = [AlertQuery(plugin_dir.name, "invalid", "alerts.yaml", "", "postgres", "", error=f"YAML: {e}")]
        _cache[str(path)] = (mtime, out)
        return out
    for spec in cfg.get("queries", []) or []:
        q = AlertQuery(
            plugin_id=plugin_dir.name, id=str(spec.get("id", "")), label=str(spec.get("label") or spec.get("id")),
            description=str(spec.get("description", "")), engine=str(spec.get("db") or "postgres").lower(),
            sql=str(spec.get("sql", "")), params=dict(spec.get("params") or {}),
            default_condition=dict(spec.get("default_condition") or {}),
            default_period=str(spec.get("default_period") or "yesterday"),
            value_label=str(spec.get("value_label", "")),
        )
        q.error = _validate(q)
        out.append(q)
    _cache[str(path)] = (mtime, out)
    return out


def list_queries(root: Path = PLUGINS_INSTALLED) -> list[AlertQuery]:
    out: list[AlertQuery] = []
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        out.extend(load_plugin_queries(d))
    return out


def find_query(plugin_id: str, query_id: str, root: Path = PLUGINS_INSTALLED) -> Optional[AlertQuery]:
    d = root / plugin_id
    if not d.is_dir():
        return None
    for q in load_plugin_queries(d):
        if q.id == query_id:
            return q
    return None


def render(q: AlertQuery, dialect, values: dict, bounds: dict[str, date]) -> tuple[str, dict]:
    """Swap {name} placeholders for typed, bound parameters."""
    params: dict[str, Any] = {}

    def sub(m: re.Match) -> str:
        name = m.group(1)
        if name in BUILTINS:
            params[name] = bounds[name]
            return dialect.placeholder(name, "date")
        p = q.params[name]
        typ = p.get("type", "number")
        raw = values.get(name, p.get("default"))
        if raw is None or raw == "":
            raise ValueError(f"Set '{p.get('label') or name}'.")
        if typ == "number":
            try:
                params[name] = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"'{p.get('label') or name}' must be a number.") from None
            return dialect.placeholder(name, "number")
        if typ == "enum" and str(raw) not in [str(o) for o in p.get("options", [])]:
            raise ValueError(f"'{p.get('label') or name}' must be one of {p.get('options')}.")
        params[name] = str(raw)
        return dialect.placeholder(name, "text")

    sql = _PLACEHOLDER.sub(sub, q.sql.strip().rstrip(";"))
    return sql, params


def evaluate_plugin_query(alert: dict, spec, *, today: date, pg_cursor=None, timeout_s: int = 30,
                          max_rows: int = 10_000, driver_factory=None):
    """Run a ready-made query and judge its rows like any other alert."""
    import time

    from .alert_engine import AlertConfigError, Evaluation, baseline_bounds, evaluate_row, period_bounds
    from .query_drivers import ConnectionMissing, QueryError, get_driver

    started = time.monotonic()
    ev = Evaluation(status="error", engine=spec.engine)
    try:
        q = find_query(spec.plugin_id or "", spec.query_id or "")
        if q is None:
            raise AlertConfigError("This ready-made alert is no longer available (plugin removed or updated).")
        if q.error:
            raise AlertConfigError(f"The plugin's alerts.yaml is invalid: {q.error}")
        ev.engine = q.engine
        p_start, p_end = period_bounds(spec.period, today)
        b_start, b_end, _ = baseline_bounds(spec.compare_to, p_start, p_end)
        driver = (driver_factory or get_driver)(q.engine, connection_id=None, pg_cursor=pg_cursor)
        try:
            sql, params = render(q, driver.dialect, spec.query_params,
                                 {"period_start": p_start, "period_end": p_end,
                                  "baseline_start": b_start, "baseline_end": b_end})
        except ValueError as e:
            raise AlertConfigError(str(e)) from None
        ev.sql, ev.period = sql, (p_start, p_end)
        ev.params = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in params.items()}
        rows = driver.run(sql, params, timeout_s=timeout_s, max_rows=max_rows, sandbox_role=True)
        ev.rows_checked = len(rows)
        if rows and "current_value" not in rows[0]:
            raise AlertConfigError("The query must return a column named current_value.")
        out = []
        for r in rows:
            cur = float(r.get("current_value") or 0)
            base = float(r.get("baseline_value") or 0)
            fired, change = evaluate_row(spec.condition, spec.threshold, cur, base)
            out.append({"group": str(r.get("group_name", "Total")), "current_value": round(cur, 6),
                        "baseline": round(base, 6), "change_pct": round(change, 1) if change is not None else None,
                        "fired": bool(fired)})
        out.sort(key=lambda x: (not x["fired"],))
        ev.rows = out
        ev.status = "ok" if rows else "no_data"
    except (AlertConfigError, ConnectionMissing, QueryError) as e:
        ev.error = str(e)
    except Exception as e:  # noqa: BLE001
        ev.error = f"{e.__class__.__name__}: {str(e)[:200]}"
    ev.elapsed_ms = int((time.monotonic() - started) * 1000)
    return ev


__all__ = ["AlertQuery", "evaluate_plugin_query", "find_query", "list_queries", "load_plugin_queries", "render"]
