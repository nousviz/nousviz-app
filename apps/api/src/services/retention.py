"""
B279 (v0.9.11.17) — automatic retention policies.

Defines the canonical POLICIES registry (table → field → predicate →
default retention days) and the SQL composer that turns a policy +
operator-tuned threshold into a parameterized DELETE.

Defense in depth:
  - Table and field names live ONLY in this code module — never
    user-supplied. The maintenance API accepts a policy_key string
    that's looked up against POLICIES_BY_KEY; unknown keys are
    rejected before any SQL is composed.
  - Identifier safety net: every policy's table + field is validated
    against `_SAFE_IDENT` (matches the validator pattern used elsewhere
    in the codebase — see plugins.py).
  - Per-policy paused flag is the kill switch. The cron worker reads
    paused state from `system_retention_overrides` on every tick;
    paused policies don't run, regardless of any other state.
  - DELETE is batched at MAX_DELETE_BATCH_SIZE rows per execution to
    bound the lock window. The cron loop re-runs the policy until the
    batch returns < MAX_DELETE_BATCH_SIZE, so a one-time backlog of
    millions still drains across a few daily ticks rather than one
    long-locked sweep.

Per operator decision 2026-05-04: every policy ships paused. First
deploy is a no-op. The seed migration (064) inserts each policy with
paused=TRUE. Operator flips them on from /settings/maintenance.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from psycopg2 import sql as pg_sql

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.services.retention")


# ── Policy registry ─────────────────────────────────────────────────


@dataclass(frozen=True)
class RetentionPolicy:
    """Canonical retention policy definition.

    `key` is the operator-facing identifier (also the PK of
    system_retention_overrides). It's a string rather than (table,
    field) so we can encode multiple policies on the same table with
    different `additional_where` clauses (e.g. `job_runs:success` vs
    `job_runs:failure`).
    """
    key: str
    table: str
    field: str
    additional_where: str
    default_days: int
    description: str


POLICIES: list[RetentionPolicy] = [
    RetentionPolicy(
        key="app_logs",
        table="app_logs",
        field="created_at",
        additional_where="",
        default_days=30,
        description="API + plugin event logs",
    ),
    RetentionPolicy(
        key="auth_audit",
        table="auth_audit",
        field="occurred_at",
        additional_where="",
        default_days=90,
        description="Authentication + RBAC audit (compliance)",
    ),
    RetentionPolicy(
        key="health_log",
        table="health_log",
        field="created_at",
        additional_where="",
        default_days=30,
        description="Health-check history",
    ),
    RetentionPolicy(
        key="activity_events",
        table="activity_events",
        field="created_at",
        additional_where="",
        default_days=30,
        description="User activity (annotations, edits, etc.)",
    ),
    RetentionPolicy(
        key="job_runs:success",
        table="job_runs",
        field="started_at",
        additional_where="status = 'success'",
        default_days=7,
        description="Successful job runs",
    ),
    RetentionPolicy(
        key="job_runs:failure",
        table="job_runs",
        field="started_at",
        additional_where="status IN ('error','cancelled','timeout','skipped')",
        default_days=30,
        description="Failed / cancelled / timed-out job runs",
    ),
    RetentionPolicy(
        key="share_access_log",
        table="share_access_log",
        field="accessed_at",
        additional_where="",
        default_days=90,
        description="Share-access tracking",
    ),
    RetentionPolicy(
        key="user_sessions:expired",
        table="user_sessions",
        field="expires_at",
        additional_where="expires_at < now()",
        default_days=0,
        description="Expired user sessions (immediate purge)",
    ),
    RetentionPolicy(
        key="password_reset_tokens:expired",
        table="password_reset_tokens",
        field="expires_at",
        additional_where="expires_at < now()",
        default_days=0,
        description="Expired password-reset tokens (immediate purge)",
    ),
]

POLICIES_BY_KEY: dict[str, RetentionPolicy] = {p.key: p for p in POLICIES}


class PolicyPausedError(RuntimeError):
    """Raised by execute_policy when paused=True and force_run=False.

    Distinguished from generic RuntimeError so run_all_unpaused can
    bucket it as 'paused' (expected, no audit log) vs 'error' (failure
    that needs operator attention).
    """


# DELETE batch size cap. Per-tick lock window stays short; the cron
# worker re-runs the same policy in a loop until the batch returns
# fewer than this number of rows.
MAX_DELETE_BATCH_SIZE = 100_000

# Identifier safety net — even though POLICIES is a code constant,
# defense in depth: validate every table and field against this regex
# before composing SQL. Catches accidental future edits that introduce
# a table or column name with whitespace or punctuation.
_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifiers(policy: RetentionPolicy) -> None:
    if not _SAFE_IDENT.match(policy.table):
        raise ValueError(f"Unsafe table identifier in policy {policy.key!r}: {policy.table!r}")
    if not _SAFE_IDENT.match(policy.field):
        raise ValueError(f"Unsafe field identifier in policy {policy.key!r}: {policy.field!r}")


# Validate the registry once at import time so a misconfiguration
# breaks the worker immediately, not on first cron fire.
for _p in POLICIES:
    _validate_identifiers(_p)


# ── State helpers ───────────────────────────────────────────────────


@dataclass
class PolicyState:
    """Runtime state for one policy — merges code-side defaults with the
    overrides row (or default-paused if no row exists yet)."""
    key: str
    table: str
    field: str
    description: str
    retention_days: int
    paused: bool
    rows_total: int
    rows_would_prune: int
    last_run_at: Optional[str]
    last_run_rows_deleted: Optional[int]
    last_run_error: Optional[str]
    updated_at: Optional[str]


def _ts_iso(ts) -> Optional[str]:
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def _table_exists(cur, table: str) -> bool:
    """Best-effort regclass check. Returns False if the table is missing."""
    try:
        cur.execute("SELECT to_regclass(%s)", (table,))
        row = cur.fetchone()
        return row is not None and row[0] is not None
    except Exception:
        return False


def _build_where(policy: RetentionPolicy, days: int) -> tuple[pg_sql.SQL, list]:
    """Compose the WHERE clause used by both COUNT preview and DELETE.

    Returns (sql, params). Identifier interpolation uses
    psycopg2.sql.Identifier; the days value is a parameter.

    For days > 0:  `<field> < now() - interval '<days> days' [AND <additional_where>]`
    For days = 0:  `<additional_where>` only (caller supplies an
                   immediate-purge predicate via additional_where).
    """
    field_id = pg_sql.Identifier(policy.field)
    parts: list[pg_sql.Composable] = []
    params: list = []

    if days > 0:
        parts.append(
            pg_sql.SQL("{field} < now() - make_interval(days => %s)").format(field=field_id)
        )
        params.append(int(days))

    if policy.additional_where:
        # additional_where is a code-constant string; safe to inline as
        # raw SQL. Validated indirectly because it's never user-supplied.
        parts.append(pg_sql.SQL(policy.additional_where))

    if not parts:
        # retention_days=0 with no additional_where would mean "delete
        # everything" — refuse, callers must supply a predicate.
        raise ValueError(
            f"Policy {policy.key!r} would match every row "
            f"(retention_days=0 and additional_where empty). Refusing."
        )

    return pg_sql.SQL(" AND ").join(parts), params


def get_policies_state() -> list[PolicyState]:
    """Compose code-side POLICIES with per-policy overrides + live counts.

    Each policy gets two SELECTs against the target table: rows_total
    (raw count or filtered by additional_where) and rows_would_prune
    (rows matching the full WHERE built from the current threshold).
    Tables that don't exist on this install (e.g. fresh deploys before
    a feature ships) skip cleanly with rows_total=0.
    """
    out: list[PolicyState] = []
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # Load overrides into a dict.
        cur.execute(
            """
            SELECT policy_key, retention_days, paused,
                   last_run_at, last_run_rows_deleted, last_run_error,
                   updated_at
            FROM system_retention_overrides
            """
        )
        overrides = {
            row[0]: {
                "retention_days": int(row[1]),
                "paused": bool(row[2]),
                "last_run_at": _ts_iso(row[3]),
                "last_run_rows_deleted": int(row[4]) if row[4] is not None else None,
                "last_run_error": row[5],
                "updated_at": _ts_iso(row[6]),
            }
            for row in cur.fetchall()
        }

        for policy in POLICIES:
            ov = overrides.get(policy.key)
            days = ov["retention_days"] if ov else policy.default_days
            paused = ov["paused"] if ov else True

            rows_total = 0
            rows_would_prune = 0
            if _table_exists(cur, policy.table):
                # rows_total: bounded by additional_where (so e.g.
                # "successful runs" total, not all runs).
                count_sql_parts: list[pg_sql.Composable] = [
                    pg_sql.SQL("SELECT COUNT(*) FROM {tbl}").format(
                        tbl=pg_sql.Identifier(policy.table),
                    ),
                ]
                if policy.additional_where:
                    count_sql_parts.append(
                        pg_sql.SQL(" WHERE ") + pg_sql.SQL(policy.additional_where)
                    )
                try:
                    cur.execute(pg_sql.Composed(count_sql_parts))
                    r = cur.fetchone()
                    rows_total = int(r[0] or 0) if r else 0
                except Exception as e:
                    logger.warning(f"rows_total count failed for {policy.key}: {e}")

                # rows_would_prune: full WHERE.
                try:
                    where_sql, params = _build_where(policy, days)
                    prune_sql = pg_sql.SQL("SELECT COUNT(*) FROM {tbl} WHERE ").format(
                        tbl=pg_sql.Identifier(policy.table),
                    ) + where_sql
                    cur.execute(prune_sql, params)
                    r = cur.fetchone()
                    rows_would_prune = int(r[0] or 0) if r else 0
                except Exception as e:
                    logger.warning(f"rows_would_prune count failed for {policy.key}: {e}")

            out.append(PolicyState(
                key=policy.key,
                table=policy.table,
                field=policy.field,
                description=policy.description,
                retention_days=days,
                paused=paused,
                rows_total=rows_total,
                rows_would_prune=rows_would_prune,
                last_run_at=ov["last_run_at"] if ov else None,
                last_run_rows_deleted=ov["last_run_rows_deleted"] if ov else None,
                last_run_error=ov["last_run_error"] if ov else None,
                updated_at=ov["updated_at"] if ov else None,
            ))
    return out


def set_policy_state(
    policy_key: str,
    *,
    retention_days: Optional[int] = None,
    paused: Optional[bool] = None,
    by_user: Optional[str] = None,
) -> None:
    """Update an override row. Inserts if missing (UPSERT)."""
    if policy_key not in POLICIES_BY_KEY:
        raise KeyError(f"Unknown policy key: {policy_key!r}")
    if retention_days is not None and (retention_days < 0 or retention_days > 3650):
        raise ValueError("retention_days must be in [0, 3650]")

    fields: list[str] = []
    values: list = []
    if retention_days is not None:
        fields.append("retention_days")
        values.append(int(retention_days))
    if paused is not None:
        fields.append("paused")
        values.append(bool(paused))
    if not fields:
        return  # no-op

    fields.append("updated_by")
    values.append(by_user)
    fields.append("updated_at")
    values.append(None)  # placeholder for now()

    set_clauses = ", ".join(
        f"{f} = now()" if f == "updated_at" else f"{f} = %s"
        for f in fields
    )

    insert_fields = ["policy_key"] + [f for f in fields if f != "updated_at"]
    insert_values = [policy_key] + [v for f, v in zip(fields, values) if f != "updated_at"]
    insert_placeholders = ", ".join(["%s"] * len(insert_fields))

    update_values = [v for f, v in zip(fields, values) if f != "updated_at"]

    # If retention_days isn't being set on insert, fall back to the policy default.
    if retention_days is None:
        insert_fields.append("retention_days")
        insert_values.append(POLICIES_BY_KEY[policy_key].default_days)
        insert_placeholders = ", ".join(["%s"] * len(insert_fields))

    sql = f"""
        INSERT INTO system_retention_overrides ({', '.join(insert_fields)})
        VALUES ({insert_placeholders})
        ON CONFLICT (policy_key) DO UPDATE SET {set_clauses}
    """

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, insert_values + update_values)
        conn.commit()


def _record_last_run(
    policy_key: str,
    rows_deleted: int,
    error: Optional[str] = None,
) -> None:
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE system_retention_overrides
            SET last_run_at = now(),
                last_run_rows_deleted = %s,
                last_run_error = %s
            WHERE policy_key = %s
            """,
            (int(rows_deleted), error, policy_key),
        )
        conn.commit()


