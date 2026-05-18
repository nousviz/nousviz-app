"""
NousViz Retention Cleanup Worker (B279, v0.9.11.17).

One-shot script invoked daily by PM2 cron_restart at 04:00 UTC. Reads
the POLICIES registry from `apps.api.src.services.retention`, executes
every UNPAUSED policy, and writes a structured summary to `app_logs`.

Per operator decision 2026-05-04: every policy ships paused. First
deploy is a no-op. Operator flips each on from /settings/maintenance.

Usage:
    python3 apps/worker/src/retention_cleanup.py
    python3 apps/worker/src/retention_cleanup.py --dry-run
    python3 apps/worker/src/retention_cleanup.py --policy <key>
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add repo root so apps.* imports resolve when the script is invoked
# directly via PM2 (cwd may differ).
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# v0.9.11.22.7: load .env BEFORE importing anything that touches the
# database. PM2 spawns one-shot crons with a slim environment; same
# fix as snapshot_resources.py and the pattern run_alerts.py /
# run_jobs.py established.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

from apps.api.src.services.retention import (  # noqa: E402
    POLICIES,
    POLICIES_BY_KEY,
    execute_policy,
    get_policies_state,
    run_all_unpaused,
)
from apps.api.src.log_events import log_job_event  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nousviz.retention_cleanup")


def _print_dry_run() -> None:
    """Show what the cron WOULD do without doing anything."""
    states = get_policies_state()
    print("Retention policies (dry-run):")
    print(f"{'KEY':<35} {'DAYS':>6} {'TABLE':<24} {'ROWS':>10} {'WOULD PRUNE':>12} {'STATUS'}")
    for s in states:
        status = "paused" if s.paused else "active"
        print(
            f"{s.key:<35} {s.retention_days:>6} {s.table:<24} "
            f"{s.rows_total:>10,} {s.rows_would_prune:>12,} {status}"
        )


def _run_one(key: str) -> int:
    if key not in POLICIES_BY_KEY:
        print(f"Unknown policy: {key!r}", file=sys.stderr)
        print(f"Known policies: {', '.join(p.key for p in POLICIES)}", file=sys.stderr)
        return 1
    n = execute_policy(key, force_run=True)
    print(f"{key}: deleted {n} rows")
    log_job_event(
        "info",
        f"retention_cleanup: {key} deleted {n} rows (manual run)",
        {"policy_key": key, "rows_deleted": n, "manual": True},
        source="retention",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NousViz retention cleanup worker")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be pruned without running any DELETEs",
    )
    parser.add_argument(
        "--policy",
        help="Run a single policy by key (overrides paused state)",
    )
    args = parser.parse_args()

    if args.dry_run:
        _print_dry_run()
        return 0

    if args.policy:
        return _run_one(args.policy)

    # Default: cron mode. Iterate POLICIES, run each unpaused, summarise.
    logger.info("retention_cleanup starting")
    summary = run_all_unpaused()

    # Headline counts for the structured log entry.
    total_deleted = sum(v for v in summary.values() if isinstance(v, int))
    paused_count = sum(1 for v in summary.values() if v == "paused")
    error_count = sum(1 for v in summary.values() if isinstance(v, str) and v.startswith("error"))
    active_count = len(summary) - paused_count - error_count

    log_job_event(
        "info" if error_count == 0 else "warning",
        (
            f"retention_cleanup: {total_deleted} rows deleted across {active_count} active policies "
            f"({paused_count} paused, {error_count} errored)"
        ),
        {
            "summary": summary,
            "total_deleted": total_deleted,
            "active": active_count,
            "paused": paused_count,
            "errors": error_count,
        },
        source="retention",
    )

    logger.info(
        f"retention_cleanup done: total_deleted={total_deleted} "
        f"active={active_count} paused={paused_count} errors={error_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
