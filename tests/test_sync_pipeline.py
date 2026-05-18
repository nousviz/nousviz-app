"""
Sync pipeline integration tests (P106 / B118).

Covers:
- BaseSyncScript writes job_runs rows on success and failure.
- Manual trigger (/api/plugins/:id/sync) writes job_runs rows.
- jobs.py reader returns accurate last_sync.
- No dead paths remain (no reads/writes to sync_log or _last_sync).

Requires a running Postgres (reads NOUSVIZ_* / POSTGRES_* env vars from .env).

Run: `pytest tests/test_sync_pipeline.py -v`

These are integration tests, not unit tests — they touch the real DB.
They do NOT require an API server running; the manual-trigger test invokes
the route handler in-process via its helper functions.
"""

import json
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="module")
def db_conn():
    """Shared Postgres connection for the whole module. Skips if unreachable."""
    try:
        from apps.api.src.db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT to_regclass('job_runs')")
            if cur.fetchone()[0] is None:
                pytest.skip("job_runs table does not exist — apply migrations first")
        yield get_pg_conn
    except Exception as e:
        pytest.skip(f"Postgres not reachable: {e}")


@pytest.fixture
def unique_plugin_id():
    """A per-test plugin_id so parallel tests don't collide."""
    return f"test-sync-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def cleanup_job_runs(db_conn, unique_plugin_id):
    """Remove any job_runs rows for this test's plugin after the test."""
    yield
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM job_runs WHERE job_id = %s",
            (f"sync:{unique_plugin_id}",),
        )
        conn.commit()


# ── BaseSyncScript writes job_runs directly ─────────────────────────────


def _run_sync_subprocess(plugin_id: str, should_fail: bool = False) -> subprocess.CompletedProcess:
    """Invoke a throwaway sync script as a subprocess so it exercises main()
    and argparse like a real plugin would."""
    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from sdk.nousviz_sdk.sync import BaseSyncScript

        class T(BaseSyncScript):
            plugin_id = {plugin_id!r}
            def run(self, since=None):
                {'raise RuntimeError("test failure")' if should_fail else 'self.log_sync_result(rows_synced=42)'}

        T().main()
    """)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, path, "--source=test"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.skip(
    reason=(
        "Tests pre-B205 BaseSyncScript.main() flow where the script wrote "
        "its own job_runs row. In the current async model the worker INSERTs "
        "the queued row before invoking the script, and the script updates "
        "(not creates) it. Rewriting this test needs a worker harness — "
        "out of scope for B217."
    )
)
def test_base_sync_script_writes_success_row(db_conn, unique_plugin_id, cleanup_job_runs):
    result = _run_sync_subprocess(unique_plugin_id, should_fail=False)
    assert result.returncode == 0, f"Subprocess failed: {result.stderr}"

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, rows_written, source, details, exit_code, error
            FROM job_runs
            WHERE job_id = %s
            ORDER BY id DESC LIMIT 1
            """,
            (f"sync:{unique_plugin_id}",),
        )
        row = cur.fetchone()

    assert row is not None, "No job_runs row written"
    status, rows_written, source, details, exit_code, error = row
    assert status == "success"
    assert rows_written == 42
    assert source == "test"
    assert error is None
    # details stored as JSONB — psycopg2 returns it as dict already
    assert isinstance(details, dict)
    assert details.get("rows_failed") == 0


