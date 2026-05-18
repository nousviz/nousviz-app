"""
Unit tests for the catalog module (B170-rev2 / v0.9.5.3).

Most catalog logic queries `information_schema` directly, so true
integration tests need a live Postgres with installed plugins. Those
are covered by post-deploy production smoke. The unit tests here
focus on:
  - The pure logic (sort parsing, identifier validation, ownership
    deduplication).
  - The shape of the data classes (CatalogColumn, CatalogTable).
  - Manifest drift detection given a mocked ownership map.

Tests that need a live DB are gated by NOUSVIZ_RUN_DB_TESTS=1 and
skipped otherwise — same pattern as tests/test_observability.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.catalog import (
    CatalogColumn,
    CatalogTable,
    _parse_sort,
    _VALID_IDENT,
    detect_manifest_drift,
)


# ── _parse_sort ──────────────────────────────────────────────────────


@pytest.fixture
def sample_columns():
    return [
        CatalogColumn("id", "bigint", False, 1),
        CatalogColumn("created_at", "timestamp with time zone", False, 2),
        CatalogColumn("name", "text", True, 3),
    ]


def test_parse_sort_none_returns_no_sort(sample_columns):
    assert _parse_sort(None, sample_columns) == (None, "ASC")


def test_parse_sort_empty_returns_no_sort(sample_columns):
    assert _parse_sort("", sample_columns) == (None, "ASC")


def test_parse_sort_valid_column_default_asc(sample_columns):
    assert _parse_sort("created_at", sample_columns) == ("created_at", "ASC")


def test_parse_sort_explicit_desc(sample_columns):
    assert _parse_sort("created_at desc", sample_columns) == ("created_at", "DESC")


def test_parse_sort_invalid_column_falls_to_no_sort(sample_columns):
    # Defense: don't let operator-supplied "DROP TABLE" arrive at the
    # query as a column name. Whitelist enforcement.
    assert _parse_sort("dropped_column desc", sample_columns) == (None, "ASC")


def test_parse_sort_sql_injection_attempt_safe(sample_columns):
    # Anything that doesn't match an exact column name is rejected.
    # The "; DROP TABLE x;" payload would never make it past the
    # whitelist check because no column has that name.
    assert _parse_sort("id; DROP TABLE users; --", sample_columns) == (None, "ASC")


# ── _VALID_IDENT ─────────────────────────────────────────────────────


def test_valid_ident_accepts_normal():
    assert _VALID_IDENT.match("foo_bar")
    assert _VALID_IDENT.match("Foo123")
    assert _VALID_IDENT.match("_underscore")


def test_valid_ident_rejects_special():
    assert not _VALID_IDENT.match("foo bar")
    assert not _VALID_IDENT.match("foo;bar")
    assert not _VALID_IDENT.match("123foo")  # can't start with digit
    assert not _VALID_IDENT.match("foo-bar")
    assert not _VALID_IDENT.match("")


# ── CatalogTable.to_dict ──────────────────────────────────────────────


def test_catalog_table_to_dict_shape():
    t = CatalogTable(
        name="programs",
        plugin_id="example-plugin",
        table_type="BASE TABLE",
        columns=[
            CatalogColumn("id", "bigint", False, 1),
            CatalogColumn("name", "text", True, 2),
        ],
        row_count_estimate=4148,
    )
    d = t.to_dict()
    assert d["name"] == "programs"
    assert d["plugin_id"] == "example-plugin"
    assert d["table_type"] == "BASE TABLE"
    assert d["row_count_estimate"] == 4148
    assert len(d["columns"]) == 2
    assert d["columns"][0] == {
        "name": "id",
        "data_type": "bigint",
        "is_nullable": False,
        "ordinal_position": 1,
    }


def test_catalog_table_to_dict_handles_null_row_estimate():
    t = CatalogTable(
        name="empty",
        plugin_id="x",
        table_type="VIEW",
        columns=[],
        row_count_estimate=None,
    )
    d = t.to_dict()
    assert d["row_count_estimate"] is None
    assert d["columns"] == []


# ── detect_manifest_drift ────────────────────────────────────────────


def test_detect_drift_returns_typo_table(monkeypatch):
    # Plugin manifest claims `foo` and `bar`, but only `bar` exists in DB.
    # Drift returns ['foo'].
    from apps.api.src import catalog

    def fake_ownership():
        return {"foo": "myplugin", "bar": "myplugin"}

    def fake_build_tables(table_names, plugin_id_override=None):
        # Simulate DB only has 'bar', not 'foo'
        if "bar" not in table_names:
            return []
        return [
            CatalogTable(
                name="bar",
                plugin_id="myplugin",
                table_type="BASE TABLE",
                columns=[],
                row_count_estimate=0,
            )
        ]

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "_build_tables", fake_build_tables)

    drift = detect_manifest_drift("myplugin")
    assert drift == ["foo"]


def test_detect_drift_empty_when_aligned(monkeypatch):
    from apps.api.src import catalog

    def fake_ownership():
        return {"foo": "myplugin", "bar": "myplugin"}

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
        ]

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "_build_tables", fake_build_tables)

    drift = detect_manifest_drift("myplugin")
    assert drift == []


def test_detect_drift_plugin_not_installed(monkeypatch):
    # Unknown plugin slug → empty drift list (not an error).
    from apps.api.src import catalog

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {})

    drift = detect_manifest_drift("unknown-plugin")
    assert drift == []


# ── fetch_rows guard rails (unit-level, not exercising the DB) ───────


def test_fetch_rows_unknown_plugin_raises(monkeypatch):
    from apps.api.src import catalog

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {})

    with pytest.raises(ValueError, match="not owned by plugin"):
        catalog.fetch_rows("unknown", "any_table")


def test_fetch_rows_table_not_owned_raises(monkeypatch):
    # Plugin owns `foo` but the call asks for `bar`.
    from apps.api.src import catalog

    def fake_ownership():
        return {"foo": "myplugin"}

    def fake_get_table(plugin_id, table_name):
        return None  # simulating "not in catalog"

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", fake_ownership)
    monkeypatch.setattr(catalog, "get_table", fake_get_table)

    with pytest.raises(ValueError):
        catalog.fetch_rows("myplugin", "bar")
