"""
nousviz_sdk.jobs — Async job primitives for plugin sync code.

Plugins that declare `execution_mode: async` in plugin.yaml should call
these helpers from inside their `run()` method to cooperate with the
async job worker:

    from nousviz_sdk.jobs import heartbeat, check_cancelled

    def run(self, since=None):
        for batch in self.batches():
            if check_cancelled():
                self.logger.info("cancel requested — exiting cleanly")
                return
            self.upsert_batch(batch)
            heartbeat(progress={
                "rows_done": self._total,
                "rows_expected": self._expected,
            })

For sync-mode plugins (the default `execution_mode: sync`), these
helpers are no-ops — safe to call but do nothing useful. This lets a
plugin author write `run()` against the async API and use the same
code in either mode during development.

The worker sets the current run_id via an environment variable
(NOUSVIZ_JOB_RUN_ID) before spawning the subprocess; the SDK reads it
from os.environ. For BaseSyncScript.main() invocations the run_id is
also set in a context var so Python-level helpers can find it without
env access.

Heartbeat writes are throttled to at most once per 2 seconds to prevent
plugins that call heartbeat in a tight loop from flooding the DB.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("nousviz_sdk.jobs")


# Context var set by BaseSyncScript.main() when it creates a job_runs row.
# Falls back to NOUSVIZ_JOB_RUN_ID env var (set by the worker for async runs
# that execute as subprocesses). None when neither is set — helpers no-op.
_current_run_id: Optional[int] = None
_last_heartbeat_at: float = 0.0
_HEARTBEAT_THROTTLE_SEC: float = 2.0


def _set_current_run_id(run_id: Optional[int]) -> None:
    """Called by BaseSyncScript.main() at run start/end. Plugin authors
    should not call this directly."""
    global _current_run_id, _last_heartbeat_at
    _current_run_id = run_id
    _last_heartbeat_at = 0.0


def get_run_id() -> Optional[int]:
    """Return the current job_runs.id, or None if not in a tracked run.

    Order of preference:
      1. Context var set by BaseSyncScript.main()
      2. NOUSVIZ_JOB_RUN_ID environment variable (set by async worker)

    Returns int or None. Plugin code that logs the run_id can use this
    without worrying about which execution mode it's in.
    """
    if _current_run_id is not None:
        return _current_run_id
    env_val = os.environ.get("NOUSVIZ_JOB_RUN_ID")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            return None
    return None


def heartbeat(progress: Optional[dict] = None) -> None:
    """Update job_runs.heartbeat_at and optionally merge `progress` into
    job_runs.progress (JSONB).

    Silent no-op when:
      - Not in a tracked run (sync-mode plugin, or standalone invocation)
      - DB is unreachable (network blip — don't fail the sync over a
        heartbeat)
      - Called more than once per 2 seconds (throttled)

    Plugin authors can call this freely in a hot loop without worrying
    about DB load.
    """
    global _last_heartbeat_at
    run_id = get_run_id()
    if run_id is None:
        return
    now = time.monotonic()
    if now - _last_heartbeat_at < _HEARTBEAT_THROTTLE_SEC:
        return
    _last_heartbeat_at = now

    try:
        from . import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            if progress:
                cur.execute(
                    """
                    UPDATE job_runs
                    SET heartbeat_at = now(),
                        progress = progress || %s::jsonb
                    WHERE id = %s
                    """,
                    (json.dumps(progress), run_id),
                )
            else:
                cur.execute(
                    "UPDATE job_runs SET heartbeat_at = now() WHERE id = %s",
                    (run_id,),
                )
            conn.commit()
    except Exception as e:
        logger.warning(f"heartbeat failed for run {run_id}: {e}")


def check_cancelled() -> bool:
    """Return True if the operator requested cancellation of the current run.

    Plugin code should call this between batches and exit cleanly (return
    from run()) when True. Writing partial data is OK — plugins manage
    their own transactional boundaries.

    Returns False when:
      - Not in a tracked run
      - DB is unreachable (assume not cancelled — err on the side of
        continuing work)
      - Run is in any non-cancelling state (running, paused — paused jobs
        are currently treated as not-cancelled; pause semantics are an
        operator signal, not a plugin-visible pause)
    """
    run_id = get_run_id()
    if run_id is None:
        return False

    try:
        from . import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT status FROM job_runs WHERE id = %s",
                (run_id,),
            )
            row = cur.fetchone()
            if not row:
                return False
            return row[0] == "cancelling"
    except Exception as e:
        logger.warning(f"check_cancelled failed for run {run_id}: {e}")
        return False
