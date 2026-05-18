"""
Database log handler for operator-visible logs (P104, B132 v0.9.1).

Writes structured log entries to the app_logs table.
Only captures INFO+ from specific loggers — DEBUG stays in file logs only.

## Structured detail via `extra=`

B132 (v0.9.1): callers can ride structured fields on a `logger.error()`
or `logger.info()` call by passing `extra={"detail": {...}}` and/or
`extra={"source_override": "..."}`. The handler reads these and writes
them through to `app_logs.detail` / `app_logs.source` respectively.

Example:

    logger.error(
        f"Plugin {slug} failed to load",
        extra={
            "detail": {
                "plugin_id": slug,
                "exception_class": type(exc).__name__,
                "stage": "routes",
            },
            "source_override": "plugin_loader",
        },
        exc_info=True,
    )

Without `extra=`, behavior is identical to pre-v0.9.1: empty detail dict
(plus auto-extracted `error` from `exc_info`), source from logger name
via `SOURCE_MAP`.

This means modules can write structured logs without bypassing the
handler with explicit `log_job_event` calls — there's now exactly one
write path per `app_logs` row.

## Worker process note

This handler is attached to specific loggers in the **API process** by
`setup_db_logging()`. The **worker process** (apps/worker/src/run_jobs.py)
does NOT call setup_db_logging — it uses `log_job_event` directly. That
asymmetry exists because the worker has different lifecycle concerns
and runs without the API's startup hooks.
"""

import logging
import json
import threading

logger = logging.getLogger("nousviz.log_handler")

# Map logger names to source categories
SOURCE_MAP = {
    "nousviz.api.plugins": "plugin_install",
    "nousviz.plugin_loader": "plugin_loader",
    "nousviz.plugin_credentials": "credentials",
    "nousviz.connections": "connections",
    "nousviz.dashboards": "dashboards",
    "nousviz.fusions": "fusions",
    "nousviz.plugin.": "sync",
}


def _get_source(name: str) -> str:
    """Map logger name to a source category."""
    for prefix, source in SOURCE_MAP.items():
        if name.startswith(prefix):
            return source
    return "api"


class DBLogHandler(logging.Handler):
    """
    Logging handler that writes to the app_logs table.

    Thread-safe. Failures are silently ignored to avoid
    cascading errors from the logging system itself.

    Reads `record.detail` and `record.source_override` if present
    (passed via `extra=` on the logging call) to produce structured
    log entries without bypassing this handler.
    """

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        try:
            from .db import get_pg_conn

            # B132: caller can override the auto-derived source via
            # record.source_override (set with `extra={"source_override": ...}`)
            source = getattr(record, "source_override", None) or _get_source(record.name)
            message = self.format(record)

            # B132: caller can pass a structured detail dict via
            # `extra={"detail": {...}}`. Merge with auto-extracted
            # exception info so existing callers keep their `error` field.
            detail: dict = {}
            extra_detail = getattr(record, "detail", None)
            if isinstance(extra_detail, dict):
                detail.update(extra_detail)
            if record.exc_info and record.exc_info[1]:
                detail.setdefault("error", str(record.exc_info[1]))

            # B208 (v0.9.6.1): callers may pass plugin_id / actor_user_id /
            # run_id directly on the LogRecord via `extra={...}`. These get
            # written to the dedicated columns AND merged into detail for
            # back-compat. Keep these explicit — no fishing them out of
            # nested detail dicts.
            plugin_id = getattr(record, "plugin_id", None)
            actor_user_id = getattr(record, "actor_user_id", None)
            run_id = getattr(record, "run_id", None)

            # Pre-B132 contract kept working: if plugin_id was provided via
            # extra, also surface it in detail (existing readers grep this).
            if plugin_id is not None and "plugin_id" not in detail:
                detail["plugin_id"] = plugin_id
            if actor_user_id is not None and "actor_user_id" not in detail:
                detail["actor_user_id"] = actor_user_id
            if run_id is not None and "run_id" not in detail:
                detail["run_id"] = run_id

            with self._lock:
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
                            record.levelname.lower(),
                            source,
                            message[:2000],
                            json.dumps(detail),
                            plugin_id,
                            actor_user_id,
                            run_id,
                        ),
                    )
        except Exception:
            # Never let logging failures crash the application
            pass


def setup_db_logging():
    """Attach the DB log handler to key application loggers."""
    handler = DBLogHandler(level=logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))

    loggers_to_attach = [
        "nousviz.api.plugins",
        "nousviz.plugin_loader",
        "nousviz.plugin_credentials",
        "nousviz.connections",
        "nousviz.dashboards",
        "nousviz.fusions",
        # B140 (v0.9.2): plugin authors call nousviz_sdk.logging.log_event
        # which uses the nousviz.plugin.<plugin_id> logger namespace.
        # Attach the handler to the parent so all plugin-emitted events
        # propagate to app_logs / /system/logs.
        "nousviz.plugin",
    ]

    for name in loggers_to_attach:
        log = logging.getLogger(name)
        log.addHandler(handler)
        log.setLevel(logging.INFO)
