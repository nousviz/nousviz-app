"""
log_events — Direct helper for operator-visible events (P114 v0.8.4).

Writes to `app_logs` (P104) without going through Python's logging
module. Used by the jobs-worker and the manual-sync-trigger route to
record terminal transitions (success / error / timeout / cancelled /
orphan cleanup) so operators can see sync outcomes alongside other
platform events in the Logs panel.

Why not use the logging-handler bridge?
  - The DB log handler in log_handler.py is attached to specific
    loggers (plugins, connections, dashboards, etc.) and maps names
    to source tags. Adding the jobs-worker means extending that map
    AND attaching to a new logger tree. For terminal transitions
    that are already structured (status, run_id, duration), a direct
    INSERT is clearer than pushing through logging middleware.
  - The jobs-worker process doesn't start the API's `setup_db_logging()`,
    so its loggers wouldn't hit the bridge anyway.

Levels: 'info' | 'warning' | 'error' — matches the filter UI in
`components/settings/LogsPanel.tsx`. Don't introduce 'debug' here unless
we also update the UI filter.

Source: defaults to 'sync' — the jobs-worker's canonical source. Callers
can override for other use cases.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger("nousviz.log_events")


def log_job_event(
    level: str,
    message: str,
    detail: Optional[dict] = None,
    source: str = "sync",
    *,
    plugin_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    run_id: Optional[int] = None,
) -> None:
    """Insert one row into app_logs. Silently no-ops on DB error so a
    logging failure never fails the caller.

    Args:
        level: 'info' | 'warning' | 'error'
        message: short human-readable event summary (truncated at 2000 chars)
        detail: optional JSON-serialisable dict for structured context
        source: app_logs.source tag (default 'sync'). Canonical plugin-side
            values (B203): 'plugin_install', 'plugin_update',
            'plugin_uninstall', 'plugin_lifecycle'. The /system/logs
            source filter dropdown populates these automatically.
        plugin_id: B208 (v0.9.6.1) — keyword-only. Plugin slug for the
            event, written to app_logs.plugin_id and merged into detail
            for back-compat. Pass when known.
        actor_user_id: B208 — keyword-only. UUID string of the operator
            who triggered the event (admin actions only). Worker /
            scheduler events leave this unset.
        run_id: B208 — keyword-only. job_runs.id when the event is tied
            to a sync or hook run.
    """
    try:
        # Merge promoted identifiers into detail so legacy query patterns
        # (`detail->>'plugin_id'`) still work. setdefault — if a caller
        # already put it in detail AND passed the kwarg, the kwarg wins
        # for the column but the existing detail key isn't overwritten.
        merged_detail = dict(detail or {})
        if plugin_id is not None:
            merged_detail.setdefault("plugin_id", plugin_id)
        if actor_user_id is not None:
            merged_detail.setdefault("actor_user_id", actor_user_id)
        if run_id is not None:
            merged_detail.setdefault("run_id", run_id)

        from .db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO app_logs (
                    level, source, message, detail,
                    plugin_id, actor_user_id, run_id
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                """,
                (
                    level,
                    source,
                    (message or "")[:2000],
                    json.dumps(merged_detail),
                    plugin_id,
                    actor_user_id,
                    run_id,
                ),
            )
            conn.commit()
    except Exception as e:
        # Never let logging failures crash the caller.
        logger.warning(f"log_job_event failed: {e}")


def log_plugin_event(
    level: str,
    plugin_id: str,
    action: str,
    message: str,
    detail: Optional[dict] = None,
    source: str = "plugin_lifecycle",
    *,
    actor_user_id: Optional[str] = None,
    run_id: Optional[int] = None,
) -> None:
    """B203: convenience wrapper for plugin-related operational events.

    Prefixes message with [plugin_id] action: ... and merges plugin_id +
    action into the structured detail dict. Use instead of log_job_event
    for plugin install/update/lifecycle events so /system/logs filtering
    by plugin works consistently.

    Args:
        level: 'info' | 'warning' | 'error'
        plugin_id: plugin slug (e.g. 'plausible', 'example-plugin') — also
            written to app_logs.plugin_id column (B208).
        action: short verb identifying the lifecycle phase
            (e.g. 'install', 'clone', 'update_check', 'migrate',
             'hook_install', 'hook_uninstall', 'grant', 'hot_reload',
             'auto_connection', 'deploy_key_lookup')
        message: human-readable short summary (truncated at 2000 chars)
        detail: optional structured context — plugin_id and action are
            auto-merged in
        source: app_logs.source tag — pick from the canonical set
            documented on log_job_event
        actor_user_id: B208 — keyword-only. UUID string of the operator
            who triggered this lifecycle event (admin actions only).
        run_id: B208 — keyword-only. job_runs.id when the lifecycle event
            is part of a sync/hook run.
    """
    enriched = {"plugin_id": plugin_id, "action": action}
    if detail:
        enriched.update(detail)
    log_job_event(
        level,
        f"[{plugin_id}] {action}: {message}",
        enriched,
        source=source,
        plugin_id=plugin_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
    )
