"""
nousviz_sdk.logging — Structured logging for plugin authors (B140 / v0.9.2).

Plugin authors emit log events that land in `/system/logs` (the
`app_logs` table) with the plugin's source tag. Levels above DEBUG land
in app_logs; DEBUG-level stays in pm2 stdout/stderr.

Usage:

    from nousviz_sdk.logging import log_event

    log_event("error", "Failed to sync customer data",
              detail={"customer_id": 12345, "retry_count": 3})

# Levels

  - "info"  → app_logs row at level=info
  - "warn"  → app_logs row at level=warning
  - "error" → app_logs row at level=error

# How it works

In the API process: a `DBLogHandler` is attached to the
`nousviz.plugin.<plugin_id>` logger namespace by the API's
`setup_db_logging()`. `log_event` emits through Python's logging,
the handler reads `record.detail` and writes a structured row.

In a plugin sync/hook subprocess (B238, v0.9.10.1): the worker
doesn't run `setup_db_logging`, so no `DBLogHandler` is attached.
`log_event` detects the missing handler and writes directly to
`app_logs` via `nousviz_sdk.get_pg_conn()` (broker-resolved as the
`nousviz_plugin` role, which has INSERT permission on `app_logs`).
The contract is the same in both contexts: rows land at
`source='plugin'`, visible at `/system/logs?source=plugin`.

# Test harness fallback

When called outside a NousViz context (no `NOUSVIZ_PLUGIN_ID` env var,
e.g., in pytest under `nousviz_sdk.testing.use_test_credentials`),
`log_event` logs to stderr only. No exception, no DB write. Tests don't
need to mock the logger.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

_LEVEL_MAP = {
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

# Lowercase database-side level strings. app_logs.level holds these
# verbatim ('info' | 'warning' | 'error') — matches the LogsPanel
# filter UI and existing log_job_event writes.
_DB_LEVEL_MAP = {
    "info": "info",
    "warn": "warning",
    "warning": "warning",
    "error": "error",
}


# Per-process cache. None = haven't checked. False = checked, no handler.
# True is intentionally absent: when a handler IS attached we just stay
# on the logger path forever — no perf concern. We only cache the False
# case (subprocess, no handler) because each call would otherwise re-walk
# the logger chain. Test harnesses (pytest's caplog) attach handlers
# late, so a True-cache would defeat tests that add handlers after first
# log_event call.
_handler_attached_cache: Optional[bool] = None


def _has_db_log_handler(plugin_id: str) -> bool:
    """Walk the full logger chain looking for a `DBLogHandler` (or
    a similarly DB-aware handler) attached anywhere along the chain.

    Crucially: a plain StreamHandler at root does NOT count — that's
    just stderr output, which is exactly what we want to bypass with
    the direct-write path. We check for handlers whose class name is
    'DBLogHandler' (the API process's app_logs writer) or whose class
    matches a known-DB-routing handler.

    For tests: pytest caplog uses `LogCaptureHandler`, which is also
    treated as "DB-routing" for the purposes of this check — tests
    that attach caplog want to verify the logger-path call shape, not
    the direct-write path. Tests that want to verify the direct-write
    path explicitly drop all handlers (see tests/test_sdk_logging_b238.py).

    The detection is by class name (string match) rather than isinstance
    because the SDK can't import DBLogHandler (apps/api/...) — it would
    create a circular dependency and require the API package as a
    runtime dep of the SDK.

    Cache semantics (B238):
    - We only memoize the negative case (no handler). The positive case
      always re-walks because handlers can be attached late.
    - The negative case is the worker-subprocess hot path.
    """
    global _handler_attached_cache

    # Names of handler classes that route through to app_logs (or some
    # other suitable test sink) — not just stderr/stdout.
    _DB_HANDLER_CLASSES = {
        "DBLogHandler",       # apps/api/src/log_handler.py — the production path
        "LogCaptureHandler",  # pytest caplog — tests verify the logger path
    }

    plugin_logger = logging.getLogger(f"nousviz.plugin.{plugin_id}")

    # Walk from the per-plugin logger up to root. If any logger in the
    # chain has a DB-routing handler attached, use the logger path.
    has_db_handler = False
    current = plugin_logger
    while current is not None:
        for handler in current.handlers:
            if type(handler).__name__ in _DB_HANDLER_CLASSES:
                has_db_handler = True
                break
        if has_db_handler:
            break
        current = current.parent

    if has_db_handler:
        # Positive case — clear any cached negative.
        _handler_attached_cache = None
        return True

    # Negative case — memoize. Subsequent calls skip the walk.
    if _handler_attached_cache is False:
        return False
    _handler_attached_cache = False
    return False


def _direct_write_app_logs(
    db_level: str,
    message: str,
    detail: dict[str, Any],
    plugin_id: str,
    run_id: Optional[int],
) -> None:
    """B238 (v0.9.10.1): direct INSERT into app_logs from a plugin
    subprocess that has no DBLogHandler attached.

    Uses nousviz_sdk.get_pg_conn() — broker-resolved to the nousviz_plugin
    role, which has INSERT, SELECT on app_logs (granted by setup.sh /
    deploy-local.sh bootstrap).

    Best-effort: any exception falls through. Caller already wraps this
    in a broader try/except for stderr fallback. Doesn't raise.
    """
    import json
    # Late import — get_pg_conn requires the broker socket path to be
    # set in the env, which is true in plugin subprocess context.
    from .db import get_pg_conn

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO app_logs (level, source, message, detail, plugin_id, run_id)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                db_level,
                "plugin",
                message[:2000],  # match log_events.py's truncation
                json.dumps(detail),
                plugin_id,
                run_id,
            ),
        )
        conn.commit()


def log_event(
    level: str,
    message: str,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Emit a structured log event for the current plugin.

    Args:
        level: One of "info", "warn", "error".
        message: Human-readable message string.
        detail: Optional dict of structured fields. Lands in
                `app_logs.detail` as JSONB.
    """
    log_level = _LEVEL_MAP.get(level.lower(), logging.INFO)
    db_level = _DB_LEVEL_MAP.get(level.lower(), "info")

    plugin_id = os.environ.get("NOUSVIZ_PLUGIN_ID", "").strip()
    if not plugin_id:
        # Test-harness / standalone fallback: log to stderr only, no DB.
        print(
            f"[nousviz_sdk] {level.upper()} (no NOUSVIZ_PLUGIN_ID): {message}",
            file=sys.stderr,
        )
        return

    # Build the structured detail. Always include plugin_id for back-
    # compat with operators querying detail->>'plugin_id'.
    detail_dict: dict[str, Any] = dict(detail) if detail else {}
    detail_dict.setdefault("plugin_id", plugin_id)

    # Branch on whether the DBLogHandler is attached:
    # - API process: handler attached → emit through Python logging.
    # - Subprocess: no handler → direct INSERT into app_logs.
    if _has_db_log_handler(plugin_id):
        # Existing path: hand off to the DBLogHandler via the logger
        # namespace. The handler reads record.detail and writes the row.
        logger = logging.getLogger(f"nousviz.plugin.{plugin_id}")
        extra: dict[str, Any] = {
            "source_override": "plugin",
            "detail": detail_dict,
        }
        logger.log(log_level, message, extra=extra)
        return

    # B238: subprocess path — direct DB write.
    run_id_raw = os.environ.get("NOUSVIZ_JOB_RUN_ID", "").strip()
    run_id: Optional[int] = None
    if run_id_raw:
        try:
            run_id = int(run_id_raw)
        except ValueError:
            run_id = None

    try:
        _direct_write_app_logs(db_level, message, detail_dict, plugin_id, run_id)
    except Exception as exc:  # noqa: BLE001 — never raise from log_event
        # Fall through to stderr. The broad except is intentional: a
        # logging failure must never break plugin code. Operators see
        # the event in pm2 stderr (and thus job_runs.details.stderr_tail).
        print(
            f"[nousviz_sdk] {level.upper()} (db write failed: {exc}): {message}",
            file=sys.stderr,
        )


__all__ = ["log_event"]