def execute_policy(
    policy_key: str,
    *,
    force_run: bool = False,
    max_total: Optional[int] = None,
) -> int:
    """Run the DELETE for one policy. Returns total rows deleted.

    Iterates DELETE in batches of MAX_DELETE_BATCH_SIZE so the lock
    window stays short. Stops when a batch returns < batch size, or
    when `max_total` rows have been pruned across batches.

    Raises:
        KeyError if policy_key is unknown.
        RuntimeError if the policy is paused and force_run is False.
    """
    if policy_key not in POLICIES_BY_KEY:
        raise KeyError(f"Unknown policy key: {policy_key!r}")
    policy = POLICIES_BY_KEY[policy_key]

    # Look up runtime state.
    days = policy.default_days
    paused = True
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT retention_days, paused FROM system_retention_overrides WHERE policy_key = %s",
            (policy_key,),
        )
        row = cur.fetchone()
        if row:
            days, paused = int(row[0]), bool(row[1])

    if paused and not force_run:
        raise PolicyPausedError(f"Policy {policy_key!r} is paused; use force_run to override")

    where_sql, where_params = _build_where(policy, days)

    # Batched DELETE. ctid subselect is the standard PostgreSQL idiom
    # for capping a DELETE with LIMIT (which the DELETE statement
    # itself doesn't support).
    delete_sql = pg_sql.SQL(
        "DELETE FROM {tbl} WHERE ctid IN ("
        "SELECT ctid FROM {tbl} WHERE "
    ).format(tbl=pg_sql.Identifier(policy.table)) + where_sql + pg_sql.SQL(
        " LIMIT %s)"
    )

    total_deleted = 0
    while True:
        batch_size = MAX_DELETE_BATCH_SIZE
        if max_total is not None:
            remaining = max_total - total_deleted
            if remaining <= 0:
                break
            batch_size = min(batch_size, remaining)

        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(delete_sql, where_params + [batch_size])
            n = cur.rowcount
            conn.commit()

        total_deleted += max(0, n)
        if n < batch_size:
            break

    # ANALYZE so the planner picks up freed space.
    if total_deleted > 0:
        try:
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    pg_sql.SQL("ANALYZE {tbl}").format(tbl=pg_sql.Identifier(policy.table))
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"ANALYZE failed for {policy.table}: {e}")

    return total_deleted


def run_all_unpaused() -> dict[str, int | str]:
    """Iterate POLICIES and run each that's currently unpaused.

    Returns a {policy_key: rows_deleted | "paused" | "error: <name>"} map.
    Per-policy failures don't abort the run — the worker logs each
    error to the overrides row's last_run_error column and continues.
    """
    summary: dict[str, int | str] = {}
    for policy in POLICIES:
        try:
            n = execute_policy(policy.key)
            summary[policy.key] = n
            _record_last_run(policy.key, n, error=None)
        except PolicyPausedError:
            # paused — expected, not an error
            summary[policy.key] = "paused"
        except Exception as e:
            err = f"{e.__class__.__name__}: {str(e)[:300]}"
            summary[policy.key] = f"error: {err}"
            try:
                _record_last_run(policy.key, 0, error=err)
            except Exception:
                pass
            logger.warning(f"retention policy {policy.key} failed: {err}")
    return summary
