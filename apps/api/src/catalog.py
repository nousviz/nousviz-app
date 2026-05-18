"""
Data catalog — host introspects `information_schema` to discover what
tables exist (B170-rev2 / v0.9.5.3).

The architectural commitment: plugin manifests are no longer the source
of truth for "what tables does this plugin own." The Postgres grants set
up at install time are the truth — a table belongs to plugin X if
plugin X declared it (in `databases.postgres.tables`) AND the table
exists AND the `nousviz_plugin` role has SELECT on it. The manifest
becomes an enrichment layer (display_name, description, semantic_type,
grain) on top of what's discovered.

This solves three concrete problems v0.9.5.2 left in place:
  1. The "row browsing not enabled for this plugin" message that
     appeared whenever a plugin didn't ship a `dataport.yaml`.
  2. Manifest claims drifting from reality (typo'd table names,
     orphaned tables created by migrations but not declared).
  3. Downstream features (fusions, dashboards, widgets) needing a
     fact-based answer to "what data exists" instead of a manifest
     claim.

Performance: production has ~15 tables across 4 plugins. Pure
`information_schema` queries take sub-millisecond. No caching layer
in v0.9.5.3 (queued as B181 if production scale ever justifies it).

Security: this module ONLY queries `information_schema` and
`pg_class.reltuples` — never operator-supplied SQL. Row fetching
uses `psycopg2.sql.Identifier` to safely quote table names. The API
runs as the `nousviz` role which has full read access; defense-in-
depth for a separate `nousviz_catalog` role is queued as B177.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Optional

from psycopg2 import sql as pg_sql

from .db import get_pg_conn

logger = logging.getLogger("nousviz.catalog")


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass
class CatalogColumn:
    """One column of a discovered table."""
    name: str
    data_type: str          # information_schema.columns.data_type
    is_nullable: bool
    ordinal_position: int


@dataclass
class CatalogTable:
    """One discovered table belonging to a plugin."""
    name: str
    plugin_id: str          # which plugin claimed this table in its manifest
    table_type: str         # 'BASE TABLE' | 'VIEW' | 'MATERIALIZED VIEW'
    columns: list[CatalogColumn]
    row_count_estimate: Optional[int]   # from pg_class.reltuples

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "plugin_id": self.plugin_id,
            "table_type": self.table_type,
            "row_count_estimate": self.row_count_estimate,
            "columns": [
                {
                    "name": c.name,
                    "data_type": c.data_type,
                    "is_nullable": c.is_nullable,
                    "ordinal_position": c.ordinal_position,
                }
                for c in self.columns
            ],
        }


# ── Plugin → table mapping (built from manifest declarations) ────────
#
# We don't have a pure "this table belongs to plugin X" signal in the
# DB — Postgres grants tell us "nousviz_plugin can read this table"
# but not "plugin X owns this table." The manifest's
# `databases.postgres.tables[]` is what we use to attribute discovered
# tables to plugins. A table not in any manifest is either operator-
# created (host-owned) or orphaned (plugin migration that wasn't
# declared); we surface those as `manifest_drift` separately.


# ── Ownership map cache (Keystone A — Phase 12 perf fix) ─────────────
#
# `_build_plugin_ownership_map()` is called from 5 sites in this module
# and (indirectly) ~34 times per `/api/plugins` request via `_enrich_datasets`'s
# double-walk through `list_tables_for_plugin` + `detect_manifest_drift`. At
# N=17 plugins on prod that meant ~578 yaml.safe_load calls per request and
# a 6.5–7s response. The function output is deterministic in the on-disk
# manifest files — so we cache it and invalidate when any plugin.yaml or
# its parent dir's mtime changes. Plugin install/uninstall/update all
# touch one of those mtimes for free.
#
# Module-level cache is safe for the gunicorn worker model (each worker
# has its own process). The lock guards against concurrent rebuilds from
# the daemon threads `plugin_update_checker.schedule_async_check` spawns.

_ownership_cache: Optional[dict[str, str]] = None
_ownership_cache_mtimes: dict[str, float] = {}
_ownership_cache_lock = threading.Lock()

# Cumulative counters (since process start). Surfaced by
# `get_ownership_cache_stats()` for observability + tests; not reset on
# cache invalidation so they reflect process-lifetime behaviour.
_ownership_cache_builds = 0
_ownership_cache_hits = 0


def _gather_manifest_mtimes() -> dict[str, float]:
    """Stat every active-plugin-dir entry and return ``{path: mtime}``.

    Includes parent directory mtimes so a new plugin install or uninstall
    (which adds/removes a child dir) invalidates the cache automatically.
    Stat failures are silently skipped — the resulting dict mismatch will
    just force a rebuild, which is the safe fallback.
    """
    # Late import to avoid circular: plugins.py imports from catalog later.
    from .routes import plugins as plugins_module

    mtimes: dict[str, float] = {}
    for base in plugins_module.ACTIVE_PLUGIN_DIRS:
        try:
            if not base.exists():
                continue
            mtimes[str(base)] = base.stat().st_mtime
            for d in base.iterdir():
                if not d.is_dir():
                    continue
                manifest = d / "plugin.yaml"
                try:
                    mtimes[str(manifest)] = manifest.stat().st_mtime
                except OSError:
                    # plugin.yaml absent or unreadable — treat dir as
                    # not-a-plugin; skip silently. _installed_slugs()
                    # applies the same filter so this matches behaviour.
                    pass
        except OSError as exc:
            logger.warning(f"catalog: could not stat {base!r} — {exc}")
    return mtimes


def invalidate_plugin_ownership_cache() -> None:
    """Drop the cached ownership map. Used by tests and by install /
    uninstall handlers that want explicit (rather than mtime-based)
    invalidation.

    Safe to call from any thread; cheap enough to call freely.
    """
    global _ownership_cache, _ownership_cache_mtimes
    with _ownership_cache_lock:
        _ownership_cache = None
        _ownership_cache_mtimes = {}


def get_ownership_cache_stats() -> dict[str, int]:
    """Return ``{"builds": N, "hits": M}`` since process start.

    Used by the observability path (logged periodically) and by tests
    that assert the cache reduced rebuild count.
    """
    return {"builds": _ownership_cache_builds, "hits": _ownership_cache_hits}


def _build_plugin_ownership_map() -> dict[str, str]:
    """Return {table_name: plugin_id} for every table claimed by a
    manifest. Reads installed plugin manifests from disk.

    Result is cached at module scope and invalidated when any active
    plugin.yaml (or its parent dir) changes mtime. Five sites in this
    module call this function; without caching that meant ~34 walks per
    `/api/plugins` request at N=17 plugins. With caching it's one walk
    per change to the on-disk plugin set.

    Multiple plugins claiming the same table (shouldn't happen — install
    validation catches it — but defensively) are resolved last-write-wins
    with a warning logged.
    """
    global _ownership_cache, _ownership_cache_mtimes
    global _ownership_cache_builds, _ownership_cache_hits

    current_mtimes = _gather_manifest_mtimes()

    with _ownership_cache_lock:
        if _ownership_cache is not None and current_mtimes == _ownership_cache_mtimes:
            _ownership_cache_hits += 1
            return _ownership_cache

        # Cache miss — rebuild. Log the reason for traceability.
        if _ownership_cache is None:
            reason = "cold"
        else:
            added = set(current_mtimes) - set(_ownership_cache_mtimes)
            removed = set(_ownership_cache_mtimes) - set(current_mtimes)
            changed = {
                k for k in current_mtimes
                if k in _ownership_cache_mtimes
                and current_mtimes[k] != _ownership_cache_mtimes[k]
            }
            reason = (
                f"added={sorted(added)} removed={sorted(removed)} "
                f"changed={sorted(changed)}"
            )
        logger.info(f"catalog: ownership cache rebuild ({reason})")

        # Late import to avoid circular: plugins.py imports from catalog later.
        from .routes import plugins as plugins_module

        ownership: dict[str, str] = {}
        try:
            installed_dirs = plugins_module._installed_slugs()
        except Exception as exc:
            logger.warning(f"catalog: could not list installed plugins — {exc}")
            # Don't cache an empty result from a transient failure — next
            # call will retry.
            return ownership

        for slug in installed_dirs:
            try:
                data = plugins_module._load_plugin(slug, installed_only=True)
                if not data:
                    continue
                # Merge module manifests so module-declared tables count.
                data = plugins_module._merge_module_manifests(slug, data)
                tables = (
                    (data.get("databases") or {}).get("postgres", {}).get("tables") or []
                )
                for tbl in tables:
                    if not isinstance(tbl, str):
                        continue
                    if tbl in ownership and ownership[tbl] != slug:
                        logger.warning(
                            f"catalog: table {tbl!r} claimed by both "
                            f"{ownership[tbl]!r} and {slug!r}; using {slug!r}"
                        )
                    ownership[tbl] = slug
            except Exception as exc:
                logger.warning(f"catalog: could not read manifest for {slug} — {exc}")

        _ownership_cache = ownership
        _ownership_cache_mtimes = current_mtimes
        _ownership_cache_builds += 1
        return ownership


# ── Discovery ────────────────────────────────────────────────────────


def list_tables_for_plugin(plugin_id: str) -> list[CatalogTable]:
    """Return all tables this plugin owns, discovered from
    `information_schema` and attributed via manifest declarations.

    A table is included if:
      - The plugin's manifest declares it in `databases.postgres.tables`
      - The table exists in `information_schema.tables` (schema 'public')
      - The `nousviz_plugin` role has SELECT on it

    Returns empty list if plugin not installed or owns no tables.
    """
    ownership = _build_plugin_ownership_map()
    plugin_tables = [t for t, owner in ownership.items() if owner == plugin_id]
    if not plugin_tables:
        return []

    return _build_tables(plugin_tables, plugin_id_override=plugin_id)


def tables_and_drift_for_plugins(
    plugin_ids: list[str],
) -> dict[str, tuple[list[CatalogTable], list[str]]]:
    """Batched version of (list_tables_for_plugin, detect_manifest_drift) for
    every plugin in ``plugin_ids``. Returns a dict mapping plugin_id to a
    tuple of (tables, drift) — same shape the per-plugin helpers return.

    Single batched information_schema query for ALL plugins' tables, in
    contrast to the per-plugin path which fires 2N queries (one tables
    scan + one columns scan per plugin). Keystone B — Phase 12 perf fix.

    Plugins with no declared tables are present in the result with
    ``([], [])`` so the caller doesn't need to guard for missing keys.
    """
    result: dict[str, tuple[list[CatalogTable], list[str]]] = {
        pid: ([], []) for pid in plugin_ids
    }
    if not plugin_ids:
        return result

    ownership = _build_plugin_ownership_map()
    requested = set(plugin_ids)

    # Reverse the ownership map: plugin_id -> [declared tables]
    declared_by_plugin: dict[str, list[str]] = {pid: [] for pid in requested}
    candidate_tables: list[str] = []
    for tbl, owner in ownership.items():
        if owner in requested:
            declared_by_plugin[owner].append(tbl)
            candidate_tables.append(tbl)

    if not candidate_tables:
        return result

    # ONE batched _build_tables call for every candidate table.
    discovered = _build_tables(candidate_tables)
    discovered_by_name = {t.name: t for t in discovered}

    for pid in requested:
        declared = declared_by_plugin[pid]
        if not declared:
            continue
        tables: list[CatalogTable] = []
        drift: list[str] = []
        for tbl_name in declared:
            t = discovered_by_name.get(tbl_name)
            if t is None:
                drift.append(tbl_name)
            elif t.plugin_id == pid:
                tables.append(t)
            # If t.plugin_id != pid the ownership map disagrees with the
            # _build_tables resolution — shouldn't happen since both read
            # from the same map; defensively skip.
        # Stable orderings: tables by name, drift sorted.
        tables.sort(key=lambda x: x.name)
        drift.sort()
        result[pid] = (tables, drift)

    return result


def list_all_tables_grouped_by_plugin() -> dict[str, list[CatalogTable]]:
    """Return {plugin_id: [tables...]} for every plugin with at least
    one discovered table. Used by the Datasets page to render a flat
    list grouped by plugin.
    """
    ownership = _build_plugin_ownership_map()
    grouped: dict[str, list[CatalogTable]] = {}

    if ownership:
        all_tables = list(ownership.keys())
        discovered = _build_tables(all_tables)
        for tbl in discovered:
            grouped.setdefault(tbl.plugin_id, []).append(tbl)

    return grouped


def get_table(plugin_id: str, table_name: str) -> Optional[CatalogTable]:
    """Return one specific table or None if not found / not owned by
    this plugin / not granted to nousviz_plugin."""
    ownership = _build_plugin_ownership_map()
    if ownership.get(table_name) != plugin_id:
        return None

    tables = _build_tables([table_name], plugin_id_override=plugin_id)
    return tables[0] if tables else None


def detect_manifest_drift(plugin_id: str) -> list[str]:
    """Return tables the plugin's manifest declares that don't exist
    in the catalog (e.g. typo, never created, dropped by a down-
    migration). Empty list when manifest matches reality.

    Doesn't include "tables in DB but not in manifest" — that's a
    separate concept (orphan detection, B181).
    """
    ownership = _build_plugin_ownership_map()
    declared = [t for t, owner in ownership.items() if owner == plugin_id]
    if not declared:
        return []

    discovered = _build_tables(declared, plugin_id_override=plugin_id)
    discovered_names = {t.name for t in discovered}
    return sorted(t for t in declared if t not in discovered_names)


# ── Row fetching ─────────────────────────────────────────────────────


# Conservative table-name validator. Even though we cross-check against
# the manifest ownership map (which only contains valid identifiers
# because install-time validation rejects bad ones), defense in depth.
_VALID_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# B262 (v0.9.11.5): server-side filter operators on the rows endpoint.
# Mapping is intentionally narrow — adding a new op requires adding to
# both _FILTER_OPS (allowlist) and _OP_TO_SQL (renderer).
_FILTER_OPS = frozenset({
    "eq", "neq", "gt", "lt", "gte", "lte",
    "contains", "startswith",
    "is_null", "not_null",
})
_OP_TO_SQL = {
    "eq": "=", "neq": "<>", "gt": ">", "lt": "<", "gte": ">=", "lte": "<=",
    # contains / startswith use ILIKE with wrapped param (built in _build_where)
    # is_null / not_null are rendered separately (no param)
}

# Postgres types that the `?q=` substring search casts to text. Anything
# else is excluded from the OR-chain (binary types, geometric types, etc.)
# to avoid casting failures and noisy matches.
_TEXT_COERCIBLE_TYPES = frozenset({
    "text", "character varying", "varchar", "character", "char",
    "json", "jsonb", "uuid",
})

_MAX_FILTERS = 8
_MAX_Q_LENGTH = 100


def _build_where(
    columns: list[CatalogColumn],
    q: Optional[str],
    filters: Optional[list[tuple[str, str, Optional[str]]]],
) -> tuple[Optional[pg_sql.Composed], list]:
    """Compose a SQL WHERE fragment (without the leading WHERE) and the
    matching positional params. Returns (None, []) when no filters apply.

    Validation:
      - Each filter's column must exist in `columns`. ValueError if not.
      - Each filter's op must be in _FILTER_OPS. ValueError if not.
      - Caps (q length, filter count) are enforced as a defense-in-depth
        assertion — the route handler enforces them first; if anything
        slips through, we raise here too rather than silently truncate.

    All values are passed as %s parameters (psycopg2 escapes them);
    column names go through pg_sql.Identifier (psycopg2 quotes them);
    operators are pulled from a frozen mapping. No user input is
    interpolated into SQL.
    """
    if q is None and not filters:
        return (None, [])

    if q is not None and len(q) > _MAX_Q_LENGTH:
        raise ValueError(f"q too long (max {_MAX_Q_LENGTH} chars)")
    if filters and len(filters) > _MAX_FILTERS:
        raise ValueError(f"too many filters (max {_MAX_FILTERS})")

    valid_cols = {c.name: c for c in columns}
    fragments: list[pg_sql.Composable] = []
    params: list = []

    # 1. q: OR across text-coercible columns, ILIKE wrapped value.
    if q:
        text_cols = [
            c.name for c in columns if c.data_type in _TEXT_COERCIBLE_TYPES
        ]
        if text_cols:
            wrapped = f"%{q}%"
            or_parts = pg_sql.SQL(" OR ").join(
                pg_sql.SQL("{}::text ILIKE %s").format(pg_sql.Identifier(c))
                for c in text_cols
            )
            fragments.append(pg_sql.SQL("(") + or_parts + pg_sql.SQL(")"))
            params.extend([wrapped] * len(text_cols))
        # If no text-coercible columns, q silently matches nothing — emit
        # a fragment that's always false so total + rows reflect that.
        else:
            fragments.append(pg_sql.SQL("FALSE"))

    # 2. filters: AND-composed predicates.
    for col, op, value in (filters or []):
        if op not in _FILTER_OPS:
            raise ValueError(f"unknown operator {op!r}")
        if col not in valid_cols:
            raise ValueError(f"unknown column {col!r}")

        ident = pg_sql.Identifier(col)

        if op == "is_null":
            fragments.append(pg_sql.SQL("{} IS NULL").format(ident))
        elif op == "not_null":
            fragments.append(pg_sql.SQL("{} IS NOT NULL").format(ident))
        elif op == "contains":
            fragments.append(
                pg_sql.SQL("{}::text ILIKE %s").format(ident)
            )
            params.append(f"%{value if value is not None else ''}%")
        elif op == "startswith":
            fragments.append(
                pg_sql.SQL("{}::text ILIKE %s").format(ident)
            )
            params.append(f"{value if value is not None else ''}%")
        else:
            # eq / neq / gt / lt / gte / lte — direct binary op
            sql_op = _OP_TO_SQL[op]
            fragments.append(
                pg_sql.SQL("{} " + sql_op + " %s").format(ident)
            )
            params.append(value)

    if not fragments:
        return (None, [])

    composed = pg_sql.SQL(" AND ").join(fragments)
    return (composed, params)


def fetch_rows(
    plugin_id: str,
    table_name: str,
    page: int = 1,
    limit: int = 50,
    sort: Optional[str] = None,
    q: Optional[str] = None,
    filters: Optional[list[tuple[str, str, Optional[str]]]] = None,
) -> dict:
    """Fetch rows from a discovered plugin table.

    Returns {"rows": [...], "total": int, "page": int, "limit": int}.
    Raises ValueError if the plugin doesn't own this table, the table
    doesn't exist, or the q/filters are malformed (B262, v0.9.11.5).

    `sort` accepts "column" or "column asc" / "column desc". Column
    name is validated against the discovered schema; invalid sort is
    silently dropped (default ordering used).

    `q` is a substring search across text-coercible columns (ILIKE).
    Capped at 100 chars. Caller-side caps are the primary enforcement;
    this is defense in depth.

    `filters` is a list of (column, op, value) tuples ANDed together.
    Operators: eq, neq, gt, lt, gte, lte, contains, startswith,
    is_null, not_null. Capped at 8 filters per call.

    The response's `total` reflects the WHERE-applied count, not the
    table total — so pagination paginates the filtered result set.
    """
    table = get_table(plugin_id, table_name)
    if not table:
        raise ValueError(
            f"Table {table_name!r} not owned by plugin {plugin_id!r}, "
            f"not installed, or not granted to nousviz_plugin."
        )

    if not _VALID_IDENT.match(table_name):
        # Already filtered by ownership map, but explicit guard.
        raise ValueError(f"Invalid table name {table_name!r}")

    page = max(1, page)
    limit = max(1, min(500, limit))   # cap at 500 rows per page
    offset = (page - 1) * limit

    sort_col, sort_dir = _parse_sort(sort, table.columns)

    where_fragment, where_params = _build_where(table.columns, q, filters)

    # Plugin tables live in the public schema (the historical default).
    table_ref = pg_sql.Identifier("public", table_name)

    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Total count — exact COUNT(*) over the WHERE-filtered set so
        # pagination reflects the filtered total. Same caveat as before:
        # for very large tables this is slow; B181 may switch to
        # pg_class.reltuples for unfiltered queries.
        if where_fragment is not None:
            count_query = pg_sql.SQL("SELECT COUNT(*) FROM {} WHERE ").format(
                table_ref
            ) + where_fragment
            cur.execute(count_query, where_params)
        else:
            cur.execute(
                pg_sql.SQL("SELECT COUNT(*) FROM {}").format(table_ref)
            )
        total = cur.fetchone()[0]

        # Build the SELECT. If sort is None, default to no ORDER BY
        # (server-defined order, fine for browsing).
        select_pieces = [
            pg_sql.SQL("SELECT * FROM {}").format(table_ref)
        ]
        select_params: list = []

        if where_fragment is not None:
            select_pieces.append(pg_sql.SQL(" WHERE ") + where_fragment)
            select_params.extend(where_params)

        if sort_col:
            select_pieces.append(
                pg_sql.SQL(" ORDER BY {} {}").format(
                    pg_sql.Identifier(sort_col),
                    pg_sql.SQL(sort_dir),  # ASC/DESC, validated by _parse_sort
                )
            )

        select_pieces.append(pg_sql.SQL(" LIMIT %s OFFSET %s"))
        select_params.extend([limit, offset])

        query = pg_sql.Composed(select_pieces)
        cur.execute(query, select_params)

        col_names = [d[0] for d in cur.description]
        rows = [dict(zip(col_names, row)) for row in cur.fetchall()]

    return {
        "rows": rows,
        "total": total,
        "page": page,
        "limit": limit,
    }


def _parse_sort(
    sort: Optional[str], columns: list[CatalogColumn]
) -> tuple[Optional[str], str]:
    """Parse a sort string like 'created_at desc' against the column
    list. Returns (column_name, 'ASC'|'DESC') or (None, 'ASC') if invalid.
    Invalid sort silently drops to no-sort (server order)."""
    if not sort:
        return (None, "ASC")

    parts = sort.strip().split()
    if not parts:
        return (None, "ASC")

    col = parts[0]
    direction = "DESC" if len(parts) > 1 and parts[1].lower().startswith("desc") else "ASC"

    valid_cols = {c.name for c in columns}
    if col not in valid_cols:
        return (None, "ASC")

    return (col, direction)


# ── Internal: bulk-build CatalogTable instances ──────────────────────


def _build_tables(
    table_names: list[str], plugin_id_override: Optional[str] = None
) -> list[CatalogTable]:
    """Given a list of candidate table names, query information_schema
    + pg_class to materialize CatalogTable instances. Skips tables that
    don't exist or aren't accessible.

    If plugin_id_override is given, every result gets that plugin_id
    (used by list_tables_for_plugin). Otherwise the ownership map is
    consulted again.
    """
    if not table_names:
        return []

    # Filter to valid identifiers — defense in depth
    valid_names = [t for t in table_names if _VALID_IDENT.match(t)]
    if not valid_names:
        return []

    ownership = (
        {t: plugin_id_override for t in valid_names}
        if plugin_id_override
        else _build_plugin_ownership_map()
    )

    tables_by_name: dict[str, CatalogTable] = {}

    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Existing tables in 'public' schema, with their type and row estimate.
        cur.execute(
            """
            SELECT t.table_name, t.table_type, c.reltuples::BIGINT AS row_est
            FROM information_schema.tables t
            LEFT JOIN pg_class c
              ON c.relname = t.table_name AND c.relkind IN ('r', 'v', 'm', 'p')
            WHERE t.table_schema = 'public'
              AND t.table_name = ANY(%s)
            """,
            (valid_names,),
        )
        for row in cur.fetchall():
            name, table_type, row_est = row[0], row[1], row[2]
            owner = ownership.get(name)
            if not owner:
                # Table exists but no manifest claims it — skip.
                # (B181 will surface these as orphans.)
                continue
            # pg_class.reltuples is -1 when ANALYZE has never run on the
            # table (or never run since last truncate). Fresh installs
            # commonly hit this. Surface as None instead of -1 so the
            # frontend can render "—" rather than the literal "-1".
            estimate = int(row_est) if row_est is not None else None
            if estimate is not None and estimate < 0:
                estimate = None
            tables_by_name[name] = CatalogTable(
                name=name,
                plugin_id=owner,
                table_type=table_type,
                columns=[],
                row_count_estimate=estimate,
            )

        if not tables_by_name:
            return []

        # Fetch columns for the surviving tables.
        cur.execute(
            """
            SELECT table_name, column_name, data_type, is_nullable, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            ORDER BY table_name, ordinal_position
            """,
            (list(tables_by_name.keys()),),
        )
        for row in cur.fetchall():
            tname, cname, dtype, nullable, ord_pos = row
            if tname not in tables_by_name:
                continue
            tables_by_name[tname].columns.append(
                CatalogColumn(
                    name=cname,
                    data_type=dtype,
                    is_nullable=nullable == "YES",
                    ordinal_position=ord_pos,
                )
            )

    # Stable order: alphabetical by table name
    return sorted(tables_by_name.values(), key=lambda t: t.name)
