"""
Error Sanitization Middleware — prevents leaking internal details to API clients.

Catches unhandled exceptions and returns a safe error message.
Full exception details are logged server-side for debugging.

B131 (v0.9.1): every unhandled 500 from any route lands in `app_logs`
with method, path, exception class, traceback tail. Plugin-route 500s
keep their `source=plugin_route` tag with `plugin_id`; everything else
gets `source=core_route`. Rate-limited per (path, exception_class) to
10/min so a runaway error doesn't drown the log table while still
allowing the first 10 occurrences to land for diagnosis.

Pre-v0.9.1 (P205d in v0.9.0): only plugin-route 500s were logged.
v0.9.1 closes the visibility gap for core routes.

4xx HTTPExceptions (status < 500) are NOT logged — those are client
errors, already in HTTP access logs, not server-side bugs.
"""
from __future__ import annotations

import logging
import re
import time
import traceback
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("nousviz.errors")


# Match /api/plugins/<plugin_id>/... (NOT /api/plugins itself, which is
# a core route returning the plugin list).
_PLUGIN_ROUTE_RE = re.compile(r"^/api/plugins/([a-z0-9][a-z0-9\-_]{0,63})/")


# B131: rate limit keyed by (path, exception_class) — same path raising
# different exception classes count separately, different paths don't
# collide. 10 per minute per key.
#
# B139 (v0.9.2): when an event is suppressed by the rate limit, increment
# _drop_counter[key]. When the next event for that key is allowed through
# (because the window slid), the caller emits a rollup row in app_logs
# saying how many were suppressed. That way operators see the suppression
# in /system/logs instead of silent gaps.
_RATE_WINDOW_SEC = 60.0
_RATE_LIMIT_PER_WINDOW = 10
_rate_lock = Lock()
_rate_timestamps: dict[tuple[str, str], list[float]] = defaultdict(list)
_drop_counter: dict[tuple[str, str], int] = defaultdict(int)


def _should_log_route_error(path: str, exc_class: str) -> tuple[bool, int]:
    """Decide whether to emit an app_logs entry for this (path, exc_class)
    pair right now.

    Returns (allowed, drops_to_report):
      - allowed: True iff the event should be logged
      - drops_to_report: if allowed AND there were prior suppressions for
        this key, the suppressed count to be reported alongside the event.
        Caller emits a single rollup row before its normal log row.
        Always 0 if not allowed.
    """
    now = time.time()
    key = (path, exc_class)
    with _rate_lock:
        stamps = _rate_timestamps[key]
        cutoff = now - _RATE_WINDOW_SEC
        while stamps and stamps[0] < cutoff:
            stamps.pop(0)
        if len(stamps) >= _RATE_LIMIT_PER_WINDOW:
            _drop_counter[key] += 1
            return False, 0
        stamps.append(now)
        # Allowed — drain any pending drop count for this key now that
        # we have a visible event to attach the rollup to.
        drops = _drop_counter.pop(key, 0)
    return True, drops


class ErrorSanitizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as exc:
            # B131: skip 4xx HTTPExceptions — those are application-intentional
            # client errors. Log only HTTPException(>=500). Re-raise so
            # FastAPI's default handler returns the proper response.
            if exc.status_code < 500:
                raise
            path = request.url.path
            method = request.method
            tb = traceback.format_exc()
            logger.error(f"Unhandled HTTPException >=500 on {method} {path}: {exc.detail}")
            self._log_route_500(path, method, exc, tb)
            raise
        except Exception as exc:
            path = request.url.path
            method = request.method
            tb = traceback.format_exc()

            # Log the full exception server-side
            logger.error(f"Unhandled exception on {method} {path}: {exc}")
            logger.error(tb)

            # B131: log every 500 to app_logs — core_route OR plugin_route
            self._log_route_500(path, method, exc, tb)

            # Return a safe message to the client
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An internal error occurred. Please try again or contact support.",
                    "path": path,
                },
            )

    @staticmethod
    def _log_route_500(path: str, method: str, exc: Exception, tb: str) -> None:
        """Write a 500 entry to app_logs with the right source tag and
        rate limiting. Non-fatal: any failure here logs a warning and
        continues — never let observability code mask the original error.

        B139 (v0.9.2): if there were prior suppressions for this
        (path, exc_class) key, emit a rollup row indicating how many
        events were suppressed before logging the current one.
        """
        exc_class = type(exc).__name__
        allowed, drops_to_report = _should_log_route_error(path, exc_class)
        if not allowed:
            return

        match = _PLUGIN_ROUTE_RE.match(path)
        plugin_id = match.group(1) if match else None
        source = "plugin_route" if match else "core_route"

        try:
            from ..log_events import log_job_event

            # B139: rollup row first, attaching context so operators
            # can correlate the suppression with the next visible event.
            if drops_to_report > 0:
                rollup_detail: dict = {
                    "path": path,
                    "exception_class": exc_class,
                    "suppressed_count": drops_to_report,
                    "source": source,
                    "rate_limit_per_window": _RATE_LIMIT_PER_WINDOW,
                    "window_seconds": int(_RATE_WINDOW_SEC),
                }
                try:
                    log_job_event(
                        "warning",
                        (
                            f"Suppressed {drops_to_report} 5xx events for "
                            f"{path} ({exc_class}) due to rate limit"
                        ),
                        rollup_detail,
                        source=source,
                        plugin_id=plugin_id,
                    )
                except Exception as rollup_err:
                    logger.warning(
                        f"Failed to log rate-limit rollup to app_logs: {rollup_err}"
                    )

            detail: dict = {
                "method": method,
                "path": path,
                "exception_class": exc_class,
                "exception_message": str(exc)[:500],
                "traceback_tail": tb[-1500:],
                "source": source,
            }

            log_job_event(
                "error",
                f"500 on {method} {path}: {exc_class}: {str(exc)[:200]}",
                detail,
                source=source,
                plugin_id=plugin_id,
            )
        except Exception as log_err:
            logger.warning(f"Failed to log {source} 500 to app_logs: {log_err}")
