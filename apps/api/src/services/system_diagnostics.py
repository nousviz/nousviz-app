"""
B272 (v0.9.11.18) — system-health diagnostic rules engine.

Each rule is a pure function that takes the snapshot dict produced by
`server_resources.to_dict() | postgres_resources.get_all()` (the same
shape served by `GET /api/system/resources`) and returns a `Finding`
or `None`.

Rules are calibrated against the 2026-05-04 production audit so the
expected findings (e.g. `sync_failing_consistently` on the four bad
plugins) come back at the right severity. Boundary cases are pinned
in tests so calibration changes show up as failing tests rather than
silent UX shifts.

Phase 1 (v0.9.11.18) ships 12 rules. Phase 2 (deferred):
  - `uninstalled_plugin_data_orphaned` (needs plugin_audit_log
    integration + curated platform-table whitelist)
  - `host_data_dominates_db` (depends on the above)
  - `sql_with_confirmation` action type (privileged apply endpoint)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.system_diagnostics")


# ── Helpers that run small SQL queries inside a rule ────────────────


def _list_table_indexes(schema: str, name: str) -> list[str]:
    """Return the names of every index on a (schema, name) table.

    Used by rules that surface "what's currently indexed" alongside
    their finding so the recommendation is grounded — operators see
    the existing indexes rather than being told to "investigate".
    Failure (table missing, role lacks SELECT on pg_indexes) returns
    an empty list rather than raising; the rule still fires, just
    without the indexes detail.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = %s AND tablename = %s
                ORDER BY indexname
                """,
                (schema, name),
            )
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.warning("list_table_indexes failed for %s.%s: %s", schema, name, e)
        return []


# ── Severity ladder helpers ─────────────────────────────────────────


def _ladder(value: float, *, warn_at: float, critical_at: float) -> Optional[str]:
    """Return 'critical' | 'warn' | None based on simple threshold ladder."""
    if value >= critical_at:
        return "critical"
    if value >= warn_at:
        return "warn"
    return None


def _make_finding(
    *,
    rule_id: str,
    severity: str,
    title: str,
    evidence: str,
    recommendation: str,
    detected_at: str,
    affected: Optional[list[dict]] = None,
    action: Optional[dict] = None,
) -> dict:
    """Compose a Finding dict. Returning dict (not BaseModel) keeps
    the rules engine free of FastAPI/Pydantic coupling — the route
    converts to the typed model at the edge."""
    return {
        "id": rule_id,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
        "affected": affected or [],
        "action": action,
        "detected_at": detected_at,
    }


# ── Rules ───────────────────────────────────────────────────────────


def rule_sync_overlapping_schedule(snap: dict, ts: str) -> list[dict]:
    """A sync's average duration is ≥ 60% / 90% of its cron interval.

    cpu_load_pct_estimate = (avg_duration_ms × runs_24h) / 86_400_000 × 100,
    but we lean on the per-row value rather than the total here so the
    finding points at the worst-offender plugin specifically. Total
    sync CPU is its own rule (`total_sync_cpu_high`).
    """
    out: list[dict] = []
    for sync in snap.get("syncs", []) or []:
        pct = sync.get("cpu_load_pct_estimate") or 0
        sev = _ladder(pct, warn_at=60, critical_at=90)
        if not sev:
            continue
        plugin_id = sync.get("plugin_id", "?")
        cron = sync.get("schedule_cron", "?")
        avg_ms = sync.get("avg_duration_ms")
        avg_str = f"{avg_ms / 1000:.1f}s" if isinstance(avg_ms, (int, float)) else "—"
        interval = sync.get("schedule_interval_seconds")
        interval_str = f"{interval}s" if interval else "?"
        evidence = (
            f"Plugin '{plugin_id}' on cron {cron}: average run takes {avg_str}, "
            f"which is {pct:.0f}% of the {interval_str} cron interval. "
            f"Each new fire risks colliding with a still-running prior run."
        )
        recommendation = (
            "Either widen the schedule (Schedule editor on /system/jobs → Settings) "
            "or speed the sync. Crossing 90% almost certainly causes overlap."
        )
        out.append(_make_finding(
            rule_id="sync_overlapping_schedule",
            severity=sev,
            title=f"sync:{plugin_id} runs at {pct:.0f}% of its schedule interval",
            evidence=evidence,
            recommendation=recommendation,
            detected_at=ts,
            affected=[{"type": "sync", "name": f"sync:{plugin_id}", "detail": f"avg {avg_str}, cron {cron}"}],
            action={
                "type": "external",
                "label": "Open plugin settings",
                "url": f"/plugin/{plugin_id}/settings",
            },
        ))
    return out


def rule_sync_failing_consistently(snap: dict, ts: str) -> list[dict]:
    """A sync's error rate exceeds 50% over 24h with at least 4 runs.

    Different from the dashboard's `failing` section (which broadened
    to >0 errors): the diagnostic rule keeps the >50% threshold so it
    only fires for chronic failures, not one-off blips. The dashboard
    surfaces the lower-severity ones.
    """
    bad: list[dict] = []
    for sync in snap.get("syncs", []) or []:
        runs = int(sync.get("runs_24h") or 0)
        errors = int(sync.get("errors_24h") or 0)
        if runs < 4:
            continue
        rate = errors / runs if runs > 0 else 0
        if rate > 0.5:
            bad.append({
                "plugin_id": sync.get("plugin_id", "?"),
                "runs": runs,
                "errors": errors,
                "rate_pct": rate * 100,
            })
    if not bad:
        return []
    bad.sort(key=lambda b: -b["rate_pct"])
    plugin_list = ", ".join(b["plugin_id"] for b in bad)
    evidence_lines = [
        f"{b['plugin_id']}: {b['errors']}/{b['runs']} errors ({b['rate_pct']:.0f}%)"
        for b in bad
    ]
    return [_make_finding(
        rule_id="sync_failing_consistently",
        severity="critical",
        title=f"{len(bad)} sync job{'s' if len(bad) != 1 else ''} failing consistently (24h)",
        evidence=(
            "Each failing run still consumes CPU and a database connection. "
            "Common causes: expired credentials, upstream API change, network outage.\n"
            + "\n".join(evidence_lines)
        ),
        recommendation=(
            f"Open the plugin settings for each ({plugin_list}) and check credentials. "
            "Use the Schedule editor on /system/jobs to pause runs while diagnosing."
        ),
        detected_at=ts,
        affected=[
            {"type": "sync", "name": f"sync:{b['plugin_id']}",
             "detail": f"{b['errors']}/{b['runs']} 24h"}
            for b in bad
        ],
        action={
            "type": "external",
            "label": "View jobs",
            "url": "/system/jobs",
        },
    )]


def rule_total_sync_cpu_high(snap: dict, ts: str) -> list[dict]:
    """Sum of cpu_load_pct_estimate across all syncs > 50% / > 100%.

    Different from the per-sync overlap rule — this is the aggregate
    pressure the schedule mix puts on a single CPU. Triggers when
    multiple plugins each look fine individually but together saturate
    the host.
    """
    syncs = snap.get("syncs", []) or []
    total = sum((s.get("cpu_load_pct_estimate") or 0) for s in syncs)
    sev = _ladder(total, warn_at=50, critical_at=100)
    if not sev:
        return []
    syncs_sorted = sorted(syncs, key=lambda s: -(s.get("cpu_load_pct_estimate") or 0))
    top = syncs_sorted[:3]
    breakdown = ", ".join(
        f"{s.get('plugin_id', '?')} {s.get('cpu_load_pct_estimate', 0):.0f}%"
        for s in top
    )
    evidence = (
        f"Total estimated sync CPU load: {total:.0f}% of one core. "
        f"Top contributors: {breakdown}."
    )
    recommendation = (
        "Either widen the cron interval on the worst offender, or split syncs "
        "across hosts. Above 100%, syncs definitely back up; above 50%, the "
        "host has little headroom for query traffic."
    )
    # v0.9.11.19.3: action targets the worst offender's plugin
    # settings page so "widen the cron interval on the worst offender"
    # is one click. Pre-19.3 this linked back to /system/resources,
    # which is where the operator was already looking when they saw
    # the finding.
    worst = top[0] if top else None
    worst_plugin_id = (worst or {}).get("plugin_id") if worst else None
    action: Optional[dict] = None
    if worst_plugin_id:
        action = {
            "type": "external",
            "label": f"Open {worst_plugin_id} settings",
            "url": f"/plugin/{worst_plugin_id}/settings",
        }

    return [_make_finding(
        rule_id="total_sync_cpu_high",
        severity=sev,
        title=f"Sync CPU load is {total:.0f}% of a core",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[
            {"type": "sync", "name": f"sync:{s.get('plugin_id', '?')}",
             "detail": f"{s.get('cpu_load_pct_estimate', 0):.0f}%"}
            for s in top
        ],
        action=action,
    )]


def rule_index_bloat(snap: dict, ts: str) -> list[dict]:
    """Index size exceeds data size on a substantial table (>100 MB total).

    Indexes legitimately get bigger than data on heavily-indexed lookup
    tables. The threshold of `index_mb > data_mb` AND total > 100 MB
    catches the audit pattern (gsc_search_analytics where indexes were
    158% of data) without firing on small lookup tables.
    """
    out: list[dict] = []
    for t in snap.get("tables", []) or []:
        total = float(t.get("total_size_mb") or 0)
        idx = float(t.get("index_mb") or 0)
        data = float(t.get("data_mb") or 0)
        if total <= 100 or data <= 0 or idx <= data:
            continue
        ratio = idx / data
        sev = _ladder(ratio, warn_at=1.0, critical_at=2.0)
        if not sev:
            continue
        name = t.get("name", "?")
        schema = t.get("schema", "public")
        evidence = (
            f"Table {schema}.{name} ({total:.0f} MB total): indexes are {idx:.0f} MB, "
            f"data is {data:.0f} MB ({ratio:.1f}× bloat). "
            f"REINDEX would shrink the indexes; if multiple unused indexes are "
            f"contributing, drop those instead (see `unused_index` findings)."
        )
        recommendation = (
            f"Run `REINDEX TABLE {schema}.{name};` during a maintenance window. "
            "If the table is heavily written-to, prefer `REINDEX TABLE CONCURRENTLY` "
            "(Postgres 12+) to avoid blocking writes."
        )
        out.append(_make_finding(
            rule_id="index_bloat",
            severity=sev,
            title=f"{schema}.{name} indexes are {ratio:.1f}× the data size",
            evidence=evidence,
            recommendation=recommendation,
            detected_at=ts,
            affected=[{"type": "table", "name": f"{schema}.{name}",
                       "detail": f"{idx:.0f}MB idx / {data:.0f}MB data"}],
            action={
                "type": "manual",
                "label": "Show REINDEX SQL",
                "sql": f"REINDEX TABLE CONCURRENTLY {schema}.{name};",
            },
        ))
    return out


def rule_unused_index(snap: dict, ts: str) -> list[dict]:
    """Indexes never scanned, > 1 MB, that aren't load-bearing for
    constraints. Each is a drop candidate.

    v0.9.11.19.3: excludes primary keys + unique indexes. PKs are
    used implicitly by every UPDATE/DELETE + every foreign-key
    lookup; unique indexes enforce a constraint regardless of whether
    a SELECT probes them. pg_stat_user_indexes.idx_scan only counts
    explicit lookups, so both legitimately show 0 scans even when
    load-bearing — dropping them would silently break inserts.

    Aggregated into a single finding listing each index — the
    operator wants the set, not 20 separate cards.
    """
    candidates: list[dict] = []
    for idx in snap.get("indexes_largest", []) or []:
        scans = int(idx.get("scans_lifetime") or 0)
        size = float(idx.get("size_mb") or 0)
        # Skip PKs and unique indexes outright — see rule docstring.
        if idx.get("is_primary") or idx.get("is_unique"):
            continue
        if scans == 0 and size >= 1:
            candidates.append(idx)
    if not candidates:
        return []
    total_size = sum(float(c.get("size_mb") or 0) for c in candidates)
    drop_sql = "\n".join(
        f"DROP INDEX CONCURRENTLY {c.get('schema','public')}.{c.get('name','?')};  -- {c.get('size_mb',0):.1f} MB on {c.get('table','?')}"
        for c in candidates
    )
    evidence_lines = [
        f"  - {c.get('schema','public')}.{c.get('name','?')} "
        f"({c.get('size_mb',0):.1f} MB on {c.get('table','?')}) — never scanned"
        for c in candidates
    ]
    return [_make_finding(
        rule_id="unused_index",
        severity="info",
        title=f"{len(candidates)} unused index{'es' if len(candidates) != 1 else ''} ({total_size:.0f} MB total)",
        evidence=(
            "Indexes that have never been scanned since they were created. "
            "Each is just disk + write overhead with no query benefit:\n"
            + "\n".join(evidence_lines)
        ),
        recommendation=(
            "Drop the listed indexes during a maintenance window. Use "
            "`DROP INDEX CONCURRENTLY` to avoid blocking writes. If a query "
            "you haven't run yet would have used one, re-create it later — "
            "Postgres records every scan, so the data here is reliable."
        ),
        detected_at=ts,
        affected=[
            {"type": "index", "name": f"{c.get('schema','public')}.{c.get('name','?')}",
             "detail": f"{c.get('size_mb',0):.1f}MB on {c.get('table','?')}"}
            for c in candidates
        ],
        action={
            "type": "manual",
            "label": "Show DROP INDEX SQL",
            "sql": drop_sql,
        },
    )]


def rule_sequential_scan_heavy(snap: dict, ts: str) -> list[dict]:
    """A table > 10 MB / > 1k rows is seq-scanned > 25% of the time.

    v0.9.11.19.2: rule reworded to be grounded rather than punting.
    Surfaces the table's existing indexes inline + reminds the
    operator that on small hot tables (< 50 MB) the planner often
    picks seq scan correctly — `verify with EXPLAIN ANALYZE` is
    better advice than "install pg_stat_statements first".
    """
    out: list[dict] = []
    for t in snap.get("tables", []) or []:
        total = float(t.get("total_size_mb") or 0)
        rows = int(t.get("rows") or 0)
        seq_pct = float(t.get("seq_scan_pct") or 0)
        if total < 10 or rows < 1000:
            continue
        if seq_pct <= 25:
            continue
        name = t.get("name", "?")
        schema = t.get("schema", "public")
        seq_count = int(t.get("seq_scan_count") or 0)
        idx_count = int(t.get("idx_scan_count") or 0)

        # Pull existing indexes so the recommendation is grounded.
        existing_indexes = _list_table_indexes(schema, name)
        index_lines = (
            "\n".join(f"  - {idx}" for idx in existing_indexes)
            if existing_indexes
            else "  (no indexes found, or pg_indexes lookup failed)"
        )

        # Tone the wording down on small hot tables — at < 50 MB the
        # planner correctly prefers seq scan over index scan when
        # query patterns don't have selective predicates.
        size_qualifier = (
            " On a table this size (< 50 MB) the planner often picks "
            "seq scan correctly when predicates aren't selective; "
            "this finding is informational rather than urgent."
        ) if total < 50 else ""

        evidence = (
            f"Table {schema}.{name} ({total:.0f} MB, {rows:,} rows) is being read "
            f"with sequential scans {seq_pct:.0f}% of the time "
            f"({seq_count:,} seq vs {idx_count:,} index scans).{size_qualifier}\n\n"
            f"Existing indexes on this table:\n{index_lines}"
        )
        recommendation = (
            f"Run `EXPLAIN (ANALYZE, BUFFERS)` on the dominant queries against "
            f"{schema}.{name} to confirm whether they're scanning vs. using one "
            f"of the indexes above. If the planner is choosing seq scan despite "
            f"a matching index, the existing index may be too wide — a partial "
            f"index targeting the dominant predicate is usually the fix. "
            f"Adding an index without confirming via EXPLAIN risks creating "
            f"index bloat for queries that wouldn't have used it anyway."
        )
        affected: list[dict] = [{
            "type": "table",
            "name": f"{schema}.{name}",
            "detail": f"{seq_pct:.0f}% seq, {rows:,} rows",
        }]
        for idx_name in existing_indexes:
            affected.append({
                "type": "index",
                "name": f"{schema}.{idx_name}",
                "detail": "existing",
            })
        out.append(_make_finding(
            rule_id="sequential_scan_heavy",
            severity="warn",
            title=f"{schema}.{name} is sequential-scanned {seq_pct:.0f}% of the time",
            evidence=evidence,
            recommendation=recommendation,
            detected_at=ts,
            affected=affected,
        ))
    return out


def rule_vacuum_behind(snap: dict, ts: str) -> list[dict]:
    """A 100 MB+ table hasn't been vacuumed in > 7 days.

    Stats go stale → planner makes bad choices → queries slow down.
    """
    out: list[dict] = []
    now = datetime.now(timezone.utc)
    affected_tables: list[dict] = []
    for t in snap.get("tables", []) or []:
        total = float(t.get("total_size_mb") or 0)
        if total < 100:
            continue
        last_vacuum_iso = t.get("last_vacuum")
        if not last_vacuum_iso:
            # Never vacuumed AND substantial size = definitely a hit.
            affected_tables.append({**t, "_age_days": None})
            continue
        try:
            last_dt = datetime.fromisoformat(str(last_vacuum_iso).replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_days = (now - last_dt).total_seconds() / 86_400
            if age_days > 7:
                affected_tables.append({**t, "_age_days": age_days})
        except Exception:
            continue
    if not affected_tables:
        return []
    affected_tables.sort(key=lambda x: -(x.get("total_size_mb") or 0))

    def _age_str(age_days: Optional[float]) -> str:
        return "never vacuumed" if age_days is None else f"{age_days:.0f} days ago"

    breakdown_lines = []
    for t in affected_tables:
        schema = t.get("schema", "public")
        name = t.get("name", "?")
        size_mb = t.get("total_size_mb", 0)
        age = t["_age_days"]
        breakdown_lines.append(f"  - {schema}.{name} ({size_mb:.0f} MB) — {_age_str(age)}")
    breakdown = "\n".join(breakdown_lines)
    vacuum_sql = "\n".join(
        f"VACUUM ANALYZE {t.get('schema','public')}.{t.get('name','?')};"
        for t in affected_tables
    )
    return [_make_finding(
        rule_id="vacuum_behind",
        severity="warn",
        title=f"{len(affected_tables)} table{'s' if len(affected_tables) != 1 else ''} have stale statistics (>7d since vacuum)",
        evidence=(
            "Postgres autovacuum hasn't run on these substantial tables in over a "
            "week. The query planner uses these stats to choose plans; stale stats "
            "mean it's guessing. Symptoms: queries that used to be fast slowing "
            "down for no obvious reason.\n" + breakdown
        ),
        recommendation=(
            "Run VACUUM ANALYZE on each table during a low-traffic window. If this "
            "keeps recurring, lower autovacuum_vacuum_scale_factor for the affected "
            "tables (per-table tuning via ALTER TABLE)."
        ),
        detected_at=ts,
        affected=[
            {
                "type": "table",
                "name": f"{t.get('schema','public')}.{t.get('name','?')}",
                "detail": (
                    f"{t.get('total_size_mb',0):.0f}MB, last vacuum: "
                    + ("never" if t['_age_days'] is None else f"{t['_age_days']:.0f}d ago")
                ),
            }
            for t in affected_tables
        ],
        action={
            "type": "manual",
            "label": "Show VACUUM ANALYZE SQL",
            "sql": vacuum_sql,
        },
    )]


def rule_cache_hit_low(snap: dict, ts: str) -> list[dict]:
    """Buffer-cache hit rate below 99% (warn) / 95% (critical).

    Healthy Postgres deployments sit at 99.5%+. Below 99 means
    significant disk reads per query; below 95 is real I/O pressure.
    """
    pg = snap.get("postgres") or {}
    pct = float(pg.get("cache_hit_pct") or 0)
    if pct >= 99:
        return []
    sev = "critical" if pct < 95 else "warn"
    evidence = (
        f"Postgres buffer-cache hit rate is {pct:.1f}%. Healthy installs sit at "
        f"99.5%+; below 99% means each query is reading from disk noticeably "
        f"often. Common causes: shared_buffers too small, working set bigger "
        f"than memory, or a cold cache after restart."
    )
    recommendation = (
        "Confirm shared_buffers ≈ 25% of host RAM (postgresql.conf). If "
        "working-set size is the issue, larger shared_buffers won't help — "
        "look for missing indexes or unbounded growth (see retention "
        "policies on /settings/maintenance)."
    )
    return [_make_finding(
        rule_id="cache_hit_low",
        severity=sev,
        title=f"Postgres cache hit rate is {pct:.1f}%",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[{"type": "db", "name": "postgres", "detail": f"{pct:.1f}% hit"}],
    )]


def rule_disk_pressure(snap: dict, ts: str) -> list[dict]:
    """Root disk usage > 80% / > 90%."""
    server = snap.get("server") or {}
    disk = server.get("disk_root") or {}
    pct = float(disk.get("used_pct") or 0)
    if pct == 0:
        return []
    sev = _ladder(pct, warn_at=80, critical_at=90)
    if not sev:
        return []
    total_gb = float(disk.get("total_gb") or 0)
    free_gb = float(disk.get("free_gb") or 0)
    evidence = (
        f"Root disk usage is {pct:.0f}% ({total_gb - free_gb:.0f} GB used of "
        f"{total_gb:.0f} GB; {free_gb:.1f} GB free). Postgres write-ahead-log + "
        f"autovacuum need free space to operate; running out causes hard failures."
    )
    recommendation = (
        "Identify the largest contributors: check the Resources tab for big "
        "tables/indexes. Activate retention policies on /settings/maintenance "
        "to prune log/event tables. If the host is undersized, scale up the volume."
    )
    return [_make_finding(
        rule_id="disk_pressure",
        severity=sev,
        title=f"Root disk is {pct:.0f}% full",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[{"type": "host", "name": "/", "detail": f"{free_gb:.1f}GB free"}],
        action={
            "type": "external",
            "label": "Open retention policies",
            "url": "/settings/maintenance",
        },
    )]


def rule_no_swap_with_low_memory(snap: dict, ts: str) -> list[dict]:
    """Swap=0 AND memory_free<500MB. OOM kill territory."""
    server = snap.get("server") or {}
    swap = server.get("swap") or {}
    mem = server.get("memory") or {}
    swap_total = float(swap.get("total_mb") or 0)
    free = float(mem.get("free_mb") or 0)
    if swap_total > 0:
        return []
    if free >= 500:
        return []
    avail = float(mem.get("available_mb") or 0)
    evidence = (
        f"No swap configured (0 MB) and free memory is {free:.0f} MB "
        f"(available {avail:.0f} MB). With no swap, the kernel will OOM-kill "
        f"processes the moment memory is exhausted — usually Postgres or the "
        f"jobs-worker, both of which interrupt service."
    )
    recommendation = (
        "Add a swap file (`fallocate -l 2G /swapfile && mkswap /swapfile && "
        "swapon /swapfile`, then add to /etc/fstab). 2 GB of swap on a "
        "Postgres host is the standard safety net even when memory is plentiful."
    )
    return [_make_finding(
        rule_id="no_swap_with_low_memory",
        severity="warn",
        title="Host has no swap and free memory is low",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[{"type": "host", "name": "swap", "detail": f"{free:.0f}MB free, 0 swap"}],
        action={
            "type": "manual",
            "label": "Show swap setup commands",
            "shell": (
                "sudo fallocate -l 2G /swapfile\n"
                "sudo chmod 600 /swapfile\n"
                "sudo mkswap /swapfile\n"
                "sudo swapon /swapfile\n"
                "echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"
            ),
        },
    )]


def rule_pg_stat_statements_missing(snap: dict, ts: str) -> list[dict]:
    """The pg_stat_statements extension isn't installed.

    Without it, identifying slow queries means tcpdumping the pg
    socket. Almost always wanted in production.
    """
    pg = snap.get("postgres") or {}
    if pg.get("pg_stat_statements_installed") is True:
        return []
    if pg.get("pg_stat_statements_installed") is None:
        # Snapshot didn't run the check (e.g. unit-test fixture without the
        # field). Don't assert.
        return []
    evidence = (
        "pg_stat_statements is the Postgres extension that records per-query "
        "stats (calls, total time, rows). Without it, diagnosing query slowness "
        "is much harder. Enabling it has near-zero overhead."
    )
    recommendation = (
        "Connect as a superuser and run "
        "`CREATE EXTENSION IF NOT EXISTS pg_stat_statements;`. Restart "
        "Postgres so it picks up shared_preload_libraries (already set in "
        "setup.sh baselines)."
    )
    return [_make_finding(
        rule_id="pg_stat_statements_missing",
        severity="info",
        title="pg_stat_statements extension not installed",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[{"type": "db", "name": "postgres", "detail": "extension missing"}],
        action={
            "type": "manual",
            "label": "Show install SQL",
            "sql": "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",
        },
    )]


def rule_connection_pool_pressure(snap: dict, ts: str) -> list[dict]:
    """Active+idle connections > 80% of max_connections."""
    pg = snap.get("postgres") or {}
    active = int(pg.get("active_connections") or 0)
    idle = int(pg.get("idle_connections") or 0)
    max_conn = int(pg.get("max_connections") or 0)
    if max_conn <= 0:
        return []
    used = active + idle
    pct = used / max_conn * 100
    if pct <= 80:
        return []
    sev = "critical" if pct > 95 else "warn"
    evidence = (
        f"{used} of {max_conn} Postgres connections are in use ({pct:.0f}%). "
        f"At saturation, new connections are refused — the API and worker "
        f"start failing immediately. Common causes: connection-leaking client, "
        f"too-aggressive connection pool, or genuine traffic growth."
    )
    recommendation = (
        "Identify connection sources via "
        "`SELECT application_name, count(*) FROM pg_stat_activity GROUP BY 1;` "
        "If a pool is the culprit, lower its max. If max_connections is "
        "genuinely under-provisioned, raise it (postgresql.conf) — but keep "
        "in mind each connection costs ~10 MB of RAM."
    )
    return [_make_finding(
        rule_id="connection_pool_pressure",
        severity=sev,
        title=f"Postgres connection pool is {pct:.0f}% utilised",
        evidence=evidence,
        recommendation=recommendation,
        detected_at=ts,
        affected=[{"type": "db", "name": "postgres",
                   "detail": f"{used}/{max_conn} connections"}],
        action={
            "type": "manual",
            "label": "Show connection-source query",
            "sql": "SELECT application_name, count(*) FROM pg_stat_activity GROUP BY 1 ORDER BY 2 DESC;",
        },
    )]


# ── Top-level evaluator ─────────────────────────────────────────────


_RULES = [
    rule_sync_overlapping_schedule,
    rule_sync_failing_consistently,
    rule_total_sync_cpu_high,
    rule_index_bloat,
    rule_unused_index,
    rule_sequential_scan_heavy,
    rule_vacuum_behind,
    rule_cache_hit_low,
    rule_disk_pressure,
    rule_no_swap_with_low_memory,
    rule_pg_stat_statements_missing,
    rule_connection_pool_pressure,
]

_SEVERITY_RANK = {"critical": 0, "warn": 1, "info": 2}


def evaluate_diagnostics(snapshot: dict) -> list[dict]:
    """Run every registered rule against the snapshot and return all
    findings, sorted critical → warn → info, ties broken by rule id.

    Rule errors are isolated: a buggy rule won't break the rest. We
    log + drop and continue.
    """
    ts = snapshot.get("collected_at") or datetime.now(timezone.utc).isoformat()
    findings: list[dict] = []
    for rule in _RULES:
        try:
            result = rule(snapshot, ts) or []
            findings.extend(result)
        except Exception as e:
            logger.warning("rule %s raised: %s", getattr(rule, "__name__", "?"), e)
    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f["severity"], 99), f["id"]))
    return findings


def summarize(findings: list[dict]) -> dict[str, int]:
    """Per-severity count for the response summary block."""
    out = {"critical": 0, "warn": 0, "info": 0}
    for f in findings:
        sev = f.get("severity")
        if sev in out:
            out[sev] += 1
    return out
