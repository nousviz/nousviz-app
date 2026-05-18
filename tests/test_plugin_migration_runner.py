"""
Unit + integration tests for B285 (v0.9.11.25.1) — migration runner stale
schema_migrations rows after B278 regression.

Production incident 2026-05-08: plugin developer reported install + Update
returning 200 on `nousviz.online` while the plugin's migrations never ran;
sync failed with `psycopg2.errors.UndefinedTable`. Root cause: B278's
`_drop_declared_tables` (v0.9.11.14) drops manifest tables but did not clear
the corresponding `schema_migrations` rows. The next install/Update saw the
stale rows and skipped re-running the SQL. Affected any plugin shipping
up-only migrations once it had been uninstalled-with-data.

These tests pin the contract for the two-half fix:

  Half 1 — `_drop_declared_tables` calls `_purge_schema_migrations_rows`
           (symmetry with `_run_down_migrations`'s tracking-row cleanup).

  Half 2 — `_run_plugin_migrations` runs `_migration_skip_is_safe` before
           honoring a tracking-row "already applied" claim. If declared
           tables are missing, the stale row is deleted and the migration
           re-runs. Defense-in-depth against any path that drops tables
           out-of-band.

Live-DB tests are gated behind NOUSVIZ_RUN_DB_TESTS=1, matching the
B278 test suite convention.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.routes.plugins import (
    _drop_declared_tables,
    _migration_skip_is_safe,
    _purge_schema_migrations_rows,
    _run_plugin_migrations,
)


# ── _migration_skip_is_safe: pure logic ──────────────────────────────


def test_skip_safe_when_no_declared_tables():
    """Utility plugin or manifest with no declared tables → no integrity
    check possible, trust schema_migrations as before B285."""
    cur = MagicMock()
    assert _migration_skip_is_safe(cur, "plugin_x", []) is True
    cur.execute.assert_not_called()


def test_skip_safe_when_all_declared_tables_exist():
    cur = MagicMock()
    cur.fetchone.return_value = (3,)
    assert _migration_skip_is_safe(cur, "plugin_x", ["a", "b", "c"]) is True


def test_skip_unsafe_when_any_declared_table_missing():
    cur = MagicMock()
    cur.fetchone.return_value = (2,)  # 2 of 3 declared tables present
    assert _migration_skip_is_safe(cur, "plugin_x", ["a", "b", "c"]) is False


def test_skip_unsafe_when_no_declared_tables_present():
    cur = MagicMock()
    cur.fetchone.return_value = (0,)
    assert _migration_skip_is_safe(cur, "plugin_x", ["a", "b"]) is False


def test_skip_safe_when_pg_class_query_raises():
    """Defensive default: on uncertainty, preserve current behavior rather
    than risk re-running unsafe migrations. Warning is logged."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("simulated transaction error")
    assert _migration_skip_is_safe(cur, "plugin_x", ["a"]) is True


def test_skip_check_uses_pg_class_with_correct_filter():
    """Guard against future edits: the integrity check must filter by
    relkind so it only counts tables (and partitioned tables), not views
    or foreign tables that happen to share a name."""
    cur = MagicMock()
    cur.fetchone.return_value = (1,)
    _migration_skip_is_safe(cur, "plugin_x", ["t"])
    sql, params = cur.execute.call_args[0]
    assert "pg_class" in sql
    assert "relkind" in sql
    assert "'r'" in sql and "'p'" in sql  # ordinary + partitioned tables
    assert params == (["t"],)


# ── _purge_schema_migrations_rows: tracking-row sweep ────────────────


def test_purge_executes_like_query_with_plugin_id_prefix():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.rowcount = 3
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        deleted = _purge_schema_migrations_rows("example-analytics")

    assert deleted == 3
    sql, params = mock_cur.execute.call_args[0]
    assert "DELETE FROM schema_migrations" in sql
    assert "filename LIKE" in sql
    assert params == ("example-analytics/%",)


def test_purge_zero_rows_returns_zero_no_error():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.rowcount = 0
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        deleted = _purge_schema_migrations_rows("never-installed")
    assert deleted == 0


