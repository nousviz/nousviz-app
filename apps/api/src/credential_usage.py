"""
B342 (v1.0.8) — credential usage telemetry.

What a credential read records, and what it no longer records:

* `credentials.last_used_at / last_used_by` — still set on every read, but
  only rewritten when the stored value is older than LAST_USED_THROTTLE_SEC,
  in one statement for all credentials of the read (no row churn under load).
* `credential_usage_daily` — one row per credential, per day, per accessor,
  counting reads. Bounded: reading one credential a million times a day is
  still one row.
* `credential_audit_log` — events only. A bulk or broker read writes ONE
  `fetch` row (who, which run, how many keys, scoped or full); credential
  lifecycle (created / rotated / deleted / decrypt_failed) is written where
  it happens. Before B342 every read wrote one `used` row per credential.

Telemetry never breaks a read: it runs after the read, in its own
transaction, and a failure logs one warning for the whole call.

Accessors are low-cardinality labels (`api:<plugin>`, `broker:<plugin>`,
`settings_read`) so the daily table stays small; the run id goes on the
`fetch` audit row and in `last_used_by`.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from .db import get_pg_conn

logger = logging.getLogger("nousviz.credential_usage")

LAST_USED_THROTTLE_SEC = 60


def record_reads(credential_ids: Iterable[str], accessor: str, last_used_by: Optional[str] = None,
                 *, plugin_id: Optional[str] = None) -> None:
    """Count one read of each credential for `accessor` today and refresh
    `last_used_*` (throttled). Never raises."""
    ids = sorted({str(i) for i in credential_ids if i})   # sorted: same lock order for concurrent calls
    if not ids:
        return
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE credentials
                   SET last_used_at = now(), last_used_by = %s
                 WHERE id = ANY(%s::uuid[])
                   AND (last_used_at IS NULL
                        OR last_used_at < now() - make_interval(secs => %s))
                """,
                (last_used_by or accessor, ids, LAST_USED_THROTTLE_SEC),
            )
            cur.execute(
                """
                INSERT INTO credential_usage_daily AS u (credential_id, day, accessor, reads, first_at, last_at)
                SELECT id, current_date, %s, 1, now(), now()
                  FROM unnest(%s::uuid[]) AS id
                ON CONFLICT (credential_id, day, accessor)
                DO UPDATE SET reads = u.reads + 1, last_at = now()
                """,
                (accessor, ids),
            )
    except Exception as exc:  # noqa: BLE001 — telemetry must not fail the read
        logger.warning(
            "credential usage telemetry failed for %s (%d credentials, accessor=%s): %s",
            plugin_id or "?", len(ids), accessor, exc,
            extra={"plugin_id": plugin_id} if plugin_id else None,
        )


def record_event(connection_id: Optional[str], action: str, performed_by: str, detail: str,
                 *, credential_id: Optional[str] = None, plugin_id: Optional[str] = None) -> None:
    """One `credential_audit_log` row (a `fetch`, `decrypt_failed`,
    `access_denied`, ...). Never raises."""
    if not connection_id:
        return
    try:
        with get_pg_conn() as conn:
            conn.cursor().execute(
                """
                INSERT INTO credential_audit_log (credential_id, connection_id, action, performed_by, detail)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (credential_id, connection_id, action, performed_by, detail),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "credential audit event %s failed for %s: %s", action, plugin_id or "?", exc,
            extra={"plugin_id": plugin_id} if plugin_id else None,
        )


__all__ = ["LAST_USED_THROTTLE_SEC", "record_event", "record_reads"]
