"""Tests for B272 (v0.9.11.18) — system-health diagnostic engine.

For each of the 12 rules: one fixture proving it fires + one boundary
fixture proving it doesn't. Plus a "clean install" snapshot test
asserting zero findings (no false positives).

Each fixture is a minimal snapshot dict carrying ONLY the fields the
rule under test needs. The rules are written defensively (`.get()`
with defaults) so missing keys mean "no signal", not exception.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TS = "2026-05-04T10:30:00+00:00"


def _empty_snap() -> dict:
    """A snapshot with every collection empty / nominal — should
    produce zero findings."""
    return {
        "collected_at": TS,
        "server": {
            "memory": {"total_mb": 4096, "used_mb": 2048, "free_mb": 2048,
                       "available_mb": 2048, "buff_cache_mb": 0},
            "swap": {"total_mb": 2048, "used_mb": 0, "free_mb": 2048},
            "disk_root": {"path": "/", "total_gb": 100, "used_gb": 30,
                          "free_gb": 70, "used_pct": 30.0},
            "load": {"load_1m": 0.5, "load_5m": 0.5, "load_15m": 0.5},
            "uptime_seconds": 86400,
            "cpu": {"cpu_count": 4, "cpu_model": "test"},
        },
        "postgres": {
            "db_size_mb": 100,
            "cache_hit_pct": 99.8,
            "active_connections": 5,
            "idle_connections": 5,
            "max_connections": 100,
            "pg_stat_statements_installed": True,
        },
        "tables": [],
        "plugins": [],
        "syncs": [],
        "indexes_largest": [],
    }


# ── Empty snapshot: no false positives ──────────────────────────────


def test_clean_install_returns_zero_findings():
    from apps.api.src.services.system_diagnostics import evaluate_diagnostics
    findings = evaluate_diagnostics(_empty_snap())
    assert findings == [], f"clean install should return zero findings, got {findings}"


# ── sync_overlapping_schedule ──────────────────────────────────────


def test_sync_overlap_warn_at_70pct():
    from apps.api.src.services.system_diagnostics import rule_sync_overlapping_schedule
    snap = _empty_snap()
    snap["syncs"] = [{
        "plugin_id": "example-customers",
        "schedule_cron": "*/15 * * * *",
        "schedule_interval_seconds": 900,
        "runs_24h": 96,
        "errors_24h": 0,
        "avg_duration_ms": 630_000,
        "max_duration_ms": 800_000,
        "cpu_load_pct_estimate": 70.0,
    }]
    out = rule_sync_overlapping_schedule(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"
    assert "example-customers" in out[0]["title"]


def test_sync_overlap_critical_at_95pct():
    from apps.api.src.services.system_diagnostics import rule_sync_overlapping_schedule
    snap = _empty_snap()
    snap["syncs"] = [{
        "plugin_id": "slow-sync",
        "schedule_cron": "*/5 * * * *",
        "schedule_interval_seconds": 300,
        "runs_24h": 288,
        "errors_24h": 0,
        "avg_duration_ms": 285_000,
        "max_duration_ms": 290_000,
        "cpu_load_pct_estimate": 95.0,
    }]
    out = rule_sync_overlapping_schedule(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


def test_sync_overlap_below_threshold_does_not_fire():
    from apps.api.src.services.system_diagnostics import rule_sync_overlapping_schedule
    snap = _empty_snap()
    snap["syncs"] = [{
        "plugin_id": "fast-sync",
        "schedule_cron": "0 * * * *",
        "schedule_interval_seconds": 3600,
        "runs_24h": 24,
        "errors_24h": 0,
        "avg_duration_ms": 30_000,
        "max_duration_ms": 30_000,
        "cpu_load_pct_estimate": 30.0,
    }]
    assert rule_sync_overlapping_schedule(snap, TS) == []


# ── sync_failing_consistently ──────────────────────────────────────


def test_failing_consistently_fires_when_4_of_4_errors():
    from apps.api.src.services.system_diagnostics import rule_sync_failing_consistently
    snap = _empty_snap()
    snap["syncs"] = [
        {"plugin_id": "quickbooks", "runs_24h": 24, "errors_24h": 24,
         "schedule_cron": "0 * * * *", "schedule_interval_seconds": 3600,
         "avg_duration_ms": 1000, "max_duration_ms": 1000, "cpu_load_pct_estimate": 0},
    ]
    out = rule_sync_failing_consistently(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


def test_failing_consistently_skips_when_few_runs():
    """min runs gate prevents firing on plugins with only 1-3 runs."""
    from apps.api.src.services.system_diagnostics import rule_sync_failing_consistently
    snap = _empty_snap()
    snap["syncs"] = [{
        "plugin_id": "rare-sync", "runs_24h": 2, "errors_24h": 2,
        "schedule_cron": "0 0 * * *", "schedule_interval_seconds": 86400,
        "avg_duration_ms": 1000, "max_duration_ms": 1000, "cpu_load_pct_estimate": 0,
    }]
    assert rule_sync_failing_consistently(snap, TS) == []


def test_failing_consistently_skips_when_below_50pct():
    from apps.api.src.services.system_diagnostics import rule_sync_failing_consistently
    snap = _empty_snap()
    snap["syncs"] = [{
        "plugin_id": "flaky", "runs_24h": 24, "errors_24h": 5,  # 21%
        "schedule_cron": "0 * * * *", "schedule_interval_seconds": 3600,
        "avg_duration_ms": 1000, "max_duration_ms": 1000, "cpu_load_pct_estimate": 0,
    }]
    assert rule_sync_failing_consistently(snap, TS) == []


# ── total_sync_cpu_high ─────────────────────────────────────────────


def test_total_sync_cpu_critical_at_120():
    from apps.api.src.services.system_diagnostics import rule_total_sync_cpu_high
    snap = _empty_snap()
    snap["syncs"] = [
        {"plugin_id": "worst-offender", "cpu_load_pct_estimate": 70, "runs_24h": 0,
         "errors_24h": 0, "schedule_cron": "x", "schedule_interval_seconds": 0,
         "avg_duration_ms": 0, "max_duration_ms": 0},
        {"plugin_id": "second", "cpu_load_pct_estimate": 50, "runs_24h": 0,
         "errors_24h": 0, "schedule_cron": "x", "schedule_interval_seconds": 0,
         "avg_duration_ms": 0, "max_duration_ms": 0},
    ]
    out = rule_total_sync_cpu_high(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"  # sum 120 > 100
    # v0.9.11.19.3: action targets the worst offender's plugin settings,
    # not back to /system/resources where the operator already is.
    action = out[0]["action"]
    assert action["type"] == "external"
    assert action["url"] == "/plugin/worst-offender/settings"
    assert action["url"] != "/system/resources"


def test_total_sync_cpu_no_fire_at_30():
    from apps.api.src.services.system_diagnostics import rule_total_sync_cpu_high
    snap = _empty_snap()
    snap["syncs"] = [
        {"plugin_id": "a", "cpu_load_pct_estimate": 15, "runs_24h": 0,
         "errors_24h": 0, "schedule_cron": "x", "schedule_interval_seconds": 0,
         "avg_duration_ms": 0, "max_duration_ms": 0},
        {"plugin_id": "b", "cpu_load_pct_estimate": 15, "runs_24h": 0,
         "errors_24h": 0, "schedule_cron": "x", "schedule_interval_seconds": 0,
         "avg_duration_ms": 0, "max_duration_ms": 0},
    ]
    assert rule_total_sync_cpu_high(snap, TS) == []


# ── index_bloat ────────────────────────────────────────────────────


def test_index_bloat_warn_at_158pct_on_large_table():
    """Production audit case: gsc_search_analytics with 158% bloat."""
    from apps.api.src.services.system_diagnostics import rule_index_bloat
    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "gsc_search_analytics", "plugin": "gsc",
        "total_size_mb": 250, "data_mb": 100, "index_mb": 158,
        "rows": 1_000_000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 0, "idx_scan_count": 0, "seq_scan_pct": 0,
    }]
    out = rule_index_bloat(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"


def test_index_bloat_skips_small_tables():
    from apps.api.src.services.system_diagnostics import rule_index_bloat
    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "tiny", "plugin": None,
        "total_size_mb": 10, "data_mb": 4, "index_mb": 6,
        "rows": 1000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 0, "idx_scan_count": 0, "seq_scan_pct": 0,
    }]
    assert rule_index_bloat(snap, TS) == []


# ── unused_index ───────────────────────────────────────────────────


def test_unused_index_collects_all_unscanned():
    from apps.api.src.services.system_diagnostics import rule_unused_index
    snap = _empty_snap()
    snap["indexes_largest"] = [
        {"schema": "public", "table": "users", "name": "idx_users_unused1",
         "size_mb": 5.0, "scans_lifetime": 0, "tuples_read": 0,
         "is_primary": False, "is_unique": False},
        {"schema": "public", "table": "events", "name": "idx_events_unused2",
         "size_mb": 12.0, "scans_lifetime": 0, "tuples_read": 0,
         "is_primary": False, "is_unique": False},
        {"schema": "public", "table": "users", "name": "idx_users_active",
         "size_mb": 4.0, "scans_lifetime": 5_000, "tuples_read": 1000,
         "is_primary": False, "is_unique": False},
    ]
    out = rule_unused_index(snap, TS)
    assert len(out) == 1
    affected_names = [a["name"] for a in out[0]["affected"]]
    assert "public.idx_users_unused1" in affected_names
    assert "public.idx_events_unused2" in affected_names
    assert "public.idx_users_active" not in affected_names


def test_unused_index_skips_tiny_indexes():
    """Indexes < 1 MB don't count — overhead is negligible and the
    drop list shouldn't bloat with chaff."""
    from apps.api.src.services.system_diagnostics import rule_unused_index
    snap = _empty_snap()
    snap["indexes_largest"] = [
        {"schema": "public", "table": "x", "name": "idx_tiny",
         "size_mb": 0.1, "scans_lifetime": 0, "tuples_read": 0,
         "is_primary": False, "is_unique": False},
    ]
    assert rule_unused_index(snap, TS) == []