def test_purge_db_failure_logs_warning_does_not_raise():
    """Caller (_drop_declared_tables) tolerates partial cleanup; the sweep
    must not propagate a DB failure."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = Exception("simulated transaction broken")
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        deleted = _purge_schema_migrations_rows("plugin_x")
    assert deleted == 0  # no raise


# ── _drop_declared_tables ↔ _purge_schema_migrations_rows symmetry ───


def test_drop_declared_tables_purges_tracking_rows():
    """B285 symmetry contract: after _drop_declared_tables runs, the
    tracking rows for that plugin are gone — same end-state as the
    *_down.sql path."""
    manifest = {"databases": {"postgres": {"tables": ["t1", "t2"]}}}
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        _drop_declared_tables("plugin_x", manifest)

    executed_sql = " ".join(
        str(call.args[0]) for call in mock_cur.execute.call_args_list
    )
    # The DROP TABLE calls go through psycopg2.sql composition, not raw text,
    # so we inspect for the DELETE that came from the purge helper.
    assert any(
        "DELETE FROM schema_migrations" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    ), f"Expected DELETE FROM schema_migrations in calls; got: {executed_sql}"


def test_drop_declared_tables_purges_even_when_no_declared_tables():
    """Utility plugin path: manifest declares no tables but the plugin may
    still have shipped migrations (e.g. seeded reference data into a shared
    table). The purge should run regardless."""
    manifest = {"databases": {"postgres": {"tables": []}}}
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        _drop_declared_tables("utility_plugin", manifest)

    assert any(
        "DELETE FROM schema_migrations" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    )


# ── _run_plugin_migrations integrity-check end-to-end (mocked) ───────


def _write_fixture_plugin(tmp_path: Path, plugin_id: str, declared_tables: list[str]):
    """Build a fake installed-plugin tree with one up migration."""
    pdir = tmp_path / plugin_id
    (pdir / "storage" / "migrations").mkdir(parents=True)
    (pdir / "storage" / "migrations" / "001_init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS placeholder_for_test (id int);\n"
    )
    manifest = "name: " + plugin_id + "\nversion: 0.1.0\n"
    if declared_tables:
        manifest += "databases:\n  postgres:\n    tables:\n"
        for t in declared_tables:
            manifest += f"      - {t}\n"
    (pdir / "plugin.yaml").write_text(manifest)
    return pdir


def test_run_migrations_skips_when_tracking_row_exists_and_tables_present(tmp_path):
    """Normal idempotent re-run: row exists in schema_migrations, tables
    exist in pg_class → migration is skipped, no SQL execution."""
    pdir = _write_fixture_plugin(tmp_path, "plugin_a", ["table_a"])

    mock_conn = MagicMock()
    mock_cur = MagicMock()

    # Sequence: CREATE TABLE schema_migrations, SELECT 1 FROM ... (row exists),
    # then pg_class lookup returns full count.
    fetchone_returns = iter([
        (1,),    # SELECT 1 FROM schema_migrations → row exists
        (1,),    # pg_class lookup → 1 of 1 declared tables present
    ])
    mock_cur.fetchone.side_effect = lambda: next(fetchone_returns)
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("plugin_a", pdir)

    assert applied == []  # nothing applied — skip honored


def test_run_migrations_reruns_when_tracking_row_exists_but_table_missing(tmp_path):
    """B285 core fix: row exists in schema_migrations, but pg_class shows
    the declared table is missing. Stale row is deleted, migration re-runs,
    new row inserted."""
    pdir = _write_fixture_plugin(tmp_path, "plugin_b", ["table_b"])

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    fetchone_returns = iter([
        (1,),    # SELECT 1 FROM schema_migrations → row exists
        (0,),    # pg_class lookup → 0 of 1 declared tables present (stale)
    ])
    mock_cur.fetchone.side_effect = lambda: next(fetchone_returns)
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("plugin_b", pdir)

    # Migration re-ran
    assert applied == ["001_init.sql"]
    # Stale row deletion happened
    assert any(
        "DELETE FROM schema_migrations WHERE filename" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    )
    # New row inserted
    assert any(
        "INSERT INTO schema_migrations" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    )


def test_run_migrations_no_integrity_check_when_manifest_declares_no_tables(tmp_path):
    """Utility plugin: manifest has no declared tables → integrity check
    no-ops, behavior unchanged from pre-B285. Skip is honored on tracking
    row alone."""
    pdir = _write_fixture_plugin(tmp_path, "utility_plugin", [])

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # Only one fetchone call expected: the schema_migrations SELECT.
    mock_cur.fetchone.return_value = (1,)
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("utility_plugin", pdir)

    assert applied == []
    # Nothing should have queried pg_class
    assert not any(
        "pg_class" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    )


def test_run_migrations_runs_first_install_normally(tmp_path):
    """No tracking row exists → migration runs. Integrity check is gated
    behind row presence so this path doesn't even consult pg_class."""
    pdir = _write_fixture_plugin(tmp_path, "plugin_c", ["table_c"])

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # SELECT 1 FROM schema_migrations → no row
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("plugin_c", pdir)

    assert applied == ["001_init.sql"]
    # Skip-path didn't trigger → no pg_class lookup
    assert not any(
        "pg_class" in str(call.args[0])
        for call in mock_cur.execute.call_args_list
    )


