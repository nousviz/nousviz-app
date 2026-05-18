"""
Unit tests for the batched `_enrich_datasets` path (Keystone B — Phase 12 perf).

Before the batching, each plugin in the `/api/plugins` response cost:
  - 2 catalog calls (`list_tables_for_plugin` + `detect_manifest_drift`),
    each firing 2 information_schema queries = 4 DB queries
  - 2 own DB queries (`job_runs` + `plugin_settings._last_sync`)
That's ~6 DB round trips per plugin. At N=17 plugins → ~102 round trips.

After Keystone B, `list_plugins` pre-fetches:
  - one batched `catalog.tables_and_drift_for_plugins(plugin_ids)` (1 batched
    information_schema scan + 1 batched columns scan)
  - one batched `_fetch_last_sync_batch(plugin_ids)` (2 batched queries)
Total: 4 round trips regardless of N.

These tests verify:
  - `tables_and_drift_for_plugins` returns the same shape as the per-plugin
    helpers (`list_tables_for_plugin` + `detect_manifest_drift`), so callers
    can swap with no behavioural change.
  - `_fetch_last_sync_batch` returns one entry per plugin that has a sync
    record, and prefers `job_runs` over the legacy `plugin_settings` row
    when newer (matching the per-plugin path).
  - `_enrich_datasets` produces an identical output dict whether called
    with the pre-fetched dicts or in the fallback per-plugin mode.

The catalog calls hit `information_schema` which needs a live Postgres, so
the catalog-batching test mocks `_build_tables` (same pattern as
test_catalog.py) and the last-sync test mocks `get_pg_conn`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src import catalog
from apps.api.src.catalog import CatalogColumn, CatalogTable


# ── tables_and_drift_for_plugins ─────────────────────────────────────


def test_tables_and_drift_returns_empty_for_empty_input():
    """Defensive: empty input → empty result, no DB queries fired."""
    assert catalog.tables_and_drift_for_plugins([]) == {}


def test_tables_and_drift_groups_results_by_plugin(monkeypatch):
    """Three plugins share one batched _build_tables call; results split correctly."""

    def fake_ownership():
        return {
            "alpha_users": "alpha",
            "alpha_events": "alpha",
            "beta_things": "beta",
            "gamma_orphan": "gamma",  # in manifest but not in DB → drift
        }

    def fake_build_tables(table_names, plugin_id_override=None):
        # ONE call expected with ALL candidate tables.
        # Returns alpha_users, alpha_events, beta_things; gamma_orphan absent
        # to exercise the drift branch.
        present = {"alpha_users", "alpha_events", "beta_things"}
        return [
            CatalogTable(
                name=t,
                plugin_id={
                    "alpha_users": "alpha",
                    "alpha_events": "alpha",
                    "beta_things": "beta",
                }[t],
                table_type="BASE TABLE",
                columns=[CatalogColumn("id", "bigint", False, 1)],
                row_count_estimate=10,
            )
            for t in table_names
            if t in present
        ]

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "_build_tables", fake_build_tables)

    result = catalog.tables_and_drift_for_plugins(["alpha", "beta", "gamma"])

    # Alpha: 2 tables, no drift
    alpha_tables, alpha_drift = result["alpha"]
    assert sorted(t.name for t in alpha_tables) == ["alpha_events", "alpha_users"]
    assert alpha_drift == []

    # Beta: 1 table, no drift
    beta_tables, beta_drift = result["beta"]
    assert [t.name for t in beta_tables] == ["beta_things"]
    assert beta_drift == []

    # Gamma: declared `gamma_orphan` but it doesn't exist → drift
    gamma_tables, gamma_drift = result["gamma"]
    assert gamma_tables == []
    assert gamma_drift == ["gamma_orphan"]


def test_tables_and_drift_fires_one_build_tables_call(monkeypatch):
    """The headline batching guarantee: ONE _build_tables call regardless of N."""

    def fake_ownership():
        return {
            f"tbl_{i}": f"plugin_{i // 3}"  # 3 tables per plugin
            for i in range(15)  # 15 tables across 5 plugins
        }

    call_count = {"n": 0}

    def counting_build_tables(table_names, plugin_id_override=None):
        call_count["n"] += 1
        return [
            CatalogTable(
                name=t,
                plugin_id=f"plugin_{int(t.split('_')[1]) // 3}",
                table_type="BASE TABLE",
                columns=[],
                row_count_estimate=0,
            )
            for t in table_names
        ]

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "_build_tables", counting_build_tables)

    plugin_ids = [f"plugin_{i}" for i in range(5)]
    result = catalog.tables_and_drift_for_plugins(plugin_ids)

    assert call_count["n"] == 1, "expected exactly one _build_tables call"
    assert len(result) == 5
    # Each plugin owns 3 tables
    for pid in plugin_ids:
        tables, drift = result[pid]
        assert len(tables) == 3
        assert drift == []


def test_tables_and_drift_unknown_plugin_returns_empty(monkeypatch):
    """A plugin_id not present in the ownership map → ([], []) entry."""
    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {})
    monkeypatch.setattr(catalog, "_build_tables", lambda *_a, **_k: [])

    result = catalog.tables_and_drift_for_plugins(["nonexistent"])
    assert result == {"nonexistent": ([], [])}


def test_tables_and_drift_match_per_plugin_helpers(monkeypatch):
    """For any plugin_id, the batched result must equal the per-plugin call
    pair (list_tables_for_plugin, detect_manifest_drift). Equivalence is the
    contract that lets callers swap freely.
    """

    def fake_ownership():
        return {
            "users": "myplugin",
            "events": "myplugin",
            "orphan": "myplugin",  # declared but not in DB → drift
        }

    def fake_build_tables(table_names, plugin_id_override=None):
        return [
            CatalogTable(
                name=t,
                plugin_id="myplugin",
                table_type="BASE TABLE",
                columns=[],
                row_count_estimate=0,
            )
            for t in table_names
            if t in {"users", "events"}
        ]

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "_build_tables", fake_build_tables)

    per_plugin_tables = catalog.list_tables_for_plugin("myplugin")
    per_plugin_drift = catalog.detect_manifest_drift("myplugin")

    batched = catalog.tables_and_drift_for_plugins(["myplugin"])
    batched_tables, batched_drift = batched["myplugin"]

    assert [t.name for t in batched_tables] == sorted(t.name for t in per_plugin_tables)
    assert batched_drift == sorted(per_plugin_drift)


# ── _fetch_last_sync_batch ───────────────────────────────────────────


def _make_mock_conn(job_run_rows: list[tuple], settings_rows: list[tuple]):
    """Build a get_pg_conn context manager that yields a cursor whose
    successive `execute()` calls return the given row sets in order.
    """
    fetchall_results = [list(job_run_rows), list(settings_rows)]
    call_idx = {"i": 0}

    cur = MagicMock()
    def fetchall_side_effect():
        idx = call_idx["i"] - 1
        return fetchall_results[idx] if 0 <= idx < len(fetchall_results) else []
    def execute_side_effect(*_a, **_k):
        call_idx["i"] += 1
    cur.execute.side_effect = execute_side_effect
    cur.fetchall.side_effect = fetchall_side_effect

    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def test_fetch_last_sync_batch_empty_input():
    """Empty input → empty result, no DB call."""
    from apps.api.src.routes import plugins as plugins_module
    assert plugins_module._fetch_last_sync_batch([]) == {}


def test_fetch_last_sync_batch_prefers_job_runs(monkeypatch):
    """When a plugin has both a job_runs row and a plugin_settings row,
    the more recent of the two wins. Mirrors the per-plugin path.
    """
    from datetime import datetime, timezone
    from apps.api.src.routes import plugins as plugins_module

    newer = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
    older_str = "2026-05-12T08:00:00+00:00"

    conn = _make_mock_conn(
        job_run_rows=[("sync:alpha", newer)],
        settings_rows=[("alpha", older_str)],
    )
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)

    result = plugins_module._fetch_last_sync_batch(["alpha"])
    assert result == {"alpha": newer.isoformat()}


def test_fetch_last_sync_batch_uses_legacy_when_newer(monkeypatch):
    """When the legacy plugin_settings row is newer than job_runs, fold it in."""
    from datetime import datetime, timezone
    from apps.api.src.routes import plugins as plugins_module

    older = datetime(2026, 5, 12, 8, 0, 0, tzinfo=timezone.utc)
    newer_str = "2026-05-13T12:00:00+00:00"

    conn = _make_mock_conn(
        job_run_rows=[("sync:beta", older)],
        settings_rows=[("beta", newer_str)],
    )
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)

    result = plugins_module._fetch_last_sync_batch(["beta"])
    assert result == {"beta": newer_str}


def test_fetch_last_sync_batch_handles_dict_legacy_value(monkeypatch):
    """The legacy plugin_settings value is sometimes a dict with `timestamp`."""
    from apps.api.src.routes import plugins as plugins_module

    conn = _make_mock_conn(
        job_run_rows=[],
        settings_rows=[("gamma", {"timestamp": "2026-05-13T00:00:00+00:00"})],
    )
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)

    result = plugins_module._fetch_last_sync_batch(["gamma"])
    assert result == {"gamma": "2026-05-13T00:00:00+00:00"}


def test_fetch_last_sync_batch_plugin_with_no_sync_record_absent(monkeypatch):
    """A plugin with neither a job_runs nor plugin_settings row → absent from result."""
    from apps.api.src.routes import plugins as plugins_module

    conn = _make_mock_conn(job_run_rows=[], settings_rows=[])
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)

    result = plugins_module._fetch_last_sync_batch(["never-synced"])
    assert result == {}


# ── _enrich_datasets (batched vs fallback parity) ────────────────────


def test_enrich_datasets_batched_and_fallback_produce_same_output(monkeypatch):
    """The batched path (caller supplies pre-fetched dicts) and the fallback
    path (function does per-plugin lookups) must produce identical entries
    for any given input. This is the equivalence guarantee that lets the
    `/api/plugins` handler swap to batched mode without behavioural diff.
    """
    from apps.api.src.routes import plugins as plugins_module

    # Mock the catalog so both paths see the same data.
    fake_tables = [
        CatalogTable(
            name="users",
            plugin_id="myplugin",
            table_type="BASE TABLE",
            columns=[CatalogColumn("id", "bigint", False, 1)],
            row_count_estimate=42,
        )
    ]
    fake_drift = ["typo_table"]

    # Mock catalog for fallback path
    monkeypatch.setattr(catalog, "list_tables_for_plugin", lambda _: list(fake_tables))
    monkeypatch.setattr(catalog, "detect_manifest_drift", lambda _: list(fake_drift))

    # Mock DB for fallback path (last_sync)
    from datetime import datetime, timezone

    sync_ts = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
    cur = MagicMock()
    cur.fetchone.side_effect = [(sync_ts,), None]  # job_runs hit, settings absent
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: conn)

    base_entry = {
        "id": "myplugin",
        "datasets": [{"name": "users", "label": "Users", "description": "User accounts"}],
    }

    # Fallback path
    fallback_result = plugins_module._enrich_datasets({**base_entry, "datasets": list(base_entry["datasets"])})

    # Batched path
    batched_result = plugins_module._enrich_datasets(
        {**base_entry, "datasets": list(base_entry["datasets"])},
        tables_drift_by_plugin={"myplugin": (fake_tables, fake_drift)},
        last_sync_by_plugin={"myplugin": sync_ts.isoformat()},
    )

    assert fallback_result["datasets"] == batched_result["datasets"]
    assert fallback_result["manifest_drift"] == batched_result["manifest_drift"]


def test_enrich_datasets_batched_handles_missing_plugin_id():
    """Plugin with no batched entry → empty datasets, empty drift."""
    from apps.api.src.routes import plugins as plugins_module

    result = plugins_module._enrich_datasets(
        {"id": "unknown-plugin"},
        tables_drift_by_plugin={},  # plugin not in dict
        last_sync_by_plugin={},
    )

    assert result["datasets"] == []
    assert result["manifest_drift"] == []


def test_enrich_datasets_preserves_manifest_annotations():
    """Manifest's `datasets[].label`/`description` should overlay catalog data."""
    from apps.api.src.routes import plugins as plugins_module

    tables = [
        CatalogTable(
            name="orders",
            plugin_id="store",
            table_type="BASE TABLE",
            columns=[],
            row_count_estimate=100,
        )
    ]

    result = plugins_module._enrich_datasets(
        {
            "id": "store",
            "datasets": [
                {"name": "orders", "label": "Order History", "description": "All orders"}
            ],
        },
        tables_drift_by_plugin={"store": (tables, [])},
        last_sync_by_plugin={},
    )

    ds = result["datasets"][0]
    assert ds["label"] == "Order History"  # from manifest, not "orders"
    assert ds["description"] == "All orders"
    assert ds["rows"] == 100  # from catalog