def test_unused_index_excludes_primary_keys():
    """v0.9.11.19.3: a primary key with 0 scans must NOT be flagged.
    PKs are load-bearing for INSERT / UPDATE / DELETE + foreign-key
    lookups regardless of pg_stat_user_indexes.idx_scan count."""
    from apps.api.src.services.system_diagnostics import rule_unused_index
    snap = _empty_snap()
    snap["indexes_largest"] = [
        {"schema": "public", "table": "auth_audit", "name": "auth_audit_pkey",
         "size_mb": 5.0, "scans_lifetime": 0, "tuples_read": 0,
         "is_primary": True, "is_unique": True},
    ]
    assert rule_unused_index(snap, TS) == []


def test_unused_index_excludes_unique_indexes():
    """v0.9.11.19.3: unique indexes enforce a constraint, so 0 scans
    doesn't mean droppable. Only flagged if NOT primary AND NOT unique."""
    from apps.api.src.services.system_diagnostics import rule_unused_index
    snap = _empty_snap()
    snap["indexes_largest"] = [
        {"schema": "public", "table": "users", "name": "users_email_unique",
         "size_mb": 5.0, "scans_lifetime": 0, "tuples_read": 0,
         "is_primary": False, "is_unique": True},
    ]
    assert rule_unused_index(snap, TS) == []


