/**
 * FusionBuilder — visual editor for the FusionGraph (B263 / v0.9.11.7).
 *
 * Sits beside (does not replace) the SQL editor in the Add Widget modal.
 * Output: a FusionGraph + the compiled SQL preview. Validation surfaces
 * inline so the operator sees compile errors before save.
 *
 * Sections (collapsible):
 *   1. Sources       — pick plugin/table per source
 *   2. Joins         — kind + alias pairs + on-cols
 *   3. Filters       — alias + col + op + value (B262 op set)
 *   4. Group by      — cols + aggregations
 *   5. Sort + Limit  — single col + asc/desc + limit
 *   6. SQL preview   — read-only output of the compiler
 */

import { useEffect, useMemo, useState } from "react";
import { Plus, X, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  compileFusionGraph,
  type CompileResult,
  type SchemaColumn,
} from "@/lib/fusion-compiler";
import {
  sharedFusionSchemaCache,
} from "@/lib/fusion-schema-cache";
import {
  EMPTY_GRAPH,
  MAX_AGGREGATIONS,
  MAX_FILTERS,
  MAX_JOINS,
  MAX_LIMIT,
  MAX_SOURCES,
  type AggregationFn,
  type FilterOp,
  type FilterRef,
  type FusionGraph,
  type GroupByRef,
  type JoinKind,
  type JoinRef,
  type OrderByRef,
} from "@/lib/fusion-graph-types";

// ── Types from the catalog API ───────────────────────────────────────

interface CatalogTable {
  name: string;
  plugin_id: string;
  table_type: string;
  columns: SchemaColumn[];
  row_count_estimate: number | null;
}

interface CatalogTablesGroupedResponse {
  plugins: { id: string; tables: CatalogTable[] }[];
}

// ── Constants ───────────────────────────────────────────────────────

const FILTER_OPS: { value: FilterOp; label: string }[] = [
  { value: "eq", label: "=" },
  { value: "neq", label: "≠" },
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "gte", label: "≥" },
  { value: "lte", label: "≤" },
  { value: "contains", label: "contains" },
  { value: "startswith", label: "starts with" },
  { value: "is_null", label: "is empty" },
  { value: "not_null", label: "is not empty" },
];

const JOIN_KINDS: { value: JoinKind; label: string }[] = [
  { value: "inner", label: "INNER" },
  { value: "left", label: "LEFT" },
  { value: "right", label: "RIGHT" },
  { value: "full", label: "FULL OUTER" },
];

const AGG_FUNCTIONS: { value: AggregationFn; label: string; needsCol: boolean }[] = [
  { value: "sum", label: "SUM", needsCol: true },
  { value: "avg", label: "AVG", needsCol: true },
  { value: "min", label: "MIN", needsCol: true },
  { value: "max", label: "MAX", needsCol: true },
  { value: "count", label: "COUNT", needsCol: false },
  { value: "count_distinct", label: "COUNT DISTINCT", needsCol: true },
];

// ── Section header ───────────────────────────────────────────────────

function SectionHeader({
  title,
  count,
  open,
  onToggle,
  children,
}: {
  title: string;
  count?: number;
  open: boolean;
  onToggle: () => void;
  children?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full flex items-center justify-between px-3 py-2 rounded-t-lg bg-secondary/40 hover:bg-secondary/60 transition-colors"
    >
      <span className="flex items-center gap-2">
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
        {count !== undefined && (
          <span className="text-meta text-muted-foreground">{count}</span>
        )}
      </span>
      <span className="flex items-center gap-2">{children}</span>
    </button>
  );
}

// ── Schema-aware column dropdown ─────────────────────────────────────

function ColumnDropdown({
  alias,
  pluginId,
  table,
  value,
  onChange,
  disabled,
  className,
}: {
  alias: string;
  pluginId: string;
  table: string;
  value: string;
  onChange: (col: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  const [cols, setCols] = useState<SchemaColumn[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!pluginId || !table) {
      setCols(null);
      return;
    }
    sharedFusionSchemaCache.fetch(pluginId, table).then((c) => {
      if (!cancelled) setCols(c);
    });
    return () => {
      cancelled = true;
    };
  }, [pluginId, table]);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled || cols === null}
      title={cols === null ? "Loading schema…" : `${alias}.${value || "—"}`}
      className={cn(
        "h-7 px-2 rounded bg-secondary border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50",
        className,
      )}
    >
      <option value="">{cols === null ? "(loading)" : "(pick column)"}</option>
      {cols?.map((c) => (
        <option key={c.name} value={c.name}>
          {c.name}
          {c.data_type ? ` (${c.data_type})` : ""}
        </option>
      ))}
    </select>
  );
}