@pytest.mark.skip(
    reason="Same as test_base_sync_script_writes_success_row — pre-B205 standalone-script contract."
)
def test_base_sync_script_writes_error_row(db_conn, unique_plugin_id, cleanup_job_runs):
    result = _run_sync_subprocess(unique_plugin_id, should_fail=True)
    # subprocess should exit non-zero because main() re-raises the exception
    assert result.returncode != 0

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, error, details
            FROM job_runs
            WHERE job_id = %s
            ORDER BY id DESC LIMIT 1
            """,
            (f"sync:{unique_plugin_id}",),
        )
        row = cur.fetchone()

    assert row is not None
    status, error, details = row
    assert status == "error"
    assert "test failure" in (error or "")
    assert "traceback" in details


# ── Manual trigger helpers write job_runs ───────────────────────────────


@pytest.mark.skip(
    reason=(
        "Refers to _start_job_run / _complete_job_run which were removed in "
        "B205 (v0.9.6.0) when sync went fully async. The current contract "
        "is _enqueue_async_run + worker completion; rewriting this test "
        "needs a live worker harness which is out of scope for B217. "
        "Surfaced 2026-05-01 by B217 phase 5 — added to PROMISES as "
        "'restore sync-pipeline coverage post-B205'."
    )
)
def test_manual_trigger_writes_job_runs_row(db_conn, unique_plugin_id, cleanup_job_runs):
    """_start_job_run + _complete_job_run are the functions used by the route.
    Test them directly so we don't need an HTTP server."""
    from apps.api.src.routes.sync import _start_job_run, _complete_job_run

    run_id = _start_job_run(unique_plugin_id)
    assert run_id is not None, "Failed to insert running row"

    _complete_job_run(
        run_id=run_id,
        status="success",
        exit_code=0,
        duration_ms=123,
        details={"mode": "incremental", "stdout_tail": "ok"},
    )

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, exit_code, duration_ms, source, details FROM job_runs WHERE id = %s",
            (run_id,),
        )
        row = cur.fetchone()

    assert row is not None
    status, exit_code, duration_ms, source, details = row
    assert status == "success"
    assert exit_code == 0
    assert duration_ms == 123
    assert source == "manual"
    assert details.get("mode") == "incremental"


@pytest.mark.skip(
    reason="Same as test_manual_trigger_writes_job_runs_row — refers to removed _start_job_run."
)
def test_manual_trigger_handles_failure(db_conn, unique_plugin_id, cleanup_job_runs):
    from apps.api.src.routes.sync import _start_job_run, _complete_job_run

    run_id = _start_job_run(unique_plugin_id)
    _complete_job_run(
        run_id=run_id,
        status="error",
        exit_code=1,
        duration_ms=50,
        details={"mode": "incremental"},
        error="plugin sync exited non-zero",
    )

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, error FROM job_runs WHERE id = %s",
            (run_id,),
        )
        status, error = cur.fetchone()

    assert status == "error"
    assert "non-zero" in error


# ── jobs.py reader returns backfilled + fresh data ───────────────────────


def test_jobs_reader_returns_accurate_last_sync(db_conn, unique_plugin_id, cleanup_job_runs):
    from apps.api.src.routes.jobs import _plugin_last_sync_map

    # Insert a synthetic success row
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO job_runs (job_id, started_at, completed_at, status, source)
            VALUES (%s, now(), now(), 'success', 'test')
            """,
            (f"sync:{unique_plugin_id}",),
        )
        conn.commit()

    result = _plugin_last_sync_map()
    assert unique_plugin_id in result
    assert result[unique_plugin_id]  # ISO string, non-empty


def test_jobs_reader_ignores_failed_runs(db_conn, unique_plugin_id, cleanup_job_runs):
    """Only status='success' rows should surface as last_sync."""
    from apps.api.src.routes.jobs import _plugin_last_sync_map

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO job_runs (job_id, started_at, completed_at, status, source)
            VALUES (%s, now(), now(), 'error', 'test')
            """,
            (f"sync:{unique_plugin_id}",),
        )
        conn.commit()

    result = _plugin_last_sync_map()
    assert unique_plugin_id not in result, "Failed runs must not appear as last_sync"