# ── sequential_scan_heavy ──────────────────────────────────────────


def test_sequential_scan_fires_at_30pct_on_big_table(monkeypatch):
    from apps.api.src.services import system_diagnostics as diag
    # v0.9.11.19.2: rule pulls pg_indexes inline. Mock the helper so
    # the test stays a pure unit test (no DB).
    monkeypatch.setattr(
        diag,
        "_list_table_indexes",
        lambda schema, name: ["auth_audit_user_idx", "auth_audit_occurred_at_idx"],
    )

    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "auth_audit", "plugin": None,
        "total_size_mb": 50, "data_mb": 30, "index_mb": 20,
        "rows": 1_140_000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 100, "idx_scan_count": 230, "seq_scan_pct": 30.0,
    }]
    out = diag.rule_sequential_scan_heavy(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"
    # New v0.9.11.19.2 behaviour: existing indexes appear in evidence
    # AND in the affected list as type="index" entries.
    assert "auth_audit_user_idx" in out[0]["evidence"]
    assert "auth_audit_occurred_at_idx" in out[0]["evidence"]
    index_affected = [a for a in out[0]["affected"] if a["type"] == "index"]
    assert len(index_affected) == 2
    # No more pg_stat_statements cross-reference in the recommendation
    # (overcoupling — the rule should stand alone now).
    assert "pg_stat_statements" not in out[0]["recommendation"]
    assert "EXPLAIN" in out[0]["recommendation"]


def test_sequential_scan_small_table_qualifier_softens_evidence(monkeypatch):
    """v0.9.11.19.2: a 19MB / 53k-row hot table fires the rule but the
    evidence text adds an "informational rather than urgent" caveat —
    the planner often correctly chooses seq scan at this size."""
    from apps.api.src.services import system_diagnostics as diag
    monkeypatch.setattr(diag, "_list_table_indexes", lambda s, n: [])

    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "auth_audit", "plugin": None,
        "total_size_mb": 19, "data_mb": 12, "index_mb": 7,
        "rows": 53_000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 7064, "idx_scan_count": 19451, "seq_scan_pct": 27.0,
    }]
    out = diag.rule_sequential_scan_heavy(snap, TS)
    assert len(out) == 1
    assert "informational rather than urgent" in out[0]["evidence"]


