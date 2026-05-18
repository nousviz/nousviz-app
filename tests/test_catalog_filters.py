"""
Unit tests for the catalog filter + search additions (B262 / v0.9.11.5).

These test the pure logic — _build_where (catalog.py) and
_parse_filter_param (routes/catalog.py). True integration coverage
(filter end-to-end against Postgres) sits behind NOUSVIZ_RUN_DB_TESTS=1
in the same pattern as tests/test_catalog.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.catalog import (
    CatalogColumn,
    _build_where,
    _FILTER_OPS,
    _MAX_FILTERS,
    _MAX_Q_LENGTH,
    _TEXT_COERCIBLE_TYPES,
)
from apps.api.src.routes.catalog import _parse_filter_param


# ── Test fixtures ────────────────────────────────────────────────────


@pytest.fixture
def sample_columns():
    return [
        CatalogColumn("id", "bigint", False, 1),
        CatalogColumn("name", "text", True, 2),
        CatalogColumn("status", "character varying", True, 3),
        CatalogColumn("created_at", "timestamp with time zone", False, 4),
        CatalogColumn("metadata", "jsonb", True, 5),
        CatalogColumn("count", "integer", True, 6),
    ]


def _render(composed) -> str:
    """Render a psycopg2 Composed/SQL fragment to a string for assertion.
    Uses as_string with no connection (psycopg2's Composed supports this
    via the str() fallback for SQL/Identifier nodes built from constants).
    """
    # psycopg2.sql.Composed needs a connection or a cursor for as_string,
    # but Identifier and SQL fragments built from string literals stringify
    # cleanly. Fall back to repr if needed.
    try:
        from psycopg2 import connect, sql as pg_sql  # noqa
        # No cursor available — use a simple string materialization that
        # walks the composable tree. Good enough for assertions on shape.
        if hasattr(composed, "_strings"):
            # Composed
            return "".join(_render(p) for p in composed._strings)
        if hasattr(composed, "_string"):
            return composed._string
        if hasattr(composed, "_seq"):
            return "".join(_render(p) for p in composed._seq)
    except Exception:
        pass
    return str(composed)


# ── _build_where: empty cases ────────────────────────────────────────


def test_build_where_no_filters_no_q_returns_none(sample_columns):
    composed, params = _build_where(sample_columns, q=None, filters=None)
    assert composed is None
    assert params == []


def test_build_where_empty_filters_list_returns_none(sample_columns):
    composed, params = _build_where(sample_columns, q=None, filters=[])
    assert composed is None
    assert params == []


# ── _build_where: q substring search ─────────────────────────────────


def test_build_where_q_only_text_columns_oring(sample_columns):
    composed, params = _build_where(sample_columns, q="foo", filters=None)
    assert composed is not None
    # name (text), status (character varying), metadata (jsonb) are text-coercible
    # id (bigint), created_at (timestamp), count (integer) are not
    assert len(params) == 3, f"expected 3 text-coercible cols, got params={params}"
    assert all(p == "%foo%" for p in params)


def test_build_where_q_no_text_cols_returns_false_fragment():
    """If a table has no text-coercible columns at all, q should match
    nothing rather than blowing up or matching everything."""
    cols = [
        CatalogColumn("id", "bigint", False, 1),
        CatalogColumn("count", "integer", True, 2),
    ]
    composed, params = _build_where(cols, q="foo", filters=None)
    assert composed is not None
    assert params == []
    # Should compile to FALSE — total + rows reflect zero matches
    rendered = str(composed)
    assert "FALSE" in rendered.upper() or "false" in rendered


def test_build_where_q_too_long_raises():
    cols = [CatalogColumn("name", "text", True, 1)]
    long_q = "x" * (_MAX_Q_LENGTH + 1)
    with pytest.raises(ValueError, match="too long"):
        _build_where(cols, q=long_q, filters=None)


# ── _build_where: filter operators ───────────────────────────────────


def test_build_where_filter_eq(sample_columns):
    composed, params = _build_where(sample_columns, None, [("status", "eq", "active")])
    assert composed is not None
    assert params == ["active"]


def test_build_where_filter_neq(sample_columns):
    composed, params = _build_where(sample_columns, None, [("status", "neq", "deleted")])
    assert composed is not None
    assert params == ["deleted"]


def test_build_where_filter_comparison_ops(sample_columns):
    for op in ("gt", "lt", "gte", "lte"):
        composed, params = _build_where(sample_columns, None, [("count", op, "10")])
        assert composed is not None
        assert params == ["10"], f"op={op} expected param=['10'], got {params}"


def test_build_where_filter_contains_wraps_value(sample_columns):
    _, params = _build_where(sample_columns, None, [("name", "contains", "foo")])
    assert params == ["%foo%"]


def test_build_where_filter_startswith_appends_value(sample_columns):
    _, params = _build_where(sample_columns, None, [("name", "startswith", "foo")])
    assert params == ["foo%"]


def test_build_where_filter_is_null_no_param(sample_columns):
    composed, params = _build_where(sample_columns, None, [("name", "is_null", None)])
    assert composed is not None
    assert params == []


def test_build_where_filter_not_null_no_param(sample_columns):
    composed, params = _build_where(sample_columns, None, [("name", "not_null", None)])
    assert composed is not None
    assert params == []


def test_build_where_filter_unknown_op_raises(sample_columns):
    with pytest.raises(ValueError, match="unknown operator"):
        _build_where(sample_columns, None, [("name", "BOGUS", "x")])


def test_build_where_filter_unknown_column_raises(sample_columns):
    with pytest.raises(ValueError, match="unknown column"):
        _build_where(sample_columns, None, [("nonexistent", "eq", "x")])


# ── _build_where: composition ────────────────────────────────────────


def test_build_where_multiple_filters_and_composed(sample_columns):
    filters = [
        ("status", "eq", "active"),
        ("count", "gte", "5"),
        ("name", "contains", "foo"),
    ]
    composed, params = _build_where(sample_columns, None, filters)
    assert composed is not None
    # Order preserved; contains wraps with %s
    assert params == ["active", "5", "%foo%"]


def test_build_where_q_and_filter_q_params_first(sample_columns):
    composed, params = _build_where(
        sample_columns,
        q="hello",
        filters=[("status", "eq", "active")],
    )
    assert composed is not None
    # text-coercible cols: name, status, metadata = 3
    # q params (3 ILIKE) come before filter params (1)
    assert len(params) == 4
    assert params[:3] == ["%hello%", "%hello%", "%hello%"]
    assert params[3] == "active"


def test_build_where_too_many_filters_raises(sample_columns):
    too_many = [("status", "eq", "x")] * (_MAX_FILTERS + 1)
    with pytest.raises(ValueError, match="too many filters"):
        _build_where(sample_columns, None, too_many)


# ── _build_where: SQL injection defense ──────────────────────────────


def test_build_where_injection_via_column_name_raises(sample_columns):
    """A user-supplied column name like '"; DROP TABLE users; --' must
    fail validation, never reach SQL composition."""
    evil = '"; DROP TABLE users; --'
    with pytest.raises(ValueError, match="unknown column"):
        _build_where(sample_columns, None, [(evil, "eq", "x")])


def test_build_where_injection_via_value_safe(sample_columns):
    """A user-supplied value like "' OR 1=1 --" must be passed as a
    parameter, not interpolated. _build_where doesn't execute, but we
    can verify the value is in params unmodified (psycopg2 escapes at
    cursor.execute time)."""
    evil = "' OR 1=1 --"
    _, params = _build_where(sample_columns, None, [("name", "eq", evil)])
    assert params == [evil]
    # The SQL fragment uses %s not interpolation — visually inspect the
    # string form does not contain the evil value
    composed, _ = _build_where(sample_columns, None, [("name", "eq", evil)])
    assert evil not in str(composed)


# ── _parse_filter_param: the route-side parser ───────────────────────


def test_parse_filter_basic_three_part():
    assert _parse_filter_param("status:eq:active") == ("status", "eq", "active")


def test_parse_filter_value_with_colons_preserved():
    """Timestamps and URLs in values contain colons — maxsplit=2 keeps them."""
    assert _parse_filter_param("created_at:gte:2026-05-03T12:34:56Z") == (
        "created_at", "gte", "2026-05-03T12:34:56Z"
    )


def test_parse_filter_value_with_url_preserved():
    assert _parse_filter_param("redirect:eq:https://example.com/path") == (
        "redirect", "eq", "https://example.com/path"
    )


def test_parse_filter_is_null_no_value():
    assert _parse_filter_param("name:is_null") == ("name", "is_null", None)


def test_parse_filter_not_null_trailing_colon_optional():
    assert _parse_filter_param("name:not_null") == ("name", "not_null", None)
    assert _parse_filter_param("name:not_null:") == ("name", "not_null", None)


def test_parse_filter_empty_string_raises():
    with pytest.raises(ValueError, match="invalid filter format"):
        _parse_filter_param("")


def test_parse_filter_no_colon_raises():
    with pytest.raises(ValueError, match="invalid filter format"):
        _parse_filter_param("just_a_word")


def test_parse_filter_missing_value_raises():
    with pytest.raises(ValueError, match="invalid filter format"):
        _parse_filter_param("col:eq")


def test_parse_filter_empty_column_raises():
    with pytest.raises(ValueError, match="column is empty"):
        _parse_filter_param(":eq:value")


def test_parse_filter_empty_op_raises():
    with pytest.raises(ValueError, match="operator is empty"):
        _parse_filter_param("col::value")


# ── Sanity: constants align ──────────────────────────────────────────


def test_filter_ops_match_op_to_sql():
    """All non-special operators must be in _OP_TO_SQL. The is_null /
    not_null / contains / startswith ops are rendered separately."""
    from apps.api.src.catalog import _OP_TO_SQL
    binary_ops = _FILTER_OPS - {"is_null", "not_null", "contains", "startswith"}
    for op in binary_ops:
        assert op in _OP_TO_SQL, f"{op} in _FILTER_OPS but missing from _OP_TO_SQL"


def test_text_coercible_types_includes_common_text_types():
    for t in ("text", "character varying", "varchar", "json", "jsonb"):
        assert t in _TEXT_COERCIBLE_TYPES
