import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Database,
  Inbox,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface Column {
  name: string;
  data_type: string;
  is_nullable: boolean;
  ordinal_position: number;
}

interface TableMeta {
  name: string;
  schema: string;
  connection_id: string;
  table_type: string;
  row_count_estimate: number | null;
  columns: Column[];
}

interface RowsResponse {
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  limit: number;
}

const DEFAULT_LIMIT = 50;
const CELL_TRUNCATE = 80;

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

export default function ConnectionTableRowsPage() {
  useMarkBootReadyOnMount();
  const { id, schema, table } = useParams<{
    id: string;
    schema: string;
    table: string;
  }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10) || 1);
  const q = searchParams.get("q") ?? "";
  const sortCol = searchParams.get("sort") ?? "";
  const sortDir = (searchParams.get("dir") === "desc" ? "desc" : "asc") as "asc" | "desc";

  const [meta, setMeta] = useState<TableMeta | null>(null);
  const [data, setData] = useState<RowsResponse | null>(null);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState(q);
  const [selectedRow, setSelectedRow] = useState<Record<string, unknown> | null>(null);
  useEffect(() => setSearchInput(q), [q]);

  const updateParams = useCallback(
    (patch: Record<string, string | null>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            if (v === null || v === "") next.delete(k);
            else next.set(k, v);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const baseUrl = useMemo(() => {
    if (!id || !schema || !table) return null;
    return `/api/connections/${encodeURIComponent(id)}/tables/${encodeURIComponent(schema)}/${encodeURIComponent(table)}`;
  }, [id, schema, table]);

  // Load schema
  useEffect(() => {
    if (!baseUrl) return;
    setLoadingMeta(true);
    setError(null);
    apiFetch(baseUrl)
      .then(async (r) => {
        if (!r.ok) {
          let detail = await r.text();
          try {
            const parsed = JSON.parse(detail);
            if (parsed?.detail) detail = String(parsed.detail);
          } catch {
            /* keep raw */
          }
          throw new Error(detail);
        }
        return r.json();
      })
      .then((m: TableMeta) => setMeta(m))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load table"),
      )
      .finally(() => setLoadingMeta(false));
  }, [baseUrl]);

  // Fetch rows
  const fetchRows = useCallback(async () => {
    if (!baseUrl || !meta) return;
    setLoadingData(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(DEFAULT_LIMIT),
      });
      if (q) params.set("q", q);
      if (sortCol) params.set("sort", `${sortCol} ${sortDir}`);
      const res = await apiFetch(`${baseUrl}/rows?${params}`);
      if (!res.ok) {
        let detail = await res.text();
        try {
          const parsed = JSON.parse(detail);
          if (parsed?.detail) detail = String(parsed.detail);
        } catch {
          /* keep raw */
        }
        throw new Error(detail);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load rows");
      setData(null);
    } finally {
      setLoadingData(false);
    }
  }, [baseUrl, meta, page, q, sortCol, sortDir]);

  // Tri-state sort cycle: unsorted → asc → desc → unsorted
  const cycleSort = useCallback(
    (col: string) => {
      if (sortCol !== col) {
        updateParams({ sort: col, dir: "asc", page: null });
      } else if (sortDir === "asc") {
        updateParams({ sort: col, dir: "desc", page: null });
      } else {
        updateParams({ sort: null, dir: null, page: null });
      }
    },
    [sortCol, sortDir, updateParams],
  );

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  // ESC closes the row detail panel
  useEffect(() => {
    if (!selectedRow) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedRow(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedRow]);

  // Debounce search -> URL ?q=
  const debounceTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (searchInput === q) return;
    if (debounceTimer.current !== undefined)
      window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(() => {
      updateParams({ q: searchInput || null, page: null });
    }, 300);
    return () => {
      if (debounceTimer.current !== undefined)
        window.clearTimeout(debounceTimer.current);
    };
  }, [searchInput, q, updateParams]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 0;

  if (loadingMeta) {
    return (
      <div className="max-w-[1400px] space-y-4">
        <div className="h-4 w-32 bg-secondary rounded animate-pulse" />
        <div className="h-16 bg-secondary rounded animate-pulse" />
      </div>
    );
  }

  if (error && !meta) {
    return (
      <div className="max-w-[900px] space-y-4">
        <Link
          to={`/connections/${id}`}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-3 h-3" /> Back to connection
        </Link>
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!meta) return null;

  return (
    <div className="max-w-[1400px] space-y-4">
      <Link
        to={`/connections/${id}`}
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="w-3 h-3" /> Back to connection
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h2 className="font-display text-base text-foreground">
            <span className="text-muted-foreground">{meta.schema}</span>
            <span className="text-muted-foreground"> / </span>
            <span>{meta.name}</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {data && typeof data.total === "number" ? (
              <>
                {data.total.toLocaleString()} row{data.total !== 1 ? "s" : ""}
              </>
            ) : typeof meta.row_count_estimate === "number" ? (
              <>~{meta.row_count_estimate.toLocaleString()} rows (estimated)</>
            ) : (
              <>Row count unavailable</>
            )}
            <span className="font-mono-deck ml-1.5 opacity-60">
              · {meta.table_type.toLowerCase()} · {meta.columns.length} column
              {meta.columns.length !== 1 ? "s" : ""}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2">
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
            onClick={fetchRows}
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

      {/* Error banner (when rows fail but meta succeeded) */}
      {error && meta && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Truly empty */}
      {!loadingData && data && data.total === 0 && !q && (
        <div className="bg-card rounded-lg border border-dashed border-border py-12 px-4 text-center">
          <Inbox className="w-6 h-6 mx-auto mb-2 text-muted-foreground opacity-40" />
          <p className="text-sm text-muted-foreground">
            No rows in this table yet.
          </p>
        </div>
      )}

      {/* No match */}
      {!loadingData && data && data.total === 0 && q && (
        <div className="bg-card rounded-lg border border-dashed border-border py-8 px-4 text-center">
          <p className="text-sm text-muted-foreground">
            No rows match your search.
          </p>
          <button
            onClick={() => updateParams({ q: null, page: null })}
            className="text-xs text-primary hover:underline mt-2"
          >
            Clear search
          </button>
        </div>
      )}

      {/* Table */}
      {data && data.rows.length > 0 && (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="overflow-auto max-h-[70vh] relative">
            <table className="text-xs border-collapse" style={{ tableLayout: "auto" }}>
              <thead>
                <tr>
                  {meta.columns.map((col, idx) => {
                    const active = sortCol === col.name;
                    return (
                      <th
                        key={col.name}
                        title={`${col.data_type}${col.is_nullable ? " (nullable)" : ""} — click to sort`}
                        className={cn(
                          "px-3 py-1.5 text-left font-display text-muted-foreground whitespace-nowrap border-b border-border bg-card sticky top-0",
                          idx === 0
                            ? "sticky left-0 z-20 shadow-[inset_-1px_0_0_var(--border)]"
                            : "z-10",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => cycleSort(col.name)}
                          className={cn(
                            "inline-flex items-center gap-1 hover:text-foreground transition-colors",
                            active && "text-foreground",
                          )}
                        >
                          <span>{col.name}</span>
                          {active ? (
                            sortDir === "asc" ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 opacity-30" />
                          )}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {!loadingData &&
                  data.rows.map((row, i) => (
                    <tr
                      key={i}
                      onClick={() => setSelectedRow(row)}
                      className="border-b border-border/50 hover:bg-secondary/20 transition-colors cursor-pointer"
                    >
                      {meta.columns.map((col, ci) => {
                        const raw = row[col.name];
                        const formatted = formatCell(raw, col.data_type);
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
                              ci === 0 &&
                                "sticky left-0 bg-card shadow-[inset_-1px_0_0_var(--border)]",
                            )}
                          >
                            {formatted === "—" ? (
                              <span className="text-muted-foreground">—</span>
                            ) : formatted.length > CELL_TRUNCATE ? (
                              <span>{formatted.slice(0, CELL_TRUNCATE)}…</span>
                            ) : (
                              <span>{formatted}</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                {loadingData &&
                  [...Array(8)].map((_, i) => (
                    <tr key={i} className="border-b border-border/50">
                      {meta.columns.map((col, ci) => (
                        <td
                          key={col.name}
                          className={cn(
                            "px-3 py-1.5",
                            ci === 0 &&
                              "sticky left-0 bg-card shadow-[inset_-1px_0_0_var(--border)]",
                          )}
                        >
                          <div className="h-3 bg-secondary rounded animate-pulse w-20" />
                        </td>
                      ))}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border">
              <span className="text-xs text-muted-foreground">
                Page {page} of {totalPages}
                {typeof data.total === "number" && (
                  <>
                    {" "}· {data.total.toLocaleString()} {q ? "matching" : "total"} rows
                  </>
                )}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() =>
                    updateParams({ page: String(Math.max(1, page - 1)) })
                  }
                  disabled={page === 1}
                  className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-30 transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() =>
                    updateParams({
                      page: String(Math.min(totalPages, page + 1)),
                    })
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

      {/* Loading first fetch */}
      {loadingData && !data && (
        <div className="bg-card rounded-lg border border-border p-4">
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div
                key={`l-${i}-${Database.name.length}`}
                className="h-4 bg-secondary rounded animate-pulse"
              />
            ))}
          </div>
        </div>
      )}

      {/* Row detail side panel */}
      {selectedRow && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/50"
          onClick={() => setSelectedRow(null)}
        >
          <div
            className="w-full max-w-[480px] h-full bg-card border-l border-border shadow-xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-card border-b border-border px-5 py-3 flex items-center justify-between z-10">
              <div className="min-w-0">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                  Row detail
                </p>
                <p className="text-xs text-foreground font-mono-deck truncate">
                  {meta.schema}.{meta.name}
                </p>
              </div>
              <button
                onClick={() => setSelectedRow(null)}
                className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors shrink-0"
                title="Close (Esc)"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="divide-y divide-border/50">
              {meta.columns.map((col) => {
                const raw = selectedRow[col.name];
                const isNull = raw === null || raw === undefined;
                const isObject = !isNull && typeof raw === "object";
                const pretty = isNull
                  ? "—"
                  : isObject
                    ? JSON.stringify(raw, null, 2)
                    : String(raw);
                return (
                  <div key={col.name} className="px-5 py-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-mono-deck text-foreground">
                        {col.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground font-mono-deck">
                        {col.data_type}
                      </span>
                      {col.is_nullable && (
                        <span className="text-[10px] text-muted-foreground">nullable</span>
                      )}
                    </div>
                    {isNull ? (
                      <p className="text-xs text-muted-foreground italic">null</p>
                    ) : isObject ? (
                      <pre className="text-xs font-mono-deck text-foreground bg-secondary/30 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                        {pretty}
                      </pre>
                    ) : (
                      <p className="text-xs text-foreground break-all whitespace-pre-wrap">
                        {pretty}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