def test_sequential_scan_large_table_no_qualifier(monkeypatch):
    """v0.9.11.19.2: a 200MB+ hot table does NOT get the qualifier —
    seq scans on large tables are more likely to be a real problem."""
    from apps.api.src.services import system_diagnostics as diag
    monkeypatch.setattr(diag, "_list_table_indexes", lambda s, n: [])

    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "big_table", "plugin": None,
        "total_size_mb": 250, "data_mb": 200, "index_mb": 50,
        "rows": 5_000_000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 100, "idx_scan_count": 230, "seq_scan_pct": 30.0,
    }]
    out = diag.rule_sequential_scan_heavy(snap, TS)
    assert "informational" not in out[0]["evidence"]


def test_sequential_scan_skips_small_tables(monkeypatch):
    from apps.api.src.services import system_diagnostics as diag
    monkeypatch.setattr(diag, "_list_table_indexes", lambda s, n: [])
    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "small", "plugin": None,
        "total_size_mb": 5, "data_mb": 4, "index_mb": 1,
        "rows": 500, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": TS, "last_analyze": TS,
        "seq_scan_count": 1000, "idx_scan_count": 0, "seq_scan_pct": 100.0,
    }]
    assert diag.rule_sequential_scan_heavy(snap, TS) == []


# ── vacuum_behind ──────────────────────────────────────────────────


