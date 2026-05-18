"""
NousViz Resource Snapshot Worker (B273, v0.9.11.19).

One-shot script invoked daily by PM2 cron_restart at 03:30 UTC. Reads
the same shape served by `/api/system/resources` + `/api/system/diagnostics`,
compacts it to top-20 per section, persists one row to
`system_resources_history`, and prunes rows older than 90 days.

Per memory rule `feedback_check_inflight_before_pg_restart`: this is
write-light (one row per day, one DELETE batch per day). Has no effect
on in-flight syncs.

Usage:
    python3 apps/worker/src/snapshot_resources.py
    python3 apps/worker/src/snapshot_resources.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add repo root so apps.* imports resolve when invoked directly via PM2.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# v0.9.11.22.7: load .env BEFORE importing anything that touches the
# database. PM2 spawns one-shot crons with a slim environment that
# doesn't carry POSTGRES_PASSWORD; without this the worker raises
# "POSTGRES_PASSWORD environment variable is required" on first
# get_pg_conn() call. Mirrors the same pattern in run_alerts.py and
# run_jobs.py.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except Exception:
    # dotenv is a soft dependency — when it's not installed (rare,
    # only in trimmed dev contexts), fall back to whatever the parent
    # env provides. The downstream get_pg_conn() will raise its own
    # clearer error if POSTGRES_PASSWORD is genuinely missing.
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nousviz.snapshot_resources")


def _collect_payload() -> tuple[dict, list[dict]]:
    """Pull resources + diagnostics. Returns (compacted_for_storage,
    full_findings).

    Compacted is what gets persisted to system_resources_history (top-20
    per section, findings reduced to {id, severity}). Full findings
    carry the complete evidence/recommendation/affected payload for the
    B274 alert bridge.

    Imports are local so the script doesn't pay the FastAPI import cost
    just to print --help.
    """
    # Reuse the same in-process collector the API endpoint uses, so the
    # snapshot is bit-for-bit consistent with what the operator sees on
    # /system/resources at the moment the worker runs.
    from apps.api.src.routes.system import _collect_resources_snapshot
    from apps.api.src.services.system_diagnostics import evaluate_diagnostics
    from apps.api.src.services.resources_history import compact_snapshot

    snap = _collect_resources_snapshot()
    findings = evaluate_diagnostics(snap)
    compacted = compact_snapshot(snap, findings, max_per_section=20)
    return compacted, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="NousViz resource snapshot worker")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the snapshot payload and print its size without persisting",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        help="Delete snapshots older than this many days (default 90)",
    )
    args = parser.parse_args()

    logger.info("snapshot_resources starting")
    try:
        payload, full_findings = _collect_payload()
    except Exception as e:
        logger.error("snapshot collection failed: %s", e, exc_info=True)
        return 1

    # Estimate JSONB byte size for size-budget verification. Use the
    # same Decimal/datetime/UUID-tolerant encoder the service uses for
    # the actual persistence call (v0.9.11.19.1: production caught a
    # Decimal serialization failure on first manual run).
    import json
    from apps.api.src.services.resources_history import _json_default
    body = json.dumps(payload, default=_json_default)
    size_kb = len(body) / 1024

    if args.dry_run:
        logger.info(
            "dry-run: payload size = %.1f KB, plugins=%d, syncs=%d, findings=%d",
            size_kb,
            len(payload.get("plugins") or []),
            len(payload.get("syncs") or []),
            len(payload.get("findings") or []),
        )
        # Show the findings list since it's typically small + most-changed.
        for f in payload.get("findings") or []:
            logger.info("  finding: %s (%s)", f.get("id"), f.get("severity"))
        return 0

    from apps.api.src.services.resources_history import (
        insert_snapshot,
        purge_old_snapshots,
    )
    from apps.api.src.log_events import log_job_event

    when = datetime.now(timezone.utc)
    try:
        insert_snapshot(payload, snapshot_at=when)
        deleted = purge_old_snapshots(retention_days=args.retention_days)
    except Exception as e:
        logger.error("snapshot persist failed: %s", e, exc_info=True)
        log_job_event(
            "error",
            f"snapshot_resources: persist failed — {e.__class__.__name__}",
            {"error": str(e)[:300]},
            source="snapshot",
        )
        return 1

    logger.info(
        "snapshot persisted: %.1f KB, %d findings, purged %d old rows",
        size_kb,
        len(payload.get("findings") or []),
        deleted,
    )

    # B274 v0.9.11.20: bridge findings → subscribed webhooks. Snapshot
    # persistence is the priority — if the bridge fails, the snapshot
    # is still durable. Reuses the full findings already collected
    # above (the compacted payload only carries id+severity, which the
    # webhook payload needs more than).
    try:
        from apps.api.src.services.diagnostic_alerts import process_findings
        bridge_summary = process_findings(full_findings)
        logger.info("diagnostic_alerts: %s", bridge_summary)
    except Exception as bridge_e:
        logger.error(
            "diagnostic_alerts dispatch failed (snapshot still persisted): %s",
            bridge_e,
            exc_info=True,
        )

    log_job_event(
        "info",
        f"snapshot_resources: wrote {size_kb:.1f}KB, {len(payload.get('findings') or [])} findings, purged {deleted}",
        {
            "size_kb": round(size_kb, 1),
            "findings_count": len(payload.get("findings") or []),
            "purged_old": deleted,
            "retention_days": args.retention_days,
        },
        source="snapshot",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
