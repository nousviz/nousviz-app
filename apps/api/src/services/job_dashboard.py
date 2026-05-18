"""
B277 (v0.9.11.16) — centralized job state dashboard.

Backs GET /api/jobs/dashboard with 4 sections:
  - now: currently-running + queued jobs with elapsed time
  - recent: last 12h of completed runs (chronological, with status)
  - upcoming: next 6h of scheduled fires (with may_overlap predictions)
  - failing: jobs with > 50% error rate over 24h

All queries use indexed columns (job_runs.started_at, job_runs.status,
sync_schedule_registry.next_fire_at). Single connection per call.
Operator-confirmed via Resources panel + cron.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.job_dashboard")


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass
class NowItem:
    id: int
    job_id: str
    status: str
    started_at: str
    elapsed_ms: int
    schedule_cron: Optional[str]
    next_fire_at: Optional[str]
    will_overlap_next: bool
    heartbeat_at: Optional[str]
    heartbeat_age_sec: Optional[int]
    worker_alive: bool


# B277 v0.9.11.16.4: a worker is considered alive if it heartbeated within
# this many seconds. Worker writes heartbeat_at every 10s during a job
# run; threshold of 90s gives 8 missed beats before "dead" — comfortable
# with cache + clock-skew + GC pauses but tight enough to detect real
# crashes within a couple of dashboard refreshes.
WORKER_ALIVE_THRESHOLD_SEC = 90


@dataclass
class RecentItem:
    id: int
    job_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    error_short: Optional[str]


@dataclass
class UpcomingItem:
    plugin_id: str
    schedule_cron: str
    next_fire_at: str
    ms_until_fire: int
    avg_duration_ms: Optional[int]
    may_overlap: bool


@dataclass
class FailingItem:
    job_id: str
    runs_24h: int
    errors_24h: int
    error_rate_pct: float
    last_error: Optional[str]
    last_error_at: Optional[str]


# ── Helpers ──────────────────────────────────────────────────────────


def _ts_iso(ts) -> Optional[str]:
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


# ── Section collectors ──────────────────────────────────────────────


def get_now_runs() -> list[NowItem]:
    """Currently running or queued jobs + their schedule context.

    v0.9.11.16.4 surfaces heartbeat_at + computed worker_alive so
    callers (dashboard, cancel endpoint) can distinguish a live worker
    from an orphaned 'running' row left over from a Postgres restart
    or scheduler crash.
    """
    out: list[NowItem] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              jr.id,
              jr.job_id,
              jr.status,
              jr.started_at,
              EXTRACT(EPOCH FROM (now() - jr.started_at))::bigint * 1000 AS elapsed_ms,
              ssr.cron_expression,
              ssr.next_fire_at,
              jr.heartbeat_at,
              CASE WHEN jr.heartbeat_at IS NOT NULL
                THEN EXTRACT(EPOCH FROM (now() - jr.heartbeat_at))::bigint
                ELSE NULL
              END AS heartbeat_age_sec
            FROM job_runs jr
            LEFT JOIN sync_schedule_registry ssr
              ON ssr.plugin_id = SUBSTRING(jr.job_id FROM 'sync:(.*)$')
            WHERE jr.status IN ('running', 'queued', 'cancelling')
            ORDER BY jr.started_at DESC
            LIMIT 50
            """
        )
        for row in cur.fetchall():
            (id_, job_id, status, started_at, elapsed_ms,
             cron, next_fire_at, heartbeat_at, heartbeat_age_sec) = row
            # will_overlap_next = elapsed > (next_fire_at - started_at)
            # i.e. the current run's already taken longer than the gap to next fire
            will_overlap = False
            if next_fire_at and started_at:
                window_ms = (next_fire_at - started_at).total_seconds() * 1000
                if elapsed_ms > window_ms:
                    will_overlap = True
            # Liveness: worker is alive iff it heartbeated recently.
            # Queued rows have no claim → no worker yet → not "alive"
            # in the running sense; the dashboard treats queued as a
            # neutral state (waiting for worker pickup).
            hb_age_int = int(heartbeat_age_sec) if heartbeat_age_sec is not None else None
            worker_alive = (
                status in ("running", "cancelling")
                and hb_age_int is not None
                and hb_age_int < WORKER_ALIVE_THRESHOLD_SEC
            )
            out.append(NowItem(
                id=int(id_),
                job_id=job_id,
                status=status,
                started_at=_ts_iso(started_at) or "",
                elapsed_ms=int(elapsed_ms or 0),
                schedule_cron=cron,
                next_fire_at=_ts_iso(next_fire_at),
                will_overlap_next=will_overlap,
                heartbeat_at=_ts_iso(heartbeat_at),
                heartbeat_age_sec=hb_age_int,
                worker_alive=worker_alive,
            ))
    return out


