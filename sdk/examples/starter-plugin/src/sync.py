"""
src/sync.py — Starter Plugin Sync Script

Canonical reference for NousViz plugin sync scripts.

Extends BaseSyncScript from the NousViz SDK. Status tracking is automatic:
every invocation via main() writes a row to the job_runs table, visible in
the jobs UI, launchpad, sidebar, and plugin detail page.

Invoked by:
  - POST /api/plugins/starter-plugin/sync   (manual trigger from UI)
  - Worker cron, on the schedule in plugin.yaml sync.schedule
  - Direct CLI: python3 src/sync.py [--full | --days N]

Rules:
  - Only write to tables declared in plugin.yaml databases
  - Never write to core tables or other plugins' tables
  - Use self.log_sync_result(rows_synced=...) to attach counts to the run
  - Unhandled exceptions are caught by main(), recorded to job_runs with
    status='error' + traceback, then re-raised
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add the SDK package dir so `nousviz_sdk` imports resolve.
# When a plugin is installed via pip, this line isn't needed — the SDK is
# on the path already. Keep it here so authors can copy the file and run
# it from any working directory while developing.
_SDK_PKG_PARENT = Path(__file__).resolve().parents[3]  # .../sdk/
if str(_SDK_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_SDK_PKG_PARENT))

from nousviz_sdk.sync import BaseSyncScript
from nousviz_sdk import get_pg_conn


logger = logging.getLogger("nousviz.plugin.starter-plugin.sync")


class StarterPluginSync(BaseSyncScript):
    plugin_id = "starter-plugin"

    def get_credentials(self) -> dict:
        """
        Credentials are injected into os.environ by the NousViz sync runner.
        When a user saves API keys via Settings UI, they're stored AES-256-GCM
        encrypted in the database. At sync time, they're decrypted and injected
        into the process environment.

        Return the subset your sync actually needs.
        """
        return {
            "api_key": os.environ.get("STARTER_API_KEY", ""),
            "host": os.environ.get("STARTER_HOST", ""),
        }

    def fetch_from_source(self, since: Optional[datetime] = None) -> list[dict]:
        """
        Pull data from the external source. Replace this stub with your
        actual fetch logic (REST API call, SQL query, CSV read, etc.).

        Args:
            since: If set, fetch only records updated after this datetime.
                   If None, fetch all records (full sync).

        Returns:
            List of dicts, one per record. Keys must match your table columns.
        """
        creds = self.get_credentials()
        if not creds.get("api_key"):
            self.logger.warning("STARTER_API_KEY not set — returning stub data")

        # Stub: return sample data
        return [
            {"name": "Example Item A", "status": "active", "metadata": {"source": "stub"}},
            {"name": "Example Item B", "status": "inactive", "metadata": {"source": "stub"}},
        ]

    def upsert_items(self, conn, records: list[dict]) -> int:
        """Idempotent write — safe to run multiple times."""
        if not records:
            return 0
        cur = conn.cursor()
        rows = 0
        for record in records:
            cur.execute(
                """
                INSERT INTO starter_items (name, status, metadata)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (name) DO UPDATE
                  SET status   = EXCLUDED.status,
                      metadata = EXCLUDED.metadata
                """,
                (
                    record["name"],
                    record.get("status", "active"),
                    json.dumps(record.get("metadata", {})),
                ),
            )
            rows += 1
        return rows

    def record_sync_event(self, conn, rows_synced: int) -> None:
        """Write a sync event to the plugin-owned audit table. Optional —
        useful for building dashboards that track plugin activity."""
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO starter_events (event_type, detail)
            VALUES ('sync', %s::jsonb)
            """,
            (
                json.dumps({
                    "rows_synced": rows_synced,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }),
            ),
        )

    def run(self, since: Optional[datetime] = None) -> None:
        """
        Main sync entry point. Called by BaseSyncScript.main().

        Raise exceptions to signal failure — main() catches them, records
        status='error' + traceback in job_runs, then re-raises. Do NOT
        swallow exceptions: that makes the run appear successful to the UI.
        """
        with get_pg_conn() as conn:
            records = self.fetch_from_source(since=since)
            self.logger.info(f"Fetched {len(records)} records from source")

            rows_synced = self.upsert_items(conn, records)
            self.logger.info(f"Upserted {rows_synced} rows into starter_items")

            self.record_sync_event(conn, rows_synced)

        # Attach row count to the in-flight job_runs row.
        self.log_sync_result(rows_synced=rows_synced)


if __name__ == "__main__":
    StarterPluginSync().main()