# ── B299: forward-migration glob narrows to [0-9]*.sql ────────────────


def _write_b299_fixture(tmp_path: Path, files: dict) -> Path:
    """Build a migrations dir with arbitrary file names + contents for the
    B299 glob tests. No declared tables — the glob fix is independent of
    the B285 integrity check, so we test the runner's file-selection
    behavior directly without entangling the manifest path."""
    pdir = tmp_path / "b299_plugin"
    (pdir / "storage" / "migrations").mkdir(parents=True)
    for name, contents in files.items():
        (pdir / "storage" / "migrations" / name).write_text(contents)
    (pdir / "plugin.yaml").write_text("name: b299_plugin\nversion: 0.1.0\n")
    return pdir


def test_b299_glob_includes_only_digit_prefixed_up_files(tmp_path):
    """Forward-migration selection must match [0-9]*.sql; bare names are
    ignored. The full directory listing exercises every shape that's bitten
    a plugin author."""
    pdir = _write_b299_fixture(tmp_path, {
        "001_init.sql":      "CREATE TABLE IF NOT EXISTS t1 (id int);\n",
        "001_init_down.sql": "DROP TABLE IF EXISTS t1;\n",
        "002_more.sql":      "CREATE TABLE IF NOT EXISTS t2 (id int);\n",
        "002_more_down.sql": "DROP TABLE IF EXISTS t2;\n",
        "down.sql":          "DROP TABLE IF EXISTS t1; DROP TABLE IF EXISTS t2;\n",
        "init.sql":          "CREATE TABLE IF NOT EXISTS leaked (id int);\n",
        "helper.sql":        "-- nothing to see here\n",
    })

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None  # no schema_migrations rows
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("b299_plugin", pdir)

    assert applied == ["001_init.sql", "002_more.sql"]


def test_b299_glob_logs_warning_for_ignored_files(tmp_path, caplog):
    """Each ignored *.sql in the migrations dir produces a warning so the
    operator (and plugin author) can spot the deviation in API logs."""
    pdir = _write_b299_fixture(tmp_path, {
        "001_init.sql": "CREATE TABLE IF NOT EXISTS t (id int);\n",
        "down.sql":     "DROP TABLE IF EXISTS t;\n",
        "init.sql":     "-- bare name\n",
    })

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with caplog.at_level("WARNING"), patch(
        "apps.api.src.db.get_pg_conn", return_value=mock_conn
    ):
        _run_plugin_migrations("b299_plugin", pdir)

    msgs = [r.getMessage() for r in caplog.records]
    assert any("ignoring migration file 'down.sql'" in m for m in msgs)
    assert any("ignoring migration file 'init.sql'" in m for m in msgs)
    # 001_init.sql must NOT trigger a warning
    assert not any("ignoring migration file '001_init.sql'" in m for m in msgs)


def test_b299_glob_does_not_warn_on_paired_down_files(tmp_path, caplog):
    """`<NNN>_<name>_down.sql` is a recognized rollback companion — must
    not be warned about even though it's filtered from up_files."""
    pdir = _write_b299_fixture(tmp_path, {
        "001_init.sql":      "CREATE TABLE IF NOT EXISTS t (id int);\n",
        "001_init_down.sql": "DROP TABLE IF EXISTS t;\n",
    })

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with caplog.at_level("WARNING"), patch(
        "apps.api.src.db.get_pg_conn", return_value=mock_conn
    ):
        _run_plugin_migrations("b299_plugin", pdir)

    msgs = [r.getMessage() for r in caplog.records]
    assert not any("ignoring migration file" in m for m in msgs)