// ── Main component ──────────────────────────────────────────────────

interface FusionBuilderProps {
  graph: FusionGraph;
  onChange: (graph: FusionGraph) => void;
  /** Optional preview — read-only summary of compile output. */
  showPreview?: boolean;
}

export function FusionBuilder({ graph, onChange, showPreview = true }: FusionBuilderProps) {
  // ── Catalog: load all tables grouped by plugin so the source picker
  //    can offer a flat list of (pluginId, table) pairs.
  const [catalog, setCatalog] = useState<CatalogTablesGroupedResponse | null>(null);
  useEffect(() => {
    let cancelled = false;
    import("@/lib/api").then(({ apiFetch }) =>
      apiFetch("/api/catalog/tables")
        .then((r) => (r.ok ? r.json() : null))
        .then((c) => {
          if (!cancelled) setCatalog(c);
        }),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const allTables = useMemo<{ pluginId: string; table: string; group: string }[]>(() => {
    if (!catalog) return [];
    const out: { pluginId: string; table: string; group: string }[] = [];
    for (const p of catalog.plugins) {
      const groupLabel = p.id === "fusions" ? "Published fusions" : p.id;
      for (const t of p.tables) {
        out.push({ pluginId: p.id, table: t.name, group: groupLabel });
      }
    }
    return out;
  }, [catalog]);

  // ── Section open/closed state
  const [openSections, setOpenSections] = useState({
    sources: true,
    joins: graph.joins.length > 0,
    filters: graph.filters.length > 0,
    groupBy: graph.groupBy !== null,
    orderBy: graph.orderBy !== null,
    preview: false,
  });

  function toggleSection(k: keyof typeof openSections) {
    setOpenSections((s) => ({ ...s, [k]: !s[k] }));
  }

  // ── Compile + validate live ────────────────────────────────────────
  const compileResult: CompileResult = useMemo(() => {
    return compileFusionGraph(graph, sharedFusionSchemaCache);
  }, [graph]);

  // ── Mutators ───────────────────────────────────────────────────────
  function nextSourceAlias(): string {
    const existing = new Set(graph.sources.map((s) => s.alias));
    let i = 1;
    while (existing.has(`s${i}`)) i++;
    return `s${i}`;
  }

  function addSource(pluginId: string, table: string) {
    if (graph.sources.length >= MAX_SOURCES) return;
    onChange({
      ...graph,
      sources: [...graph.sources, { alias: nextSourceAlias(), pluginId, table }],
    });
  }

  function removeSource(alias: string) {
    onChange({
      ...graph,
      sources: graph.sources.filter((s) => s.alias !== alias),
      // Cascade: remove anything referring to this alias
      joins: graph.joins.filter((j) => j.leftAlias !== alias && j.rightAlias !== alias),
      filters: graph.filters.filter((f) => f.alias !== alias),
      groupBy: graph.groupBy
        ? {
            cols: graph.groupBy.cols.filter((c) => c.alias !== alias),
            aggregations: graph.groupBy.aggregations.filter((a) => a.alias !== alias),
          }
        : null,
    });
  }

  function addJoin() {
    if (graph.joins.length >= MAX_JOINS) return;
    if (graph.sources.length < 2) return;
    const left = graph.sources[0].alias;
    const right = graph.sources[1].alias;
    onChange({
      ...graph,
      joins: [
        ...graph.joins,
        { kind: "inner", leftAlias: left, rightAlias: right, on: { leftCol: "", rightCol: "" } },
      ],
    });
  }

  function updateJoin(idx: number, patch: Partial<JoinRef>) {
    const next = [...graph.joins];
    next[idx] = { ...next[idx], ...patch, on: { ...next[idx].on, ...(patch.on ?? {}) } };
    onChange({ ...graph, joins: next });
  }

  function removeJoin(idx: number) {
    onChange({ ...graph, joins: graph.joins.filter((_, i) => i !== idx) });
  }

  function addFilter() {
    if (graph.filters.length >= MAX_FILTERS) return;
    if (graph.sources.length === 0) return;
    onChange({
      ...graph,
      filters: [
        ...graph.filters,
        { alias: graph.sources[0].alias, col: "", op: "eq", value: "" },
      ],
    });
  }

  function updateFilter(idx: number, patch: Partial<FilterRef>) {
    const next = [...graph.filters];
    next[idx] = { ...next[idx], ...patch };
    onChange({ ...graph, filters: next });
  }

  function removeFilter(idx: number) {
    onChange({ ...graph, filters: graph.filters.filter((_, i) => i !== idx) });
  }

  function toggleGroupBy() {
    onChange({
      ...graph,
      groupBy: graph.groupBy ? null : { cols: [], aggregations: [] },
    });
  }

  function updateGroupBy(patch: Partial<GroupByRef>) {
    if (!graph.groupBy) return;
    onChange({ ...graph, groupBy: { ...graph.groupBy, ...patch } });
  }

  function addGroupCol() {
    if (!graph.groupBy || graph.sources.length === 0) return;
    updateGroupBy({
      cols: [
        ...graph.groupBy.cols,
        { alias: graph.sources[0].alias, col: "" },
      ],
    });
  }

  function addAggregation() {
    if (!graph.groupBy) return;
    if (graph.groupBy.aggregations.length >= MAX_AGGREGATIONS) return;
    const fn: AggregationFn = "count";
    updateGroupBy({
      aggregations: [
        ...graph.groupBy.aggregations,
        { fn, outputName: `metric_${graph.groupBy.aggregations.length + 1}` },
      ],
    });
  }

  function setOrderBy(orderBy: OrderByRef | null) {
    onChange({ ...graph, orderBy });
  }

  function setLimit(value: string) {
    const n = parseInt(value, 10);
    onChange({ ...graph, limit: Number.isFinite(n) && n > 0 ? Math.min(n, MAX_LIMIT) : null });
  }

  // ── Render ─────────────────────────────────────────────────────────

  const sourceLookup = (alias: string) => graph.sources.find((s) => s.alias === alias);

  return (
    <div className="space-y-3 text-xs">
      {/* SECTION: Sources */}
      <div className="rounded-lg border border-border overflow-hidden">
        <SectionHeader
          title="Sources"
          count={graph.sources.length}
          open={openSections.sources}
          onToggle={() => toggleSection("sources")}
        />
        {openSections.sources && (
          <div className="p-3 space-y-2 bg-card/50">
            {graph.sources.length === 0 && (
              <p className="text-[11px] text-muted-foreground">
                Pick a table below to start. The query runs as you build it — no need to write SQL.
              </p>
            )}
            {graph.sources.map((s, idx) => (
              <div key={s.alias} className="flex items-center gap-2">
                {/* v0.10.1.5: alias prefix removed. It's internal metadata
                    used to disambiguate joins; surfacing "s1" / "s11" in the
                    UI confused operators authoring single-source widgets.
                    When ≥2 sources exist, the joins section surfaces the
                    table names directly. */}
                <select
                  value={`${s.pluginId}::${s.table}`}
                  onChange={(e) => {
                    const [pluginId, table] = e.target.value.split("::");
                    const next = [...graph.sources];
                    next[idx] = { ...s, pluginId, table };
                    onChange({ ...graph, sources: next });
                  }}
                  className="flex-1 h-7 px-2 rounded bg-secondary border border-border text-xs"
                >
                  <option value="::">Pick a table…</option>
                  {allTables.map((t) => (
                    <option key={`${t.pluginId}::${t.table}`} value={`${t.pluginId}::${t.table}`}>
                      {t.group} → {t.table}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeSource(s.alias)}
                  className="h-6 w-6 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
                  title="Remove source"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => {
                if (allTables.length === 0) return;
                addSource(allTables[0].pluginId, allTables[0].table);
              }}
              disabled={graph.sources.length >= MAX_SOURCES || allTables.length === 0}
              className="h-7 px-2 rounded bg-secondary text-muted-foreground hover:text-foreground inline-flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Plus className="w-3 h-3" /> {graph.sources.length === 0 ? "Pick a table" : "Add another source"}
            </button>
          </div>
        )}
      </div>

      {/* SECTION: Joins */}
      {graph.sources.length >= 2 && (
        <div className="rounded-lg border border-border overflow-hidden">
          <SectionHeader
            title="Joins"
            count={graph.joins.length}
            open={openSections.joins}
            onToggle={() => toggleSection("joins")}
          />
          {openSections.joins && (
            <div className="p-3 space-y-2 bg-card/50">
              {graph.joins.map((j, idx) => {
                const left = sourceLookup(j.leftAlias);
                const right = sourceLookup(j.rightAlias);
                return (
                  <div key={idx} className="flex items-center gap-1.5 flex-wrap">
                    <select
                      value={j.kind}
                      onChange={(e) => updateJoin(idx, { kind: e.target.value as JoinKind })}
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs"
                    >
                      {JOIN_KINDS.map((k) => (
                        <option key={k.value} value={k.value}>{k.label}</option>
                      ))}
                    </select>
                    <select
                      value={j.leftAlias}
                      onChange={(e) => updateJoin(idx, { leftAlias: e.target.value })}
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs font-mono-deck"
                    >
                      {graph.sources.map((s) => <option key={s.alias} value={s.alias}>{s.alias}</option>)}
                    </select>
                    {left && (
                      <ColumnDropdown
                        alias={j.leftAlias}
                        pluginId={left.pluginId}
                        table={left.table}
                        value={j.on.leftCol}
                        onChange={(col) => updateJoin(idx, { on: { leftCol: col, rightCol: j.on.rightCol } })}
                      />
                    )}
                    <span className="text-muted-foreground">=</span>
                    <select
                      value={j.rightAlias}
                      onChange={(e) => updateJoin(idx, { rightAlias: e.target.value })}
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs font-mono-deck"
                    >
                      {graph.sources.map((s) => <option key={s.alias} value={s.alias}>{s.alias}</option>)}
                    </select>
                    {right && (
                      <ColumnDropdown
                        alias={j.rightAlias}
                        pluginId={right.pluginId}
                        table={right.table}
                        value={j.on.rightCol}
                        onChange={(col) => updateJoin(idx, { on: { leftCol: j.on.leftCol, rightCol: col } })}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => removeJoin(idx)}
                      className="h-6 w-6 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
                      title="Remove join"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
              <button
                type="button"
                onClick={addJoin}
                disabled={graph.joins.length >= MAX_JOINS}
                className="h-7 px-2 rounded bg-secondary text-muted-foreground hover:text-foreground inline-flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Plus className="w-3 h-3" /> Add join
              </button>
            </div>
          )}
        </div>
      )}

      {/* SECTION: Filters */}
      <div className="rounded-lg border border-border overflow-hidden">
        <SectionHeader
          title="Filters"
          count={graph.filters.length}
          open={openSections.filters}
          onToggle={() => toggleSection("filters")}
        />
        {openSections.filters && (
          <div className="p-3 space-y-2 bg-card/50">
            {graph.filters.map((f, idx) => {
              const src = sourceLookup(f.alias);
              const isNullOp = f.op === "is_null" || f.op === "not_null";
              return (
                <div key={idx} className="flex items-center gap-1.5 flex-wrap">
                  <select
                    value={f.alias}
                    onChange={(e) => updateFilter(idx, { alias: e.target.value })}
                    className="h-7 px-2 rounded bg-secondary border border-border text-xs font-mono-deck"
                  >
                    {graph.sources.map((s) => <option key={s.alias} value={s.alias}>{s.alias}</option>)}
                  </select>
                  {src && (
                    <ColumnDropdown
                      alias={f.alias}
                      pluginId={src.pluginId}
                      table={src.table}
                      value={f.col}
                      onChange={(col) => updateFilter(idx, { col })}
                    />
                  )}
                  <select
                    value={f.op}
                    onChange={(e) => updateFilter(idx, { op: e.target.value as FilterOp })}
                    className="h-7 px-2 rounded bg-secondary border border-border text-xs"
                  >
                    {FILTER_OPS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  {!isNullOp && (
                    <input
                      type="text"
                      value={f.value ?? ""}
                      onChange={(e) => updateFilter(idx, { value: e.target.value })}
                      placeholder="value"
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs flex-1 min-w-[100px]"
                    />
                  )}
                  <button
                    type="button"
                    onClick={() => removeFilter(idx)}
                    className="h-6 w-6 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
                    title="Remove filter"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
            <button
              type="button"
              onClick={addFilter}
              disabled={graph.filters.length >= MAX_FILTERS || graph.sources.length === 0}
              className="h-7 px-2 rounded bg-secondary text-muted-foreground hover:text-foreground inline-flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Plus className="w-3 h-3" /> Add filter
            </button>
          </div>
        )}
      </div>

      {/* SECTION: Group by */}
      <div className="rounded-lg border border-border overflow-hidden">
        <SectionHeader
          title="Group by + aggregations"
          count={graph.groupBy ? graph.groupBy.cols.length + graph.groupBy.aggregations.length : 0}
          open={openSections.groupBy}
          onToggle={() => toggleSection("groupBy")}
        >
          <input
            type="checkbox"
            checked={graph.groupBy !== null}
            onChange={(e) => {
              e.stopPropagation();
              toggleGroupBy();
            }}
            onClick={(e) => e.stopPropagation()}
            className="h-3.5 w-3.5"
          />
        </SectionHeader>
        {openSections.groupBy && graph.groupBy && (
          <div className="p-3 space-y-3 bg-card/50">
            <div className="space-y-2">
              <p className="text-meta uppercase tracking-wider text-muted-foreground">Group columns</p>
              {graph.groupBy.cols.map((c, idx) => {
                const src = sourceLookup(c.alias);
                return (
                  <div key={idx} className="flex items-center gap-1.5">
                    <select
                      value={c.alias}
                      onChange={(e) => {
                        const next = [...graph.groupBy!.cols];
                        next[idx] = { ...c, alias: e.target.value };
                        updateGroupBy({ cols: next });
                      }}
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs font-mono-deck"
                    >
                      {graph.sources.map((s) => <option key={s.alias} value={s.alias}>{s.alias}</option>)}
                    </select>
                    {src && (
                      <ColumnDropdown
                        alias={c.alias}
                        pluginId={src.pluginId}
                        table={src.table}
                        value={c.col}
                        onChange={(col) => {
                          const next = [...graph.groupBy!.cols];
                          next[idx] = { ...c, col };
                          updateGroupBy({ cols: next });
                        }}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => updateGroupBy({ cols: graph.groupBy!.cols.filter((_, i) => i !== idx) })}
                      className="h-6 w-6 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
              <button
                type="button"
                onClick={addGroupCol}
                disabled={graph.sources.length === 0}
                className="h-7 px-2 rounded bg-secondary text-muted-foreground hover:text-foreground inline-flex items-center gap-1 disabled:opacity-40"
              >
                <Plus className="w-3 h-3" /> Add group column
              </button>
            </div>
            <div className="space-y-2 pt-2 border-t border-border">
              <p className="text-meta uppercase tracking-wider text-muted-foreground">Aggregations</p>
              {graph.groupBy.aggregations.map((a, idx) => {
                const fnDef = AGG_FUNCTIONS.find((f) => f.value === a.fn)!;
                const src = a.alias ? sourceLookup(a.alias) : undefined;
                return (
                  <div key={idx} className="flex items-center gap-1.5 flex-wrap">
                    <select
                      value={a.fn}
                      onChange={(e) => {
                        const next = [...graph.groupBy!.aggregations];
                        next[idx] = { ...a, fn: e.target.value as AggregationFn };
                        updateGroupBy({ aggregations: next });
                      }}
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs"
                    >
                      {AGG_FUNCTIONS.map((fn) => <option key={fn.value} value={fn.value}>{fn.label}</option>)}
                    </select>
                    {fnDef.needsCol && (
                      <>
                        <select
                          value={a.alias ?? ""}
                          onChange={(e) => {
                            const next = [...graph.groupBy!.aggregations];
                            next[idx] = { ...a, alias: e.target.value };
                            updateGroupBy({ aggregations: next });
                          }}
                          className="h-7 px-2 rounded bg-secondary border border-border text-xs font-mono-deck"
                        >
                          <option value="">(alias)</option>
                          {graph.sources.map((s) => <option key={s.alias} value={s.alias}>{s.alias}</option>)}
                        </select>
                        {src && (
                          <ColumnDropdown
                            alias={a.alias!}
                            pluginId={src.pluginId}
                            table={src.table}
                            value={a.col ?? ""}
                            onChange={(col) => {
                              const next = [...graph.groupBy!.aggregations];
                              next[idx] = { ...a, col };
                              updateGroupBy({ aggregations: next });
                            }}
                          />
                        )}
                      </>
                    )}
                    <span className="text-muted-foreground">AS</span>
                    <input
                      type="text"
                      value={a.outputName}
                      onChange={(e) => {
                        const next = [...graph.groupBy!.aggregations];
                        next[idx] = { ...a, outputName: e.target.value };
                        updateGroupBy({ aggregations: next });
                      }}
                      placeholder="output_name"
                      className="h-7 px-2 rounded bg-secondary border border-border text-xs flex-1 min-w-[120px] font-mono-deck"
                    />
                    <button
                      type="button"
                      onClick={() => updateGroupBy({ aggregations: graph.groupBy!.aggregations.filter((_, i) => i !== idx) })}
                      className="h-6 w-6 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })}
              <button
                type="button"
                onClick={addAggregation}
                disabled={graph.groupBy.aggregations.length >= MAX_AGGREGATIONS}
                className="h-7 px-2 rounded bg-secondary text-muted-foreground hover:text-foreground inline-flex items-center gap-1 disabled:opacity-40"
              >
                <Plus className="w-3 h-3" /> Add aggregation
              </button>
            </div>
          </div>
        )}
      </div>

      {/* SECTION: Sort + Limit */}
      <div className="rounded-lg border border-border overflow-hidden">
        <SectionHeader
          title="Sort + Limit"
          open={openSections.orderBy}
          onToggle={() => toggleSection("orderBy")}
        />
        {openSections.orderBy && (
          <div className="p-3 space-y-2 bg-card/50">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">ORDER BY</span>
              <input
                type="text"
                value={graph.orderBy?.col ?? ""}
                onChange={(e) => {
                  const col = e.target.value;
                  if (!col) {
                    setOrderBy(null);
                  } else {
                    setOrderBy({ col, direction: graph.orderBy?.direction ?? "asc" });
                  }
                }}
                placeholder="output_name or s1.col"
                className="h-7 px-2 rounded bg-secondary border border-border text-xs flex-1 font-mono-deck"
              />
              <select
                value={graph.orderBy?.direction ?? "asc"}
                onChange={(e) =>
                  graph.orderBy &&
                  setOrderBy({ ...graph.orderBy, direction: e.target.value as "asc" | "desc" })
                }
                className="h-7 px-2 rounded bg-secondary border border-border text-xs"
                disabled={!graph.orderBy}
              >
                <option value="asc">ASC</option>
                <option value="desc">DESC</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">LIMIT</span>
              <input
                type="number"
                value={graph.limit ?? ""}
                min={1}
                max={MAX_LIMIT}
                onChange={(e) => setLimit(e.target.value)}
                placeholder="(none)"
                className="h-7 px-2 rounded bg-secondary border border-border text-xs w-32 font-mono-deck"
              />
            </div>
          </div>
        )}
      </div>

      {/* SECTION: Compile result — v0.10.1.6: suppress the red banner
          when the operator just hasn't picked a source yet. The Sources
          section already shows the "Pick a table below to start" hint;
          a second "Compile errors / must have at least one source"
          banner reads as a real failure when it's just "incomplete". */}
      {!compileResult.ok && graph.sources.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
          <div className="text-xs text-red-300 space-y-0.5">
            <p className="font-semibold">Compile errors</p>
            <ul className="list-disc pl-4 opacity-90">
              {compileResult.errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          </div>
        </div>
      )}
      {showPreview && compileResult.ok && (
        <details className="rounded-lg border border-border overflow-hidden" open={openSections.preview}>
          <summary
            className="cursor-pointer px-3 py-2 bg-secondary/40 hover:bg-secondary/60 text-xs font-semibold uppercase tracking-wider"
            onClick={(e) => {
              e.preventDefault();
              toggleSection("preview");
            }}
          >
            Generated SQL
          </summary>
          <pre className="p-3 bg-card/50 text-xs font-mono-deck whitespace-pre-wrap text-foreground overflow-x-auto">
{compileResult.sql}
            {compileResult.params.length > 0 && (
              <>
                {"\n\n-- params: "}
                {JSON.stringify(compileResult.params)}
              </>
            )}
          </pre>
        </details>
      )}
    </div>
  );
}

// ── Helper: build the empty graph for new widgets ───────────────────

export function emptyGraph(): FusionGraph {
  // Spread to avoid handing out the singleton.
  return {
    ...EMPTY_GRAPH,
    sources: [],
    joins: [],
    filters: [],
  };
}
