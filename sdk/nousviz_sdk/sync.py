"""
BaseSyncScript for NousViz plugins.

Usage:
    from nousviz_sdk.sync import BaseSyncScript

    class MyPluginSync(BaseSyncScript):
        plugin_id = "my-plugin"

        def run(self, since=None):
            creds = self.get_credentials()
            api_key = creds.get("api_key")
            # ... fetch data, write to Postgres ...
            self.log_sync_result(rows_synced=1234)

    if __name__ == "__main__":
        MyPluginSync().main()

Status tracking:
    Every invocation via main() writes a row to the job_runs table.
    The jobs UI, launchpad, sidebar, and plugin detail page all read
    status from job_runs. Plugin authors don't need to write status
    explicitly — log_sync_result() is optional and only used to attach
    row counts or extra detail to the in-flight run.
"""

import json
import logging
import os
import argparse
import traceback
from datetime import datetime, timezone
from typing import Optional


class BaseSyncScript:
    """
    Base class for NousViz plugin sync scripts.

    Subclasses must set:
    - plugin_id (str): the plugin slug, e.g. "my-plugin"

    Subclasses must implement:
    - run(since=None): fetch data and write to plugin tables.
      `since` is a datetime of the last successful sync (incremental mode),
      or None for a full sync.
    """

    plugin_id: str = ""

    def __init__(self):
        self.logger = logging.getLogger(f"nousviz.sync.{self.plugin_id}")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._run_id: Optional[int] = None
        self._rows_synced: int = 0
        self._rows_failed: int = 0
        self._details: dict = {}

    def get_credentials(self) -> dict:
        """
        Return all credentials for this plugin as a dict {key: value}.
        Subclasses override this to read their own credential keys from
        env vars (injected by the sync runner) or CredentialManager.
        """
        return {}

    def run(self, since: Optional[datetime] = None):
        """
        Execute the sync. Called by main().

        Args:
            since: datetime of the last successful sync (incremental mode).
                   None = full sync from the beginning.

        Subclasses must implement this method.
        """
        del since  # signature documents the contract; base raises
        raise NotImplementedError(f"{self.__class__.__name__}.run() is not implemented")

    def log_sync_result(
        self,
        rows_synced: int = 0,
        rows_failed: int = 0,
        details: Optional[dict] = None,
    ) -> None:
        """
        Attach row counts / extra detail to the in-flight job_runs row.
        Safe to call multiple times — later calls overwrite earlier values.
        If called outside a main()-managed run, logs a warning and records
        an ad-hoc success row so the call isn't silently dropped.
        """
        self._rows_synced = rows_synced
        self._rows_failed = rows_failed
        if details:
            self._details.update(details)
        self.logger.info(
            f"Sync progress: {rows_synced} rows synced, {rows_failed} failed"
        )

        if self._run_id is None:
            # Called without main() wrapping — still record so the call isn't lost
            self._record_standalone_success()

    def get_last_sync_time(self) -> Optional[datetime]:
        """Return the completed_at of the most recent successful sync, or None."""
        try:
            from . import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT completed_at
                    FROM job_runs
                    WHERE job_id = %s AND status = 'success'
                    ORDER BY completed_at DESC
                    LIMIT 1
                    """,
                    (f"sync:{self.plugin_id}",),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            self.logger.warning(f"Could not read last sync time: {e}")
        return None

    # ── job_runs integration ──────────────────────────────────────────

    def _start_run(self, source: str = "cron") -> None:
        """Insert a job_runs row with status='running'. Stores the id for updates.

        B282: when invoked under the async worker, the worker has already
        claimed a job_runs row and exposes its id via NOUSVIZ_JOB_RUN_ID
        (set in apps/worker/src/run_jobs.py before subprocess.Popen). Adopt
        that row instead of inserting a duplicate. The standalone /
        direct-invocation path (no env var) is unchanged.
        """
        inherited = os.environ.get("NOUSVIZ_JOB_RUN_ID", "").strip()
        if inherited:
            try:
                self._run_id = int(inherited)
                self.logger.info(
                    f"Adopted worker-claimed run {self._run_id} (source={source})"
                )
                return
            except ValueError:
                self.logger.warning(
                    f"NOUSVIZ_JOB_RUN_ID={inherited!r} is not an integer; "
                    "falling back to standalone insert"
                )

        try:
            from . import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO job_runs (job_id, started_at, status, source)
                    VALUES (%s, now(), 'running', %s)
                    RETURNING id
                    """,
                    (f"sync:{self.plugin_id}", source),
                )
                row = cur.fetchone()
                if row:
                    self._run_id = int(row[0])
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Could not record sync start: {e}")
            self._run_id = None

    def _complete_run(
        self,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Update the in-flight job_runs row with final status + counts + details."""
        if self._run_id is None:
            return
        try:
            from . import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE job_runs
                    SET completed_at = now(),
                        status = %s,
                        duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000,
                        rows_written = %s,
                        details = %s,
                        error = %s
                    WHERE id = %s
                    """,
                    (
                        status,
                        self._rows_synced,
                        json.dumps({
                            **self._details,
                            "rows_failed": self._rows_failed,
                        }),
                        error,
                        self._run_id,
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Could not record sync completion: {e}")

    def _record_standalone_success(self) -> None:
        """Record a synthetic success row when log_sync_result() is called
        without a main()-managed run. Rare — usually means a plugin is
        invoking run() directly without using main()."""
        try:
            from . import get_pg_conn
            with get_pg_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO job_runs (job_id, started_at, completed_at, status, source, rows_written, details)
                    VALUES (%s, now(), now(), 'success', 'standalone', %s, %s)
                    """,
                    (
                        f"sync:{self.plugin_id}",
                        self._rows_synced,
                        json.dumps({
                            **self._details,
                            "rows_failed": self._rows_failed,
                            "note": "recorded via log_sync_result() without main()",
                        }),
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Could not record standalone sync result: {e}")

    # ── CLI entry point ───────────────────────────────────────────────

    def main(self):
        """CLI entry point. Parses --days / --full flags, runs sync, records status."""
        if not self.plugin_id:
            raise RuntimeError(
                f"{self.__class__.__name__}.plugin_id must be set"
            )

        parser = argparse.ArgumentParser(description=f"{self.plugin_id} sync")
        parser.add_argument("--days", type=int, default=None,
                            help="Backfill N days (overrides incremental)")
        parser.add_argument("--full", action="store_true",
                            help="Full sync from the beginning (no incremental)")
        parser.add_argument("--source", default="cron",
                            help="Run source tag for job_runs (cron | manual | install)")
        args = parser.parse_args()

        since: Optional[datetime] = None
        if args.full or args.days:
            if args.days:
                from datetime import timedelta
                since = datetime.now(timezone.utc) - timedelta(days=args.days)
                self.logger.info(f"Starting sync: last {args.days} days")
            else:
                self.logger.info("Starting full sync")
        else:
            since = self.get_last_sync_time()
            if since:
                self.logger.info(f"Starting incremental sync since {since}")
            else:
                self.logger.info("Starting full sync (no previous sync found)")

        self._start_run(source=args.source)

        # P107: expose the current run_id to nousviz_sdk.jobs helpers
        # so plugins using async primitives (heartbeat, check_cancelled)
        # find the right row without threading the id through their code.
        from . import jobs as _jobs
        _jobs._set_current_run_id(self._run_id)

        try:
            self.run(since=since)
            self._complete_run(status="success")
        except Exception as e:
            err_text = f"{e.__class__.__name__}: {e}"
            self._details["traceback"] = traceback.format_exc()[-2000:]
            self.logger.error(f"Sync failed: {err_text}", exc_info=True)
            self._complete_run(status="error", error=err_text)
            raise
        finally:
            _jobs._set_current_run_id(None)