def test_b299_empty_dir_no_crash(tmp_path):
    """No *.sql files at all — early return, no warnings, no crash."""
    pdir = tmp_path / "b299_plugin"
    (pdir / "storage" / "migrations").mkdir(parents=True)
    (pdir / "plugin.yaml").write_text("name: b299_plugin\nversion: 0.1.0\n")

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = MagicMock()
    mock_conn.__enter__ = lambda self: mock_conn
    mock_conn.__exit__ = lambda *a: False

    with patch("apps.api.src.db.get_pg_conn", return_value=mock_conn):
        applied = _run_plugin_migrations("b299_plugin", pdir)

    assert applied == []


# ── Live integration: real Postgres ───────────────────────────────────

LIVE = pytest.mark.skipif(
    os.environ.get("NOUSVIZ_RUN_DB_TESTS") != "1",
    reason="Set NOUSVIZ_RUN_DB_TESTS=1 to run live-DB tests against the local Postgres",
)


@LIVE
def test_live_drop_declared_tables_clears_tracking_rows(tmp_path):
    """End-to-end: insert a stale schema_migrations row, run
    _drop_declared_tables, verify the row is gone alongside any matching
    tables. This is the exact regression that surfaced on production."""
    from apps.api.src.db import get_pg_conn

    plugin_id = "b285_test_plugin"
    table_name = "b285_test_table"
    filename_key = f"{plugin_id}/001_init.sql"

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id int)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) "
            "ON CONFLICT (filename) DO NOTHING",
            (filename_key,),
        )
        conn.commit()

    manifest = {"databases": {"postgres": {"tables": [table_name]}}}
    dropped, failed = _drop_declared_tables(plugin_id, manifest)
    assert dropped == [table_name]
    assert failed == []

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = %s",
            (filename_key,),
        )
        assert cur.fetchone()[0] == 0, "B285 symmetry: tracking row must be gone"
        cur.execute(
            "SELECT count(*) FROM pg_class WHERE relname = %s",
            (table_name,),
        )
        assert cur.fetchone()[0] == 0, "Table must be gone (B278 contract)"


@LIVE
def test_live_run_migrations_recovers_from_stale_tracking_row(tmp_path):
    """End-to-end: simulate the production scenario — table dropped
    out-of-band, stale tracking row still present, then call
    _run_plugin_migrations. The integrity check should detect the missing
    table, delete the stale row, and re-run the migration so the table
    exists again."""
    from apps.api.src.db import get_pg_conn

    plugin_id = "b285_recovery_plugin"
    table_name = "b285_recovery_table"
    filename_key = f"{plugin_id}/001_init.sql"

    pdir = tmp_path / plugin_id
    (pdir / "storage" / "migrations").mkdir(parents=True)
    (pdir / "storage" / "migrations" / "001_init.sql").write_text(
        f"CREATE TABLE IF NOT EXISTS {table_name} (id int);\n"
    )
    (pdir / "plugin.yaml").write_text(
        "name: b285_recovery_plugin\n"
        "version: 0.1.0\n"
        "databases:\n  postgres:\n    tables:\n"
        f"      - {table_name}\n"
    )

    with get_pg_conn() as conn:
        cur = conn.cursor()
        # Set up the broken state: table missing, tracking row present
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) "
            "ON CONFLICT (filename) DO NOTHING",
            (filename_key,),
        )
        conn.commit()

    try:
        applied = _run_plugin_migrations(plugin_id, pdir)
        assert applied == ["001_init.sql"]

        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) FROM pg_class WHERE relname = %s",
                (table_name,),
            )
            assert cur.fetchone()[0] == 1, "Recovery must recreate the table"
            cur.execute(
                "SELECT count(*) FROM schema_migrations WHERE filename = %s",
                (filename_key,),
            )
            assert cur.fetchone()[0] == 1, "Tracking row must be restored"
    finally:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            cur.execute(
                "DELETE FROM schema_migrations WHERE filename = %s",
                (filename_key,),
            )
            conn.commit()