def test_jobs_reader_falls_back_to_legacy_last_sync(db_conn, unique_plugin_id):
    """Plugins that still write plugin_settings._last_sync (instead of
    job_runs) must still appear in the jobs UI so pre-migration plugins
    aren't misreported as 'Never run'."""
    from apps.api.src.routes.jobs import _plugin_last_sync_map

    legacy_ts = "2026-04-23T21:00:00+00:00"
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO plugin_settings (plugin_id, key, value)
            VALUES (%s, '_last_sync', %s::jsonb)
            """,
            (unique_plugin_id, json.dumps({"timestamp": legacy_ts})),
        )
        conn.commit()

    try:
        result = _plugin_last_sync_map()
        assert unique_plugin_id in result, "Legacy _last_sync plugin must appear"
        assert legacy_ts in result[unique_plugin_id]
    finally:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM plugin_settings WHERE plugin_id = %s AND key = '_last_sync'",
                (unique_plugin_id,),
            )
            conn.commit()


def test_jobs_reader_prefers_newer_of_two_sources(db_conn, unique_plugin_id, cleanup_job_runs):
    """When both job_runs and _last_sync have rows for the same plugin,
    the newer timestamp wins."""
    from apps.api.src.routes.jobs import _plugin_last_sync_map

    older_ts = "2026-01-01T00:00:00+00:00"
    newer_ts = "2026-05-01T00:00:00+00:00"

    with db_conn() as conn:
        cur = conn.cursor()
        # Older in job_runs
        cur.execute(
            """
            INSERT INTO job_runs (job_id, started_at, completed_at, status, source)
            VALUES (%s, %s, %s, 'success', 'test')
            """,
            (f"sync:{unique_plugin_id}", older_ts, older_ts),
        )
        # Newer in legacy
        cur.execute(
            """
            INSERT INTO plugin_settings (plugin_id, key, value)
            VALUES (%s, '_last_sync', %s::jsonb)
            """,
            (unique_plugin_id, json.dumps({"timestamp": newer_ts})),
        )
        conn.commit()

    try:
        result = _plugin_last_sync_map()
        assert unique_plugin_id in result
        assert newer_ts in result[unique_plugin_id], (
            f"Expected newer legacy ts to win, got {result[unique_plugin_id]}"
        )
    finally:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM plugin_settings WHERE plugin_id = %s AND key = '_last_sync'",
                (unique_plugin_id,),
            )
            conn.commit()


# ── Dead-path regression guard ───────────────────────────────────────────


def test_no_code_writes_sync_log():
    """Regression guard for F2 audit finding — SDK must not write to
    the non-existent sync_log table."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "sync_log", str(REPO_ROOT / "apps"), str(REPO_ROOT / "sdk"),
         "--include=*.py"],
        capture_output=True, text=True,
    )
    # Filter out __pycache__ matches
    hits = [line for line in result.stdout.splitlines() if "__pycache__" not in line]
    assert not hits, f"Found sync_log references: {hits}"


def test_legacy_last_sync_is_fallback_only():
    """Regression guard: we kept a backwards-compat read from
    plugin_settings._last_sync for plugins that haven't migrated to
    BaseSyncScript. But the primary read MUST be job_runs — the fallback
    is belt-and-braces, not the main path.

    The test ensures no reader is a `_last_sync`-only path.
    """
    import subprocess
    readers = [
        REPO_ROOT / "apps" / "api" / "src" / "routes" / "jobs.py",
        REPO_ROOT / "apps" / "api" / "src" / "routes" / "plugins.py",
        REPO_ROOT / "apps" / "api" / "src" / "routes" / "launchpad.py",
    ]
    for reader in readers:
        content = reader.read_text()
        has_legacy = "_last_sync" in content
        has_new = "job_runs" in content and "sync:" in content
        if has_legacy:
            assert has_new, (
                f"{reader.name} reads _last_sync but has no job_runs path — "
                f"must prefer job_runs with _last_sync as fallback"
            )


# ── B282: SDK adopts worker-claimed run id, no double-insert ────────────


class _DummySync:
    """Minimal stand-in for a BaseSyncScript subclass — just enough
    surface to exercise _start_run() in isolation."""

    def __init__(self, plugin_id: str):
        from sdk.nousviz_sdk.sync import BaseSyncScript
        self._impl = BaseSyncScript.__new__(BaseSyncScript)
        self._impl.plugin_id = plugin_id
        import logging
        self._impl.logger = logging.getLogger(f"test.b282.{plugin_id}")
        self._impl._run_id = None
        self._impl._rows_synced = 0
        self._impl._rows_failed = 0
        self._impl._details = {}

    def start(self, source: str = "cron") -> None:
        self._impl._start_run(source=source)

    @property
    def run_id(self):
        return self._impl._run_id


