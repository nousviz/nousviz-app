"""nousviz_sdk.progress — Friendly progress reporting for plugin sync scripts.

Plugins call ``progress.report(...)`` any time during sync to update the
``job_runs.progress`` JSONB column that powers the live progress card in
the UI. The card on the plugin Settings tab and on /system/jobs polls
``/api/plugins/<id>/sync/status`` and renders whatever fields you set.

Wraps ``nousviz_sdk.jobs.heartbeat()`` with a more discoverable signature.
All fields optional. Safe to call from sync-mode plugins (no-op when not
in a tracked run, e.g. running a sync script directly from a shell).

Example::

    from nousviz_sdk import progress, jobs

    def run(self, since=None):
        total = self.api.count(self.jql)
        done = 0
        for batch in self.api.iter_pages(self.jql):
            if jobs.check_cancelled():
                return
            for issue in batch:
                self.upsert_issue(issue)
                done += 1
            progress.report(
                rows_done=done,
                rows_total=total,
                message=f"Fetching issues {done}/{total}",
            )
"""
from __future__ import annotations

from typing import Optional

from . import jobs as _jobs


def report(
    pct: Optional[float] = None,
    message: Optional[str] = None,
    rows_done: Optional[int] = None,
    rows_total: Optional[int] = None,
) -> None:
    """Update the live progress for the current job_runs row.

    Args:
        pct: 0-100 percentage. UI renders a determinate bar.
        message: short status line shown below the bar.
        rows_done: rows processed so far. UI computes pct from this and
            rows_total when pct is not given explicitly.
        rows_total: total rows expected.

    All arguments optional. Calling with no arguments is equivalent to
    a bare heartbeat — useful in long inner loops where the script wants
    to signal liveness without changing displayed progress.

    Silent no-op when:
      - Not in a tracked run (running outside the worker / outside
        BaseSyncScript.main()).
      - The DB is unreachable (transient network blip — never fail a
        real sync because progress reporting failed).
      - Called more than once per 2 seconds (heartbeat is throttled
        in nousviz_sdk.jobs to keep DB load trivial).

    pct is clamped to [0, 100] to defend against script bugs (e.g. a
    division-by-zero producing inf).
    """
    payload: dict = {}
    if pct is not None:
        payload["pct"] = max(0.0, min(100.0, float(pct)))
    if message is not None:
        payload["message"] = str(message)
    if rows_done is not None:
        payload["rows_done"] = int(rows_done)
    if rows_total is not None:
        payload["rows_total"] = int(rows_total)

    if not payload:
        # No fields supplied — bump heartbeat without touching progress.
        _jobs.heartbeat()
        return

    _jobs.heartbeat(progress=payload)
