/**
 * Dataset detail — row-level view for a single (plugin, table).
 *
 * B170-rev2 (v0.9.5.3): catalog-driven. Reads /api/catalog endpoints
 * which discover from information_schema. Works for every plugin's
 * every granted table — no `dataport.yaml` opt-in required.
 *
 * B262 (v0.9.11.5): server-side search + per-column filter chips.
 * Replaces the previous per-page client-side filter (which silently
 * matched only visible rows on tables larger than DEFAULT_LIMIT).
 *   - Search box drives ?q= server-side with 300ms debounce.
 *   - Filter chips drive ?filter=col:op:value on the catalog endpoint.
 *   - Pagination resets to page 1 when q or filters change.
 *   - Empty state distinguishes "no rows match filters" from "table empty".
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  Database,
  Package,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Inbox,
  ArrowLeft,
  Search,
  ArrowUp,
  ArrowDown,
  ChevronsUpDown,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import {
  FilterChips,
  type Filter,
  serializeFilter,
  parseFilter,
} from "@/components/datasets/FilterChips";

// ── Types matching /api/catalog response shapes ───────────────────────

interface CatalogColumn {
  name: string;
  data_type: string;
  is_nullable: boolean;
  ordinal_position: number;
}

interface CatalogTable {
  name: string;
  plugin_id: string;
  table_type: string;
  row_count_estimate: number | null;
  columns: CatalogColumn[];
}

interface RowsResponse {
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  limit: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const DEFAULT_LIMIT = 50;
const CELL_TRUNCATE = 80; // chars before truncation hint

function isJsonLike(s: string): boolean {
  if (s.length < 2) return false;
  const f = s[0];
  const l = s[s.length - 1];
  return (f === "{" && l === "}") || (f === "[" && l === "]");
}

function formatCell(value: unknown, dataType?: string): string {
  if (value === null || value === undefined) return "—";
  if (
    dataType?.includes("timestamp") ||
    dataType === "date" ||
    (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value))
  ) {
    try {
      return new Date(value as string).toLocaleString();
    } catch {
      return String(value);
    }
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function shortenForCell(s: string): { short: string; truncated: boolean } {
  if (s.length <= CELL_TRUNCATE) return { short: s, truncated: false };
  return { short: s.slice(0, CELL_TRUNCATE) + "…", truncated: true };
}

// ── Cell renderer with click-to-expand for long strings + JSON ────────

function Cell({
  value,
  dataType,
}: {
  value: unknown;
  dataType: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const formatted = formatCell(value, dataType);
  const isLong = formatted.length > CELL_TRUNCATE;
  const looksJson = typeof value === "object" || (typeof value === "string" && isJsonLike(formatted));

  if (formatted === "—") {
    return <span className="text-muted-foreground">—</span>;
  }

  if (!isLong && !looksJson) {
    return (
      <span
        className={cn(
          dataType.includes("timestamp") ||
            dataType === "date"
            ? "font-mono-deck text-muted-foreground"
            : "",
        )}
      >
        {formatted}
      </span>
    );
  }

  // Long or JSON-like → truncated by default, click to expand
  const { short } = shortenForCell(formatted);

  if (!expanded) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(true);
        }}
        className={cn(
          "text-left max-w-md truncate hover:underline cursor-pointer",
          looksJson ? "font-mono-deck text-blue-400" : "",
        )}
        title="Click to expand"
      >
        {short}
      </button>
    );
  }

  // Expanded: pretty-print JSON if applicable
  let pretty = formatted;
  if (looksJson) {
    try {
      const parsed = typeof value === "object" ? value : JSON.parse(formatted);
      pretty = JSON.stringify(parsed, null, 2);
    } catch {
      // fall through with raw string
    }
  }

  return (
    <div className="relative max-w-2xl">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(false);
        }}
        className="absolute top-0 right-0 text-muted-foreground hover:text-foreground"
        title="Collapse"
      >
        <X className="w-3 h-3" />
      </button>
      <pre
        className={cn(
          "whitespace-pre-wrap text-xs bg-secondary/40 rounded p-2 max-h-64 overflow-auto pr-6",
          looksJson ? "font-mono-deck" : "",
        )}
      >
        {pretty}
      </pre>
    </div>
  );
}

// ── Sort header ───────────────────────────────────────────────────────

function SortHeader({
  column,
  active,
  direction,
  onClick,
  isFirst,
}: {
  column: CatalogColumn;
  active: boolean;
  direction: "asc" | "desc";
  onClick: () => void;
  isFirst: boolean;
}) {
  const Icon = active
    ? direction === "asc"
      ? ArrowUp
      : ArrowDown
    : ChevronsUpDown;
  return (
    <th
      className={cn(
        "px-3 py-1.5 text-left font-display text-muted-foreground whitespace-nowrap select-none border-b border-border bg-card sticky top-0",
        isFirst
          ? "sticky left-0 z-20 shadow-[inset_-1px_0_0_var(--border)]"
          : "z-10",
      )}
      title={`${column.data_type}${column.is_nullable ? " (nullable)" : ""}`}
    >
      <button
        onClick={onClick}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground transition-colors",
          active && "text-foreground",
        )}
      >
        {column.name}
        <Icon className="w-3 h-3 opacity-60" />
      </button>
    </th>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function DatasetDetailPage() {
  useMarkBootReadyOnMount();
  const { plugin: pluginSlug, table: tableId } = useParams<{
    plugin: string;
    table: string;
  }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10) || 1);
  const sort = searchParams.get("sort") ?? "";
  const q = searchParams.get("q") ?? "";

  // Filters live in the URL as repeated ?filter=col:op:value entries.
  // Parse on every render — cheap and keeps URL as source of truth.
  const filters: Filter[] = useMemo(() => {
    return searchParams
      .getAll("filter")
      .map(parseFilter)
      .filter((f): f is Filter => f !== null);
  }, [searchParams]);

  const filtersActive = q.length > 0 || filters.length > 0;

  // Local search-input state — debounces into the URL ?q= param so the
  // user can type without firing one request per keystroke (B262).
  const [searchInput, setSearchInput] = useState(q);
  useEffect(() => {
    setSearchInput(q);
  }, [q]);

  const [tableMeta, setTableMeta] = useState<CatalogTable | null>(null);
  const [data, setData] = useState<RowsResponse | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const updateParams = useCallback(
    (patch: Record<string, string | null>, replace = true) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            if (v === null || v === "") next.delete(k);
            else next.set(k, v);
          }
          return next;
        },
        { replace },
      );
    },
    [setSearchParams],
  );

  // Load table metadata (schema)
  useEffect(() => {
    if (!pluginSlug || !tableId) return;
    setLoadingMeta(true);
    setNotFound(false);
    apiFetch(
      `/api/catalog/plugins/${encodeURIComponent(pluginSlug)}/tables/${encodeURIComponent(tableId)}`,
    )
      .then((r) => {
        if (r.status === 404) {
          setNotFound(true);
          throw new Error("not_found");
        }
        return r.json();
      })
      .then((meta: CatalogTable) => {
        setTableMeta(meta);
        setError(null);
      })
      .catch((err) => {
        if (err.message !== "not_found") {
          setError("Failed to load table metadata.");
        }
        setTableMeta(null);
      })
      .finally(() => setLoadingMeta(false));
  }, [pluginSlug, tableId]);

  // Fetch rows. B262: includes ?q= and repeated ?filter= params.
  const fetchData = useCallback(async () => {
    if (!pluginSlug || !tableId || !tableMeta) return;
    setLoadingData(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(DEFAULT_LIMIT),
      });
      if (sort) params.set("sort", sort);
      if (q) params.set("q", q);
      filters.forEach((f) => params.append("filter", serializeFilter(f)));
      const res = await apiFetch(
        `/api/catalog/plugins/${encodeURIComponent(pluginSlug)}/tables/${encodeURIComponent(tableId)}/rows?${params}`,
      );
      if (!res.ok) {
        // Try to surface the API's detail message — useful for 400s
        // from filter validation.
        let msg = await res.text();
        try {
          const parsed = JSON.parse(msg);
          if (parsed?.detail) msg = String(parsed.detail);
        } catch {
          /* keep raw text */
        }
        throw new Error(msg);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load rows");
      setData(null);
    } finally {
      setLoadingData(false);
    }
  }, [pluginSlug, tableId, page, sort, q, filters, tableMeta]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Debounce search input → URL `q` (300ms). Resets page to 1 on change.
  const debounceTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (searchInput === q) return;
    if (debounceTimer.current !== undefined) {
      window.clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = window.setTimeout(() => {
      updateParams({ q: searchInput || null, page: null });
    }, 300);
    return () => {
      if (debounceTimer.current !== undefined) {
        window.clearTimeout(debounceTimer.current);
      }
    };
  }, [searchInput, q, updateParams]);

  // Filter change handler — also resets page to 1.
  const onFiltersChange = useCallback(
    (next: Filter[]) => {
      setSearchParams(
        (prev) => {
          const params = new URLSearchParams(prev);
          params.delete("filter");
          next.forEach((f) => params.append("filter", serializeFilter(f)));
          params.delete("page");
          return params;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const clearAllFilters = useCallback(() => {
    setSearchInput("");
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev);
        params.delete("q");
        params.delete("filter");
        params.delete("page");
        return params;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 0;

  // Parse current sort
  const [sortCol, sortDir] = useMemo<[string | null, "asc" | "desc"]>(() => {
    if (!sort) return [null, "asc"];
    const parts = sort.trim().split(/\s+/);
    return [
      parts[0] ?? null,
      parts[1]?.toLowerCase() === "desc" ? "desc" : "asc",
    ];
  }, [sort]);

  const toggleSort = useCallback(
    (colName: string) => {
      if (sortCol !== colName) {
        updateParams({ sort: `${colName} asc`, page: null });
      } else if (sortDir === "asc") {
        updateParams({ sort: `${colName} desc`, page: null });
      } else {
        updateParams({ sort: null, page: null });
      }
    },
    [sortCol, sortDir, updateParams],
  );

  // B262: rows are now server-filtered. Render data.rows directly; the
  // previous client-side per-page filter is gone (it silently lied on
  // tables larger than DEFAULT_LIMIT).
  const visibleRows = data?.rows ?? [];

  // ── Render: not found ────────────────────────────────────────────────────

  if (notFound) {
    return (
      <div className="max-w-[900px]">
        <Link
          to="/datasets"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-3 h-3" /> Back to Datasets
        </Link>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="h-16 w-16 rounded-2xl bg-secondary flex items-center justify-center mb-4">
            <Database className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="font-display text-lg text-foreground mb-2">
            Table not found
          </h3>
          <p className="text-sm text-muted-foreground font-body max-w-md mb-6">
            The table <span className="font-mono-deck">{tableId}</span> isn't
            registered to plugin{" "}
            <span className="font-mono-deck">{pluginSlug}</span>. Either the
            plugin isn't installed, the manifest doesn't declare this table, or
            the table doesn't exist in the database.
          </p>
          <Link
            to={`/plugin/${pluginSlug}`}
            className="h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-2 transition-colors"
          >
            <Package className="w-4 h-4" /> View plugin
          </Link>
        </div>
      </div>
    );
  }

  // ── Render: loading metadata ─────────────────────────────────────────────

  if (loadingMeta) {
    return (
      <div className="max-w-[1400px] space-y-4">
        <div className="h-4 w-32 bg-secondary rounded animate-pulse" />
        <div className="h-16 bg-secondary rounded animate-pulse" />
      </div>
    );
  }

  if (!tableMeta) {
    return (
      <div className="max-w-[900px]">
        <Link
          to="/datasets"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-3 h-3" /> Back to Datasets
        </Link>
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error ?? "Failed to load table."}
        </div>
      </div>
    );
  }

  // ── Header text: row-count display ───────────────────────────────────────
  // Honest distinction: if the rows endpoint has loaded, use its `total`
  // (exact COUNT(*)). Otherwise fall back to catalog estimate; if that's
  // null too, say "row count unavailable" instead of misleading "0 rows".

  let rowCountLabel: React.ReactNode;
  if (data && typeof data.total === "number") {
    rowCountLabel = (
      <>
        {data.total.toLocaleString()} row{data.total !== 1 ? "s" : ""}
      </>
    );
  } else if (typeof tableMeta.row_count_estimate === "number") {
    rowCountLabel = (
      <>~{tableMeta.row_count_estimate.toLocaleString()} rows (estimated)</>
    );
  } else {
    rowCountLabel = <>Row count unavailable</>;
  }

  // B262: empty state semantics changed. With server-side filtering,
  // data.total reflects the filtered count. Distinguish:
  //   - filtersActive && total === 0 → "no rows match your filters"
  //   - !filtersActive && total === 0 → "table is empty"
  // The "no match on this page" pseudo-empty state from the old
  // client-side filter is gone — it can't happen anymore.
  const showEmptyAfterSearch = !loadingData && data && data.total === 0 && filtersActive;
  const showTrulyEmpty = !loadingData && data && data.total === 0 && !filtersActive;

  // ── Render: dataset detail ───────────────────────────────────────────────

  return (
    <div className="max-w-[1400px] space-y-4">
      <Link
        to="/datasets"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="w-3 h-3" /> Back to Datasets
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h2 className="font-display text-base text-foreground">
            <Link
              to={`/plugin/${pluginSlug}`}
              className="text-muted-foreground hover:text-foreground"
            >
              {pluginSlug}
            </Link>
            <span className="text-muted-foreground"> / </span>
            <span>{tableMeta.name}</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {rowCountLabel}
            <span className="font-mono-deck ml-1.5 opacity-60">
              · {tableMeta.table_type.toLowerCase()} · {tableMeta.columns.length}{" "}
              column{tableMeta.columns.length !== 1 ? "s" : ""}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search — B262: drives ?q= server-side with 300ms debounce */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search whole table…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              maxLength={100}
              className="h-8 pl-8 pr-3 w-56 rounded-md bg-secondary border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <button
            onClick={fetchData}
            disabled={loadingData}
            className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw
              className={cn("w-3.5 h-3.5", loadingData && "animate-spin")}
            />
          </button>
        </div>
      </div>

      {/* Filter chips — B262 */}
      <FilterChips
        columns={tableMeta.columns}
        filters={filters}
        onChange={onFiltersChange}
      />

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Empty states (shown OUTSIDE the table to avoid scroll-trap) */}
      {showTrulyEmpty && (
        <>
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <div className="overflow-auto max-h-[40vh] relative">
              <table className="text-xs border-collapse" style={{ tableLayout: "auto" }}>
                <thead>
                  <tr>
                    {tableMeta.columns.map((col, idx) => (
                      <SortHeader
                        key={col.name}
                        column={col}
                        active={false}
                        direction="asc"
                        onClick={() => {}}
                        isFirst={idx === 0}
                      />
                    ))}
                  </tr>
                </thead>
              </table>
            </div>
          </div>
          <div className="bg-card rounded-lg border border-dashed border-border py-12 px-4 text-center">
            <Inbox className="w-6 h-6 mx-auto mb-2 text-muted-foreground opacity-40" />
            <p className="text-sm text-muted-foreground">
              No rows in this table yet.
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Sync may be pending, or the table is genuinely empty.
            </p>
          </div>
        </>
      )}

      {showEmptyAfterSearch && (
        <div className="bg-card rounded-lg border border-dashed border-border py-8 px-4 text-center">
          <p className="text-sm text-muted-foreground">
            No rows match your {q && filters.length > 0 ? "search and filters" : q ? "search" : "filters"}.
          </p>
          <button
            onClick={clearAllFilters}
            className="text-xs text-primary hover:underline mt-2"
          >
            Clear {q && filters.length > 0 ? "all" : q ? "search" : "filters"}
          </button>
        </div>
      )}

      {/* Table — only render when there ARE rows and search has matches */}
      {data && data.rows.length > 0 && visibleRows.length > 0 && (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="overflow-auto max-h-[70vh] relative">
            <table className="text-xs border-collapse" style={{ tableLayout: "auto" }}>
              <thead>
                <tr>
                  {tableMeta.columns.map((col, idx) => (
                    <SortHeader
                      key={col.name}
                      column={col}
                      active={sortCol === col.name}
                      direction={sortCol === col.name ? sortDir : "asc"}
                      onClick={() => toggleSort(col.name)}
                      isFirst={idx === 0}
                    />
                  ))}
                </tr>
              </thead>
              <tbody>
                {loadingData &&
                  [...Array(8)].map((_, i) => (
                    <tr key={i} className="border-b border-border/50">
                      {tableMeta.columns.map((col, ci) => (
                        <td
                          key={col.name}
                          className={cn(
                            "px-3 py-1.5",
                            ci === 0 && "sticky left-0 bg-card shadow-[inset_-1px_0_0_var(--border)]",
                          )}
                        >
                          <div className="h-3 bg-secondary rounded animate-pulse w-20" />
                        </td>
                      ))}
                    </tr>
                  ))}
                {!loadingData &&
                  visibleRows.map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/50 hover:bg-secondary/20 transition-colors"
                    >
                      {tableMeta.columns.map((col, ci) => {
                        const raw = row[col.name];
                        const titleText =
                          raw === null || raw === undefined
                            ? ""
                            : typeof raw === "object"
                              ? JSON.stringify(raw)
                              : String(raw);
                        return (
                          <td
                            key={col.name}
                            title={titleText}
                            className={cn(
                              "px-3 py-1.5 text-foreground",
                              "max-w-[320px] overflow-hidden text-ellipsis whitespace-nowrap",
                              ci === 0 && "sticky left-0 bg-card shadow-[inset_-1px_0_0_var(--border)]",
                            )}
                          >
                            <Cell
                              value={raw}
                              dataType={col.data_type}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border">
              <span className="text-xs text-muted-foreground">
                Page {page} of {totalPages}
                {typeof data?.total === "number" && (
                  <>
                    {" "}· {data.total.toLocaleString()}{" "}
                    {filtersActive ? "matching" : "total"} rows
                  </>
                )}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() =>
                    updateParams(
                      { page: String(Math.max(1, page - 1)) },
                      false,
                    )
                  }
                  disabled={page === 1}
                  className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-30 transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() =>
                    updateParams(
                      { page: String(Math.min(totalPages, page + 1)) },
                      false,
                    )
                  }
                  disabled={page === totalPages}
                  className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-30 transition-colors"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loading state when no data yet */}
      {loadingData && !data && (
        <div className="bg-card rounded-lg border border-border p-4">
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-secondary rounded animate-pulse" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
