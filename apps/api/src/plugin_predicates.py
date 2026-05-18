"""
Plugin predicate resolver — shared between P119 (declarative actions) and
P121 (setup checklist).

Predicates are a closed allowlist of named DB-state questions. Plugins
reference them by name in `plugin.yaml` (e.g. `disabled_when: no_credentials`,
`done_if: first_sync_success`). Core resolves them server-side when
returning plugin details to the UI — plugins never author the logic.

Adding a new predicate: register it in `_PREDICATES` below and document it
in `docs/plugin-architecture.md`. The allowlist is deliberately small to
keep the contract stable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from .db import get_pg_conn

logger = logging.getLogger("nousviz.api.plugin_predicates")

# B147 (v0.9.3): scheduler polls every ~30s and refreshes the registry
# row's updated_at on each pass. If the timestamp is older than 5 min,
# either the scheduler has crashed or the row is otherwise stale —
# treat the schedule as inactive.
_SCHEDULER_FRESHNESS_SEC = 300.0


# ── Predicate implementations ─────────────────────────────────────────


def _has_credentials(plugin_id: str) -> bool:
    """True iff at least one credential row exists for this plugin.

    Plugin connections use the naming convention
    `connections.name = "plugin:{plugin_id}"` (see plugin_credentials.py).
    """
    conn_name = f"plugin:{plugin_id}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM credentials c
                JOIN connections conn ON c.connection_id = conn.id
                WHERE conn.name = %s
            )
            """,
            (conn_name,),
        )
        (exists,) = cur.fetchone()
        return bool(exists)


def _no_credentials(plugin_id: str) -> bool:
    return not _has_credentials(plugin_id)


def _sync_in_progress(plugin_id: str) -> bool:
    """True iff there is a queued/running/cancelling sync job for this plugin."""
    job_id = f"sync:{plugin_id}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM job_runs
                WHERE job_id = %s
                  AND status IN ('queued', 'running', 'cancelling')
            )
            """,
            (job_id,),
        )
        (exists,) = cur.fetchone()
        return bool(exists)


def _first_sync_success(plugin_id: str) -> bool:
    """True iff at least one `sync:<plugin>` run has status=success."""
    job_id = f"sync:{plugin_id}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM job_runs
                WHERE job_id = %s AND status = 'success'
            )
            """,
            (job_id,),
        )
        (exists,) = cur.fetchone()
        return bool(exists)


def _no_prior_sync(plugin_id: str) -> bool:
    return not _first_sync_success(plugin_id)


def _last_test_success(plugin_id: str) -> bool:
    """True iff the most recent job_runs row for this plugin has status=success.

    Considers both `sync:<plugin>` and `hook:<plugin>:*` runs — any of the
    plugin's terminal events qualify, most-recent wins.
    """
    like = f"%:{plugin_id}:%"
    sync_job = f"sync:{plugin_id}"
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status
            FROM job_runs
            WHERE job_id = %s OR job_id LIKE %s
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST
            LIMIT 1
            """,
            (sync_job, like),
        )
        row = cur.fetchone()
        if not row:
            return False
        return row[0] == "success"


def _schedule_active(plugin_id: str) -> bool:
    """True iff the sync scheduler has registered this plugin and its
    registry row is fresh.

    B147 (v0.9.3): semantics shifted from "grep pm2/crontab" to
    "sync_schedule_registry has a row updated within freshness window."
    The scheduler refreshes updated_at on every poll (~30s); a healthy
    scheduler keeps the predicate true. If the scheduler has been dead
    for >5 min, the predicate flips false — visible to operators via the
    setup checklist's `schedule_active` item.

    The check also requires `last_error IS NULL` so that a plugin with a
    bad cron expression doesn't show as "scheduled" — the registry row
    still exists (so the operator can see the error via the override UI),
    but the predicate is honest that scheduling isn't working.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT updated_at, last_error
                FROM sync_schedule_registry
                WHERE plugin_id = %s
                """,
                (plugin_id,),
            )
            row = cur.fetchone()
        if not row:
            return False
        updated_at, last_error = row
        if last_error:
            return False
        if updated_at is None:
            return False
        age = (datetime.now(timezone.utc) - updated_at).total_seconds()
        return age < _SCHEDULER_FRESHNESS_SEC
    except Exception as exc:
        logger.warning("schedule_active check failed for %s: %s", plugin_id, exc)
        return False


# ── Allowlist ─────────────────────────────────────────────────────────


_PREDICATES: dict[str, Callable[[str], bool]] = {
    # P119 (actions): disabled_when / visible_when
    "no_credentials":     _no_credentials,
    "has_credentials":    _has_credentials,
    "sync_in_progress":   _sync_in_progress,
    "no_prior_sync":      _no_prior_sync,
    "first_sync_success": _first_sync_success,
    "backfill_running":   _sync_in_progress,  # readability alias
    # P121 (setup checklist): done_if
    "credentials_saved":  _has_credentials,   # readability alias
    "last_test_success":  _last_test_success,
    "schedule_active":    _schedule_active,
}


ALLOWED_PREDICATES: frozenset[str] = frozenset(_PREDICATES.keys())


# ── Public API ────────────────────────────────────────────────────────


def is_valid_predicate(name: str) -> bool:
    """Used by manifest validation at install time."""
    return name in _PREDICATES


def resolve(plugin_id: str, name: str) -> bool:
    """Resolve a single predicate. Unknown predicates return False (defensive —
    manifest validation should have caught them at install time).
    """
    fn = _PREDICATES.get(name)
    if fn is None:
        logger.warning("resolve() called with unknown predicate %r for %s", name, plugin_id)
        return False
    try:
        return fn(plugin_id)
    except Exception as exc:
        logger.warning("predicate %s failed for %s: %s", name, plugin_id, exc)
        return False


def resolve_all(plugin_id: str, names: list[str]) -> dict[str, bool]:
    """Resolve multiple predicates for a plugin in one shot. Caller deduplicates."""
    seen: dict[str, bool] = {}
    for name in names:
        if name in seen:
            continue
        seen[name] = resolve(plugin_id, name)
    return seen
