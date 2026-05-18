"""
Unit tests for the v0.10.0.6.2 /api/alerts/sources changes:
  - Plugin ownership comes from the catalog cache (no manifest walks)
  - One batched information_schema.columns query instead of N+1
  - Response shape unchanged (consumer compat)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _make_mock_conn(table_rows, column_rows, connection_rows=None):
    """Build a get_pg_conn() context manager whose cursor returns the
    given table-listing rows, then column rows, then connection rows."""
    if connection_rows is None:
        connection_rows = []

    fetchall_queue = [list(table_rows), list(column_rows), list(connection_rows)]
    call_idx = {"i": 0}

    cur = MagicMock()

    def execute_side_effect(*_a, **_k):
        call_idx["i"] += 1

    def fetchall_side_effect():
        idx = call_idx["i"] - 1
        return fetchall_queue[idx] if 0 <= idx < len(fetchall_queue) else []

    cur.execute.side_effect = execute_side_effect
    cur.fetchall.side_effect = fetchall_side_effect

    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def test_alert_sources_response_shape_preserved(monkeypatch):
    """Response keys + nested shapes match what the frontend Create Alert
    modal expects. This is the consumer-contract guarantee."""
    from apps.api.src import catalog
    from apps.api.src.routes import alerts as alerts_module

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {
        "users": "auth-plugin",
        "events": "auth-plugin",
    })

    from apps.api.src.routes import plugins as plugins_module
    monkeypatch.setattr(plugins_module, "_load_plugin",
                        lambda pid, installed_only=True: {
                            "display_name": "Auth Plugin",
                            "datasets": [
                                {"name": "users", "label": "Users",
                                 "fields": [{"name": "id", "type": "uuid"}]}
                            ],
                        } if pid == "auth-plugin" else None)

    table_rows = [("users", 42), ("some_other_table", 100)]
    column_rows = [
        ("users", "id", "uuid"),
        ("users", "email", "text"),
        ("some_other_table", "id", "bigint"),
    ]
    conn = _make_mock_conn(table_rows, column_rows, connection_rows=[])
    monkeypatch.setattr(alerts_module, "get_pg_conn", lambda: conn)

    result = asyncio.run(alerts_module.alert_sources())

    assert "postgres" in result
    assert "connections" in result
    assert "plugins" in result

    pg = {t["table"]: t for t in result["postgres"]}
    assert pg["users"]["plugin_id"] == "auth-plugin"
    assert pg["users"]["source_label"] == "Auth Plugin"
    assert pg["users"]["source_type"] == "plugin_postgres"
    assert len(pg["users"]["columns"]) == 2
    assert pg["users"]["row_estimate"] == 42

    assert pg["some_other_table"]["plugin_id"] is None
    assert pg["some_other_table"]["source_type"] == "postgres"
    assert pg["some_other_table"]["source_label"] == "PostgreSQL"


def test_alert_sources_columns_query_fires_once_not_per_table(monkeypatch):
    """The headline guarantee: ONE batched columns query regardless of
    table count. Previously this was N+1 (one query per table)."""
    from apps.api.src import catalog
    from apps.api.src.routes import alerts as alerts_module

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {})
    from apps.api.src.routes import plugins as plugins_module
    monkeypatch.setattr(plugins_module, "_load_plugin",
                        lambda pid, installed_only=True: None)

    # Five tables → previously 5+1 = 6 queries; now 1 + 1 = 2.
    table_rows = [(f"t{i}", i * 10) for i in range(5)]
    column_rows = [(f"t{i}", "id", "bigint") for i in range(5)]
    conn = _make_mock_conn(table_rows, column_rows, connection_rows=[])
    monkeypatch.setattr(alerts_module, "get_pg_conn", lambda: conn)

    asyncio.run(alerts_module.alert_sources())

    cur = conn.cursor.return_value
    # Tables query + batched columns query + connections query = 3.
    # Previously would have been 1 + 5 (per-table columns) + 1 = 7.
    assert cur.execute.call_count <= 4, (
        f"Expected at most 4 execute() calls, got {cur.execute.call_count}"
    )
    sql_strs = [str(c.args[0]) if c.args else "" for c in cur.execute.call_args_list]
    has_batched = any("ANY(%s)" in s for s in sql_strs)
    assert has_batched, "Expected batched ANY(%s) columns query"


def test_alert_sources_empty_install_returns_empty_lists(monkeypatch):
    """Fresh install with no plugins, no tables → empty response, no crash."""
    from apps.api.src import catalog
    from apps.api.src.routes import alerts as alerts_module

    monkeypatch.setattr(catalog, "_build_plugin_ownership_map", lambda: {})
    from apps.api.src.routes import plugins as plugins_module
    monkeypatch.setattr(plugins_module, "_load_plugin",
                        lambda pid, installed_only=True: None)

    conn = _make_mock_conn(table_rows=[], column_rows=[], connection_rows=[])
    monkeypatch.setattr(alerts_module, "get_pg_conn", lambda: conn)

    result = asyncio.run(alerts_module.alert_sources())

    assert result["postgres"] == []
    assert result["connections"] == []
    assert result["plugins"] == []