def get_recent_runs(hours: int = 12) -> list[RecentItem]:
    """Last N hours of completed runs (excludes still-running)."""
    out: list[RecentItem] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, job_id, status, started_at, completed_at,
                   duration_ms,
                   -- v0.9.11.22.4: take the TAIL of the error, not the head.
                   -- Python tracebacks put the actual exception class +
                   -- message at the END; LEFT(error, 200) truncated mid-
                   -- frame and never showed the operator the actual error.
                   -- 4000 chars covers the exception line + ~15 stack
                   -- frames, which is typically more than enough.
                   CASE WHEN error IS NOT NULL
                        THEN RIGHT(error, 4000)
                        END AS error_short
            FROM job_runs
            WHERE started_at > now() - (%s || ' hours')::interval
              AND status IN ('success', 'error', 'cancelled', 'timeout', 'skipped', 'paused')
            ORDER BY started_at DESC
            LIMIT 100
            """,
            (str(hours),),
        )
        # B313 (v0.10.4.1): pull a clean exception headline out of the
        # raw traceback so the dashboard's recent-runs row shows the
        # actionable message instead of a head-chopped stack frame.
        from .error_summary import extract_error_summary

        for row in cur.fetchall():
            id_, job_id, status, started_at, completed_at, duration_ms, error_short = row
            if error_short:
                parsed = extract_error_summary(error_short)
                if parsed["summary"]:
                    error_short = parsed["summary"]
            out.append(RecentItem(
                id=int(id_),
                job_id=job_id,
                status=status,
                started_at=_ts_iso(started_at) or "",
                completed_at=_ts_iso(completed_at),
                duration_ms=int(duration_ms) if duration_ms is not None else None,
                error_short=error_short,
            ))
    return out


def get_upcoming_runs(hours: int = 6) -> list[UpcomingItem]:
    """Next N hours of scheduled fires + may_overlap predictions."""
    out: list[UpcomingItem] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              ssr.plugin_id,
              ssr.cron_expression,
              ssr.next_fire_at,
              EXTRACT(EPOCH FROM (ssr.next_fire_at - now()))::bigint * 1000 AS ms_until_fire,
              (SELECT AVG(duration_ms)::int FROM job_runs
                WHERE job_id = 'sync:' || ssr.plugin_id
                  AND status = 'success'
                  AND started_at > now() - interval '24 hours') AS avg_duration_ms
            FROM sync_schedule_registry ssr
            WHERE ssr.next_fire_at < now() + (%s || ' hours')::interval
              AND ssr.next_fire_at > now()
            ORDER BY ssr.next_fire_at ASC
            LIMIT 50
            """,
            (str(hours),),
        )
        for row in cur.fetchall():
            plugin_id, cron, next_fire_at, ms_until_fire, avg_duration_ms = row
            ms_until_fire = int(ms_until_fire or 0)
            avg_duration_ms = int(avg_duration_ms) if avg_duration_ms is not None else None
            # may_overlap: if average duration exceeds 90% of time-to-fire,
            # it's likely the running sync OR the next run will collide
            may_overlap = False
            if avg_duration_ms is not None and ms_until_fire > 0:
                may_overlap = avg_duration_ms > ms_until_fire * 0.9
            out.append(UpcomingItem(
                plugin_id=plugin_id,
                schedule_cron=cron or "",
                next_fire_at=_ts_iso(next_fire_at) or "",
                ms_until_fire=ms_until_fire,
                avg_duration_ms=avg_duration_ms,
                may_overlap=may_overlap,
            ))
    return out


def get_failing_jobs() -> list[FailingItem]:
    """Jobs with ANY errors in the last 24h, ordered by most recent error.

    The original v0.9.11.16 threshold of > 50% error rate (min 4 runs)
    hid jobs with sporadic-but-real failures. Operator UX feedback: a
    single failure in the last hour matters and should surface, not
    just chronic-failure jobs. The frontend renames this section to
    "Issues" and deep-links each row into /system/logs filtered to the
    erroring job.
    """
    out: list[FailingItem] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            WITH stats AS (
              SELECT
                job_id,
                COUNT(*) AS runs,
                COUNT(*) FILTER (WHERE status = 'error') AS errors,
                MAX(error) FILTER (WHERE status = 'error') AS last_error,
                MAX(started_at) FILTER (WHERE status = 'error') AS last_error_at
              FROM job_runs
              WHERE started_at > now() - interval '24 hours'
              GROUP BY job_id
            )
            SELECT
              job_id, runs, errors,
              ROUND(100.0 * errors / NULLIF(runs, 0), 1) AS error_rate_pct,
              -- v0.9.11.22.4: same TAIL-not-HEAD treatment as get_recent_runs.
              CASE WHEN last_error IS NOT NULL
                   THEN RIGHT(last_error, 4000)
                   END AS last_error_short,
              last_error_at
            FROM stats
            WHERE errors > 0
            ORDER BY last_error_at DESC NULLS LAST
            LIMIT 30
            """
        )
        # B313 (v0.10.4.1): clean exception headline for the "failing
        # jobs" widget too. Same parser as recent_runs.
        from .error_summary import extract_error_summary

        for row in cur.fetchall():
            job_id, runs, errors, error_rate_pct, last_error, last_error_at = row
            if last_error:
                parsed = extract_error_summary(last_error)
                if parsed["summary"]:
                    last_error = parsed["summary"]
            out.append(FailingItem(
                job_id=job_id,
                runs_24h=int(runs or 0),
                errors_24h=int(errors or 0),
                error_rate_pct=float(error_rate_pct or 0),
                last_error=last_error,
                last_error_at=_ts_iso(last_error_at),
            ))
    return out


# ── Top-level dashboard ──────────────────────────────────────────────


def get_dashboard() -> dict:
    """Compose all 4 sections into one snapshot for the API endpoint."""
    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "now": [asdict(item) for item in get_now_runs()],
        "recent": [asdict(item) for item in get_recent_runs(hours=12)],
        "upcoming": [asdict(item) for item in get_upcoming_runs(hours=6)],
        "failing": [asdict(item) for item in get_failing_jobs()],
    }