def test_vacuum_behind_fires_at_8_days_old():
    from apps.api.src.services.system_diagnostics import rule_vacuum_behind
    snap = _empty_snap()
    eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    snap["tables"] = [{
        "schema": "public", "name": "big_table", "plugin": None,
        "total_size_mb": 500, "data_mb": 400, "index_mb": 100,
        "rows": 10_000_000, "dead_rows": 100_000, "dead_pct": 1.0,
        "last_vacuum": eight_days_ago, "last_analyze": eight_days_ago,
        "seq_scan_count": 0, "idx_scan_count": 100, "seq_scan_pct": 0,
    }]
    out = rule_vacuum_behind(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"


def test_vacuum_behind_skips_recent():
    from apps.api.src.services.system_diagnostics import rule_vacuum_behind
    snap = _empty_snap()
    snap["tables"] = [{
        "schema": "public", "name": "big_table", "plugin": None,
        "total_size_mb": 500, "data_mb": 400, "index_mb": 100,
        "rows": 10_000_000, "dead_rows": 100_000, "dead_pct": 1.0,
        "last_vacuum": TS, "last_analyze": TS,  # today
        "seq_scan_count": 0, "idx_scan_count": 100, "seq_scan_pct": 0,
    }]
    assert rule_vacuum_behind(snap, TS) == []


def test_vacuum_behind_skips_small_tables():
    from apps.api.src.services.system_diagnostics import rule_vacuum_behind
    snap = _empty_snap()
    eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    snap["tables"] = [{
        "schema": "public", "name": "small", "plugin": None,
        "total_size_mb": 50, "data_mb": 40, "index_mb": 10,
        "rows": 1_000, "dead_rows": 0, "dead_pct": 0,
        "last_vacuum": eight_days_ago, "last_analyze": eight_days_ago,
        "seq_scan_count": 0, "idx_scan_count": 100, "seq_scan_pct": 0,
    }]
    assert rule_vacuum_behind(snap, TS) == []


# ── cache_hit_low ──────────────────────────────────────────────────


def test_cache_hit_low_critical_below_95():
    from apps.api.src.services.system_diagnostics import rule_cache_hit_low
    snap = _empty_snap()
    snap["postgres"]["cache_hit_pct"] = 90.0
    out = rule_cache_hit_low(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


def test_cache_hit_low_warn_at_98():
    from apps.api.src.services.system_diagnostics import rule_cache_hit_low
    snap = _empty_snap()
    snap["postgres"]["cache_hit_pct"] = 98.0
    out = rule_cache_hit_low(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"


def test_cache_hit_low_skips_healthy():
    from apps.api.src.services.system_diagnostics import rule_cache_hit_low
    snap = _empty_snap()
    snap["postgres"]["cache_hit_pct"] = 99.7
    assert rule_cache_hit_low(snap, TS) == []


# ── disk_pressure ──────────────────────────────────────────────────


def test_disk_pressure_critical_at_95pct():
    from apps.api.src.services.system_diagnostics import rule_disk_pressure
    snap = _empty_snap()
    snap["server"]["disk_root"] = {
        "path": "/", "total_gb": 100, "used_gb": 95, "free_gb": 5, "used_pct": 95.0,
    }
    out = rule_disk_pressure(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


def test_disk_pressure_skips_normal():
    from apps.api.src.services.system_diagnostics import rule_disk_pressure
    snap = _empty_snap()
    snap["server"]["disk_root"] = {
        "path": "/", "total_gb": 100, "used_gb": 60, "free_gb": 40, "used_pct": 60.0,
    }
    assert rule_disk_pressure(snap, TS) == []


# ── no_swap_with_low_memory ────────────────────────────────────────


def test_no_swap_low_memory_fires_when_both_conditions_match():
    from apps.api.src.services.system_diagnostics import rule_no_swap_with_low_memory
    snap = _empty_snap()
    snap["server"]["swap"] = {"total_mb": 0, "used_mb": 0, "free_mb": 0}
    snap["server"]["memory"] = {
        "total_mb": 4096, "used_mb": 3700, "free_mb": 200,
        "available_mb": 200, "buff_cache_mb": 0,
    }
    out = rule_no_swap_with_low_memory(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "warn"


def test_no_swap_skips_when_swap_present():
    from apps.api.src.services.system_diagnostics import rule_no_swap_with_low_memory
    snap = _empty_snap()
    snap["server"]["swap"] = {"total_mb": 2048, "used_mb": 0, "free_mb": 2048}
    snap["server"]["memory"]["free_mb"] = 100
    assert rule_no_swap_with_low_memory(snap, TS) == []


def test_no_swap_skips_when_memory_plentiful():
    from apps.api.src.services.system_diagnostics import rule_no_swap_with_low_memory
    snap = _empty_snap()
    snap["server"]["swap"] = {"total_mb": 0, "used_mb": 0, "free_mb": 0}
    snap["server"]["memory"]["free_mb"] = 2000
    assert rule_no_swap_with_low_memory(snap, TS) == []


# ── pg_stat_statements_missing ─────────────────────────────────────


def test_pg_stat_statements_missing_fires_when_false():
    from apps.api.src.services.system_diagnostics import rule_pg_stat_statements_missing
    snap = _empty_snap()
    snap["postgres"]["pg_stat_statements_installed"] = False
    out = rule_pg_stat_statements_missing(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "info"


def test_pg_stat_statements_skips_when_installed():
    from apps.api.src.services.system_diagnostics import rule_pg_stat_statements_missing
    snap = _empty_snap()
    snap["postgres"]["pg_stat_statements_installed"] = True
    assert rule_pg_stat_statements_missing(snap, TS) == []


# ── connection_pool_pressure ───────────────────────────────────────


def test_connection_pressure_critical_above_95pct():
    from apps.api.src.services.system_diagnostics import rule_connection_pool_pressure
    snap = _empty_snap()
    snap["postgres"]["active_connections"] = 60
    snap["postgres"]["idle_connections"] = 38
    snap["postgres"]["max_connections"] = 100  # 98% utilised
    out = rule_connection_pool_pressure(snap, TS)
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


def test_connection_pressure_skips_normal():
    from apps.api.src.services.system_diagnostics import rule_connection_pool_pressure
    snap = _empty_snap()
    snap["postgres"]["active_connections"] = 5
    snap["postgres"]["idle_connections"] = 10
    snap["postgres"]["max_connections"] = 100  # 15% utilised
    assert rule_connection_pool_pressure(snap, TS) == []


# ── Top-level evaluator ────────────────────────────────────────────


def test_evaluate_diagnostics_sorts_by_severity():
    """Findings must come back critical → warn → info."""
    from apps.api.src.services.system_diagnostics import evaluate_diagnostics
    snap = _empty_snap()
    snap["postgres"]["cache_hit_pct"] = 90.0  # critical
    snap["postgres"]["pg_stat_statements_installed"] = False  # info
    snap["server"]["disk_root"] = {
        "path": "/", "total_gb": 100, "used_gb": 85, "free_gb": 15, "used_pct": 85.0,  # warn
    }
    findings = evaluate_diagnostics(snap)
    severities = [f["severity"] for f in findings]
    rank = {"critical": 0, "warn": 1, "info": 2}
    for i in range(len(severities) - 1):
        assert rank[severities[i]] <= rank[severities[i + 1]], (
            f"findings not severity-sorted: {severities}"
        )


def test_summarize_counts_per_severity():
    from apps.api.src.services.system_diagnostics import summarize
    findings = [
        {"severity": "critical"}, {"severity": "critical"},
        {"severity": "warn"},
        {"severity": "info"}, {"severity": "info"}, {"severity": "info"},
    ]
    out = summarize(findings)
    assert out == {"critical": 2, "warn": 1, "info": 3}


def test_evaluator_isolates_buggy_rule(monkeypatch):
    """A rule that raises shouldn't break the others."""
    from apps.api.src.services import system_diagnostics as diag

    def good(snap, ts):
        return [{"id": "good", "severity": "info", "title": "ok",
                 "evidence": "", "recommendation": "", "affected": [],
                 "action": None, "detected_at": ts}]

    def bad(snap, ts):
        raise RuntimeError("oops")

    monkeypatch.setattr(diag, "_RULES", [good, bad, good])
    findings = diag.evaluate_diagnostics(_empty_snap())
    assert len(findings) == 2  # both 'good's, 'bad' dropped silently