def _count_rows(db_conn, plugin_id: str) -> int:
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM job_runs WHERE job_id = %s",
            (f"sync:{plugin_id}",),
        )
        return int(cur.fetchone()[0])


def test_b282_start_run_adopts_worker_claimed_id(
    db_conn, unique_plugin_id, cleanup_job_runs, monkeypatch, caplog
):
    """When NOUSVIZ_JOB_RUN_ID is set, _start_run must adopt it and skip
    the INSERT entirely (the worker has already created the row)."""
    # Pre-create the worker-claimed row so adoption has a real id to land on.
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO job_runs (job_id, started_at, status, source, claimed_by, claimed_at, details)
            VALUES (%s, now(), 'running', 'cron', 'TestWorker:1',
                    now(), '{"scheduler_id": "test"}'::jsonb)
            RETURNING id
            """,
            (f"sync:{unique_plugin_id}",),
        )
        worker_run_id = int(cur.fetchone()[0])
        conn.commit()

    monkeypatch.setenv("NOUSVIZ_JOB_RUN_ID", str(worker_run_id))

    import logging as _logging
    with caplog.at_level(_logging.INFO, logger=f"test.b282.{unique_plugin_id}"):
        sync = _DummySync(unique_plugin_id)
        sync.start(source="cron")

    assert sync.run_id == worker_run_id, "Adopted run_id must equal env var value"
    assert _count_rows(db_conn, unique_plugin_id) == 1, (
        "B282: standalone insert must NOT happen when NOUSVIZ_JOB_RUN_ID is set"
    )
    assert any(
        "Adopted worker-claimed run" in record.message for record in caplog.records
    ), "Adoption log line missing"


def test_b282_start_run_standalone_path_still_inserts(
    db_conn, unique_plugin_id, cleanup_job_runs, monkeypatch
):
    """No env var → SDK still creates a fresh row (dev / direct-invocation
    contract is preserved)."""
    monkeypatch.delenv("NOUSVIZ_JOB_RUN_ID", raising=False)

    sync = _DummySync(unique_plugin_id)
    sync.start(source="manual")

    assert sync.run_id is not None
    assert _count_rows(db_conn, unique_plugin_id) == 1

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, source, claimed_by FROM job_runs WHERE id = %s",
            (sync.run_id,),
        )
        status, source, claimed_by = cur.fetchone()
    assert status == "running"
    assert source == "manual"
    assert claimed_by is None  # standalone insert leaves claim fields NULL


def test_b282_start_run_malformed_env_falls_back_to_insert(
    db_conn, unique_plugin_id, cleanup_job_runs, monkeypatch, caplog
):
    """Malformed NOUSVIZ_JOB_RUN_ID must warn + fall through to standalone
    insert (fail-open: a sync should never be blocked by a broken env var)."""
    monkeypatch.setenv("NOUSVIZ_JOB_RUN_ID", "not-an-int")

    import logging as _logging
    with caplog.at_level(_logging.WARNING, logger=f"test.b282.{unique_plugin_id}"):
        sync = _DummySync(unique_plugin_id)
        sync.start(source="cron")

    assert sync.run_id is not None, "Fallback insert must populate run_id"
    assert _count_rows(db_conn, unique_plugin_id) == 1
    assert any(
        "is not an integer" in record.message for record in caplog.records
    ), "Warning about malformed env var missing"


def test_b282_worker_already_passes_env_var():
    """Static guard: the worker site that spawns sync subprocesses must
    set NOUSVIZ_JOB_RUN_ID. If this regresses, the SDK adoption path
    silently turns into the standalone path and duplicates return."""
    worker_src = (REPO_ROOT / "apps" / "worker" / "src" / "run_jobs.py").read_text()
    assert 'NOUSVIZ_JOB_RUN_ID' in worker_src, (
        "B282 contract: apps/worker/src/run_jobs.py must set NOUSVIZ_JOB_RUN_ID "
        "in the spawned subprocess env (see line ~579)"
    )
