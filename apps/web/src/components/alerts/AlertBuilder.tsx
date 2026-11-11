/**
 * P230 / B345: the alert builder.
 *
 * Step 1 — where the data is: a plugin dataset, a table on a connection,
 *          a core table, or a plugin's ready-made alert. Every source shows
 *          its database (Postgres, ClickHouse, MySQL); one that can't run is
 *          greyed out with the reason.
 * Step 2 — map the columns: date column, value (column, count or ratio),
 *          up to three group-by columns, filters, minimum volume and a
 *          currency column. Ready-made alerts show their parameters instead.
 * Step 3 — name, condition, period, comparison, schedule, channels, and a
 *          live Preview that shows which groups would fire and the SQL.
 *
 * The server decides the engine, connection and table from the source id;
 * this component only sends the mapping.
 */
import { apiFetch } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ChevronRight, Database, Link2, Plug, Plus, Sparkles, Trash2, X, Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { defaultAlertChannels, fetchSmtpConfigured } from "@/lib/email-status";

// ── Types ───────────────────────────────────────────────────────────────────

export interface SourceEntry {
  id: string;
  label: string;
  source_type: string;
  source_label: string;
  table?: string;
  plugin_id?: string;
  row_estimate?: number;
  engine?: string;
  available?: boolean;
  unavailable_reason?: string | null;
  needs_table?: boolean;
  columns: { name: string; type: string }[];
}

export interface QueryEntry {
  id: string;
  query_id: string;
  plugin_id: string;
  label: string;
  description?: string;
  engine: string;
  params: Record<string, { type?: string; default?: unknown; label?: string; options?: string[] }>;
  default_condition?: { type?: string; threshold?: number };
  default_period?: string;
  value_label?: string;
  sql?: string;
  available?: boolean;
  unavailable_reason?: string | null;
}

interface SourcesResponse {
  postgres: SourceEntry[];
  connections: SourceEntry[];
  plugins: SourceEntry[];
  queries?: QueryEntry[];
}

interface ColumnInfo { name: string; type: string; kind: string }

interface ColumnsResponse {
  engine: string;
  table: string;
  database?: string;
  table_engine?: string;
  columns: ColumnInfo[];
  suggested_date_column?: string;
  suggested_currency_column?: string;
}

interface FilterRow { column: string; op: string; value: string }

interface PreviewRow { group: string; current_value: number; baseline: number; change_pct?: number | null; fired: boolean }

interface PreviewResponse {
  status: string;
  engine: string;
  sql?: string;
  rows_checked?: number;
  elapsed_ms?: number;
  error?: string | null;
  fired?: boolean;
  fired_count?: number;
  rows?: PreviewRow[];
  period?: string[];
}

// ── Options ─────────────────────────────────────────────────────────────────

const CONDITIONS = [
  { value: "threshold_drop", label: "Drops by more than…", hint: "% vs the comparison" },
  { value: "threshold_rise", label: "Rises by more than…", hint: "% vs the comparison" },
  { value: "absolute_below", label: "Falls below a value…", hint: "fixed number" },
  { value: "absolute_above", label: "Rises above a value…", hint: "fixed number" },
  { value: "zero_check", label: "Drops to zero", hint: "had data before" },
];

const PERIODS = [
  { value: "yesterday", label: "Yesterday" },
  { value: "today", label: "Today" },
  { value: "today_or_yesterday", label: "Today or yesterday" },
  { value: "this_week", label: "This week" },
  { value: "rolling_7d", label: "Last 7 days" },
  { value: "rolling_30d", label: "Last 30 days" },
  { value: "this_month", label: "This month" },
  { value: "last_month", label: "Last full month" },
];

const COMPARISONS = [
  { value: "7d_avg", label: "7-day average" },
  { value: "14d_avg", label: "14-day average" },
  { value: "30d_avg", label: "30-day average" },
  { value: "previous_period", label: "Previous period" },
  { value: "same_period_last_month", label: "Same period last month" },
];

const AGGREGATIONS = [
  { value: "sum", label: "Sum" },
  { value: "avg", label: "Average" },
  { value: "min", label: "Minimum" },
  { value: "max", label: "Maximum" },
  { value: "count_distinct", label: "Count distinct" },
];

const FILTER_OPS = [
  { value: "eq", label: "=" },
  { value: "neq", label: "≠" },
  { value: "in", label: "is one of" },
  { value: "not_in", label: "is not one of" },
  { value: "contains", label: "contains" },
  { value: "gt", label: ">" },
  { value: "gte", label: "≥" },
  { value: "lt", label: "<" },
  { value: "lte", label: "≤" },
  { value: "empty", label: "is empty" },
  { value: "not_empty", label: "is not empty" },
];

const FREQUENCIES = [
  { value: "hourly", label: "Every hour" },
  { value: "daily", label: "Once a day" },
];

const ENGINE_LABEL: Record<string, string> = { postgres: "Postgres", clickhouse: "ClickHouse", mysql: "MySQL" };

const inputCls =
  "w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary";
const labelCls = "block text-xs font-medium text-muted-foreground mb-1.5";

async function errorText(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
  } catch {
    return `Request failed (${res.status})`;
  }
}

function EngineBadge({ engine }: { engine?: string }) {
  const e = engine || "postgres";
  return (
    <span className={cn(
      "text-[10px] px-1.5 py-0.5 rounded font-mono-deck shrink-0",
      e === "clickhouse" ? "bg-yellow-500/10 text-warning-foreground"
        : e === "mysql" ? "bg-purple-500/10 text-purple-700 dark:text-purple-400"
          : "bg-blue-500/10 text-info-foreground",
    )}>
      {ENGINE_LABEL[e] ?? e}
    </span>
  );
}

function fmt(n: number): string {
  if (!Number.isFinite(n)) return "–";
  const abs = Math.abs(n);
  if (abs !== 0 && abs < 1) return n.toFixed(4);
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

// ── Component ───────────────────────────────────────────────────────────────

export function AlertBuilder<T>({ onClose, onCreate, outboundWebhooks }: {
  onClose: () => void;
  onCreate: (a: T) => void;
  outboundWebhooks: { id: string; name: string }[];
}) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [source, setSource] = useState<SourceEntry | null>(null);
  const [query, setQuery] = useState<QueryEntry | null>(null);
  const [tables, setTables] = useState<string[] | null>(null);
  const [table, setTable] = useState("");
  const [showCore, setShowCore] = useState(false);

  // Step 2: mapping
  const [cols, setCols] = useState<ColumnsResponse | null>(null);
  const [colsError, setColsError] = useState<string | null>(null);
  const [dateColumn, setDateColumn] = useState("");
  const [valueKind, setValueKind] = useState<"column" | "count" | "ratio">("column");
  const [metric, setMetric] = useState("");
  const [aggregation, setAggregation] = useState("sum");
  const [denominator, setDenominator] = useState("");
  const [groupBy, setGroupBy] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterRow[]>([]);
  const [suggestions, setSuggestions] = useState<Record<string, string[]>>({});
  const [minVolumeColumn, setMinVolumeColumn] = useState("");
  const [minVolume, setMinVolume] = useState("");
  const [currencyColumn, setCurrencyColumn] = useState("");
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});

  // Step 3: rule
  const [label, setLabel] = useState("");
  const [conditionType, setConditionType] = useState("threshold_drop");
  const [threshold, setThreshold] = useState("-20");
  const [period, setPeriod] = useState("yesterday");
  const [compareTo, setCompareTo] = useState("7d_avg");
  const [frequency, setFrequency] = useState("daily");
  const [notifyChannels, setNotifyChannels] = useState<string[]>(["log"]);
  const [smtpConfigured, setSmtpConfigured] = useState<boolean | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [showSql, setShowSql] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSmtpConfigured().then(ok => {
      if (cancelled) return;
      setSmtpConfigured(ok);
      setNotifyChannels(defaultAlertChannels(ok));
    });
    apiFetch("/api/alerts/sources")
      .then(r => r.json())
      .then(d => { if (!cancelled) setSources(d); })
      .catch(() => { if (!cancelled) setSources({ postgres: [], connections: [], plugins: [], queries: [] }); });
    return () => { cancelled = true; };
  }, []);

  // A connection needs a table: load its list when chosen.
  useEffect(() => {
    setTables(null);
    setTable("");
    if (!source?.needs_table) return;
    apiFetch(`/api/alerts/sources/tables?source_id=${encodeURIComponent(source.id)}`)
      .then(async r => (r.ok ? r.json() : Promise.reject(await errorText(r))))
      .then(d => setTables(d.tables ?? []))
      .catch(e => { setTables([]); setColsError(String(e)); });
  }, [source]);

  // Load the real columns for step 2.
  useEffect(() => {
    if (step !== 2 || !source || query) return;
    if (source.needs_table && !table) return;
    setCols(null);
    setColsError(null);
    const qs = new URLSearchParams({ source_id: source.id });
    if (table) qs.set("table", table);
    apiFetch(`/api/alerts/sources/columns?${qs}`)
      .then(async r => (r.ok ? r.json() : Promise.reject(await errorText(r))))
      .then((d: ColumnsResponse) => {
        setCols(d);
        setDateColumn(c => c || d.suggested_date_column || "");
        setCurrencyColumn(c => c || d.suggested_currency_column || "");
      })
      .catch(e => setColsError(String(e)));
  }, [step, source, table, query]);

  const dateCols = useMemo(() => (cols?.columns ?? []).filter(c => c.kind === "date" || c.kind === "datetime"), [cols]);
  const numberCols = useMemo(() => (cols?.columns ?? []).filter(c => c.kind === "number" || c.kind === "bool"), [cols]);
  const groupCols = useMemo(() => (cols?.columns ?? []).filter(c => c.kind !== "other"), [cols]);
  const textCols = useMemo(() => (cols?.columns ?? []).filter(c => c.kind === "text"), [cols]);

  function loadSuggestions(column: string) {
    if (!source || !column || suggestions[column]) return;
    const qs = new URLSearchParams({ source_id: source.id, column });
    if (table) qs.set("table", table);
    apiFetch(`/api/alerts/sources/values?${qs}`)
      .then(r => (r.ok ? r.json() : { values: [] }))
      .then(d => setSuggestions(s => ({ ...s, [column]: (d.values ?? []).map(String) })))
      .catch(() => undefined);
  }

  function pickSource(s: SourceEntry) {
    if (s.available === false) return;
    setSource(s); setQuery(null); setCols(null); setColsError(null);
    setMetric(""); setDenominator(""); setGroupBy([]); setFilters([]); setDateColumn(""); setCurrencyColumn("");
    setPreview(null);
  }

  function pickQuery(q: QueryEntry) {
    if (q.available === false) return;
    setQuery(q); setSource(null); setPreview(null);
    const defaults: Record<string, string> = {};
    Object.entries(q.params || {}).forEach(([k, p]) => { defaults[k] = p.default != null ? String(p.default) : ""; });
    setQueryParams(defaults);
    if (q.default_condition?.type) setConditionType(q.default_condition.type);
    if (q.default_condition?.threshold != null) setThreshold(String(q.default_condition.threshold));
    if (q.default_period) setPeriod(q.default_period);
    setLabel(l => l || q.label);
  }

  function body() {
    const base: Record<string, unknown> = {
      name: (label.trim() || "alert").toLowerCase().replace(/\s+/g, "_"),
      label: label.trim() || "Preview",
      condition_type: conditionType,
      threshold: conditionType !== "zero_check" ? parseFloat(threshold) : undefined,
      compare_to: compareTo,
      check_period: period,
      check_frequency: frequency,
      notify_channels: notifyChannels,
      enabled: true,
    };
    if (query) return { ...base, source_id: query.id, query_params: queryParams };
    return {
      ...base,
      source_id: source?.id,
      table: table || undefined,
      date_column: dateColumn,
      value_kind: valueKind,
      metric: valueKind === "count" ? "*" : metric,
      aggregation: valueKind === "ratio" ? "sum" : aggregation,
      denominator: valueKind === "ratio" ? denominator : undefined,
      denominator_aggregation: valueKind === "ratio" ? "sum" : undefined,
      group_by_columns: groupBy.filter(Boolean),
      filters: filters.filter(f => f.column).map(f => ({ column: f.column, op: f.op, value: f.value })),
      min_volume_column: minVolumeColumn || undefined,
      min_volume: minVolumeColumn && minVolume !== "" ? parseFloat(minVolume) : undefined,
      currency_column: currencyColumn || undefined,
    };
  }

  async function runPreview() {
    setPreviewing(true); setError(null);
    try {
      const res = await apiFetch("/api/alerts/preview", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body()),
      });
      if (!res.ok) throw new Error(await errorText(res));
      setPreview(await res.json());
    } catch (e) {
      setPreview(null);
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim()) return;
    setSaving(true); setError(null);
    try {
      const res = await apiFetch("/api/alerts", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body()),
      });
      if (!res.ok) throw new Error(await errorText(res));
      onCreate(await res.json());
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create alert");
      setSaving(false);
    }
  }

  const mappingReady = query
    ? Object.entries(query.params || {}).every(([k]) => (queryParams[k] ?? "") !== "")
    : !!dateColumn && (valueKind === "count" || (!!metric && (valueKind !== "ratio" || !!denominator)));
  const step1Ready = !!query || (!!source && (!source.needs_table || !!table));

  // ── Source lists ──
  const pluginSources: SourceEntry[] = sources
    ? [...sources.plugins, ...sources.postgres.filter(s => s.source_type === "plugin_postgres")] : [];
  const pluginGroups = pluginSources.reduce<Record<string, SourceEntry[]>>((acc, s) => {
    (acc[s.source_label] ||= []).push(s); return acc;
  }, {});
  const connSources = sources?.connections ?? [];
  const coreSources = sources ? sources.postgres.filter(s => s.source_type !== "plugin_postgres") : [];
  const queries = sources?.queries ?? [];

  function sourceButton(s: SourceEntry, Icon: typeof Plug) {
    const active = source?.id === s.id;
    const off = s.available === false;
    return (
      <button key={s.id} type="button" onClick={() => pickSource(s)} disabled={off}
        title={off ? s.unavailable_reason ?? undefined : undefined}
        className={cn(
          "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all",
          off ? "border-border opacity-50 cursor-not-allowed"
            : active ? "border-primary bg-primary/5 ring-1 ring-primary/20"
              : "border-border hover:border-primary/30 hover:bg-secondary/30",
        )}>
        <div className="h-8 w-8 rounded-md flex items-center justify-center shrink-0 bg-secondary text-muted-foreground">
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <p className="text-sm text-foreground truncate">{s.label}</p>
            <EngineBadge engine={s.engine} />
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {off ? s.unavailable_reason
              : s.needs_table ? "Choose a table after selecting"
                : s.columns.length > 0 ? `${s.columns.length} columns` : "columns load on the next step"}
            {!off && s.row_estimate ? ` · ~${s.row_estimate.toLocaleString()} rows` : ""}
          </p>
        </div>
        {active && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
      </button>
    );
  }

  const selectedCondition = CONDITIONS.find(o => o.value === conditionType) ?? CONDITIONS[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-2 sm:p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-[640px] shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            {([1, 2, 3] as const).map(s => (
              <div key={s} className="flex items-center gap-1.5">
                <div className={cn("h-2 w-2 rounded-full transition-colors",
                  s < step ? "bg-green-500" : s === step ? "bg-primary" : "bg-border")} />
                {s < 3 && <div className="h-px w-4 bg-border" />}
              </div>
            ))}
            <span className="text-xs text-muted-foreground ml-1">
              {step === 1 ? "Choose data" : step === 2 ? (query ? "Set parameters" : "Map columns") : "Condition & preview"}
            </span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {/* ── Step 1 ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-base text-foreground">What data should this alert watch?</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Any table or dataset NousViz can read: Postgres, ClickHouse or MySQL.
                </p>
              </div>
              {!sources && <p className="text-sm text-muted-foreground py-6 text-center">Loading sources…</p>}

              {queries.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
                    <Sparkles className="w-3 h-3" /> Ready-made alerts
                  </p>
                  <div className="space-y-1">
                    {queries.map(q => {
                      const active = query?.id === q.id;
                      const off = q.available === false;
                      return (
                        <button key={q.id} type="button" onClick={() => pickQuery(q)} disabled={off}
                          className={cn(
                            "w-full flex items-start gap-3 px-3 py-2.5 rounded-lg border text-left transition-all",
                            off ? "border-border opacity-50 cursor-not-allowed"
                              : active ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                : "border-border hover:border-primary/30 hover:bg-secondary/30",
                          )}>
                          <Sparkles className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm text-foreground truncate">{q.label}</p>
                              <EngineBadge engine={q.engine} />
                            </div>
                            <p className="text-[11px] text-muted-foreground">
                              {off ? q.unavailable_reason : q.description || q.plugin_id}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {Object.entries(pluginGroups).map(([group, items]) => (
                <div key={group}>
                  <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
                    <Plug className="w-3 h-3" /> {group}
                  </p>
                  <div className="space-y-1">{items.map(s => sourceButton(s, Plug))}</div>
                </div>
              ))}

              {connSources.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
                    <Link2 className="w-3 h-3" /> Connections
                  </p>
                  <div className="space-y-1">{connSources.map(s => sourceButton(s, Link2))}</div>
                  {source?.needs_table && (
                    <div className="mt-2">
                      <label className={labelCls}>Table on {source.label}</label>
                      {tables === null ? <p className="text-xs text-muted-foreground">Loading tables…</p> : (
                        <select value={table} onChange={e => setTable(e.target.value)} className={inputCls}>
                          <option value="">Choose a table…</option>
                          {tables.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      )}
                      {colsError && <p className="text-xs text-danger-foreground mt-1">{colsError}</p>}
                    </div>
                  )}
                </div>
              )}

              {coreSources.length > 0 && (
                <div>
                  <button type="button" onClick={() => setShowCore(v => !v)}
                    className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-1.5">
                    <Database className="w-3 h-3" /> Core tables ({coreSources.length})
                    <ChevronRight className={cn("w-3 h-3 transition-transform", showCore && "rotate-90")} />
                  </button>
                  {showCore && <div className="space-y-1">{coreSources.map(s => sourceButton(s, Database))}</div>}
                </div>
              )}
            </div>
          )}

          {/* ── Step 2: ready-made parameters ── */}
          {step === 2 && query && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-base text-foreground">{query.label}</h2>
                <p className="text-xs text-muted-foreground mt-1">{query.description}</p>
              </div>
              {Object.keys(query.params || {}).length === 0 && (
                <p className="text-sm text-muted-foreground">This alert has no parameters.</p>
              )}
              {Object.entries(query.params || {}).map(([k, p]) => (
                <div key={k}>
                  <label className={labelCls}>{p.label || k}</label>
                  {p.type === "enum" ? (
                    <select value={queryParams[k] ?? ""} onChange={e => setQueryParams(v => ({ ...v, [k]: e.target.value }))} className={inputCls}>
                      {(p.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input type={p.type === "number" ? "number" : "text"} value={queryParams[k] ?? ""}
                      onChange={e => setQueryParams(v => ({ ...v, [k]: e.target.value }))} className={inputCls} />
                  )}
                </div>
              ))}
              {query.sql && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground">The plugin's query (read-only)</summary>
                  <pre className="mt-2 p-3 rounded-md bg-secondary/40 overflow-x-auto font-mono-deck text-[11px] whitespace-pre-wrap">{query.sql}</pre>
                </details>
              )}
            </div>
          )}

          {/* ── Step 2: column mapping ── */}
          {step === 2 && source && !query && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground bg-secondary/40 rounded-lg px-3 py-2">
                <span className="truncate">{source.label}{table ? ` · ${table}` : ""}</span>
                <EngineBadge engine={cols?.engine ?? source.engine} />
                {cols?.table_engine?.includes("ReplacingMergeTree") && (
                  <span className="text-[10px] text-muted-foreground">read with FINAL</span>
                )}
              </div>
              {colsError && (
                <div className="flex items-start gap-2 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-3 py-2.5 text-xs text-warning-foreground">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {colsError}
                </div>
              )}
              {!cols && !colsError && <p className="text-sm text-muted-foreground py-6 text-center">Reading columns…</p>}

              {cols && (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className={labelCls}>Date column</label>
                      <select value={dateColumn} onChange={e => setDateColumn(e.target.value)} className={inputCls}>
                        <option value="">Choose…</option>
                        {dateCols.map(c => <option key={c.name} value={c.name}>{c.name} ({c.type})</option>)}
                      </select>
                      {dateCols.length === 0 && <p className="text-[10px] text-danger-foreground mt-1">This table has no date column, so it can't be alerted on by period.</p>}
                    </div>
                    <div>
                      <label className={labelCls}>Value</label>
                      <div className="flex gap-1">
                        {(["column", "count", "ratio"] as const).map(k => (
                          <button key={k} type="button" onClick={() => setValueKind(k)}
                            className={cn("flex-1 h-9 rounded-md border text-xs transition-all",
                              valueKind === k ? "border-primary bg-primary/5 text-foreground" : "border-border text-muted-foreground hover:border-primary/30")}>
                            {k === "column" ? "A column" : k === "count" ? "Row count" : "A ratio"}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {valueKind === "column" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className={labelCls}>Column</label>
                        <select value={metric} onChange={e => setMetric(e.target.value)} className={inputCls}>
                          <option value="">Choose…</option>
                          {(aggregation === "count_distinct" ? groupCols : numberCols).map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className={labelCls}>Aggregation</label>
                        <select value={aggregation} onChange={e => setAggregation(e.target.value)} className={inputCls}>
                          {AGGREGATIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                        </select>
                      </div>
                    </div>
                  )}
                  {valueKind === "ratio" && (
                    <div>
                      <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-end">
                        <div>
                          <label className={labelCls}>Sum of</label>
                          <select value={metric} onChange={e => setMetric(e.target.value)} className={inputCls}>
                            <option value="">Choose…</option>
                            {numberCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                        </div>
                        <span className="pb-2 text-muted-foreground">÷</span>
                        <div>
                          <label className={labelCls}>Sum of</label>
                          <select value={denominator} onChange={e => setDenominator(e.target.value)} className={inputCls}>
                            <option value="">Choose…</option>
                            {numberCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                        </div>
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-1">Computed from totals (a ratio of sums), never an average of ratios.</p>
                    </div>
                  )}

                  <div>
                    <label className={labelCls}>Check each… (group by, up to 3)</label>
                    <div className="space-y-1.5">
                      {groupBy.map((g, i) => (
                        <div key={i} className="flex gap-2">
                          <select value={g} onChange={e => setGroupBy(v => v.map((x, j) => (j === i ? e.target.value : x)))} className={inputCls}>
                            <option value="">Choose…</option>
                            {groupCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                          <button type="button" onClick={() => setGroupBy(v => v.filter((_, j) => j !== i))}
                            className="h-9 w-9 shrink-0 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-danger-foreground flex items-center justify-center" aria-label="Remove">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      {groupBy.length < 3 && (
                        <button type="button" onClick={() => setGroupBy(v => [...v, ""])}
                          className="text-xs text-primary hover:underline flex items-center gap-1"><Plus className="w-3 h-3" /> Add a column</button>
                      )}
                      {groupBy.length === 0 && <p className="text-[10px] text-muted-foreground">No grouping: the alert checks the whole table as one total.</p>}
                    </div>
                  </div>

                  <div>
                    <label className={labelCls}>Only rows where…</label>
                    <div className="space-y-1.5">
                      {filters.map((f, i) => (
                        <div key={i} className="grid grid-cols-[1fr_auto_1fr_auto] gap-1.5">
                          <select value={f.column}
                            onChange={e => { const c = e.target.value; setFilters(v => v.map((x, j) => (j === i ? { ...x, column: c } : x))); loadSuggestions(c); }}
                            className={inputCls}>
                            <option value="">Column…</option>
                            {groupCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                          <select value={f.op} onChange={e => setFilters(v => v.map((x, j) => (j === i ? { ...x, op: e.target.value } : x)))}
                            className="h-9 px-2 rounded-md bg-background border border-border text-sm text-foreground">
                            {FILTER_OPS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                          {f.op === "empty" || f.op === "not_empty" ? <span /> : (
                            <>
                              <input list={`vals-${i}`} value={f.value}
                                placeholder={f.op === "in" || f.op === "not_in" ? "a, b, c" : "value"}
                                onChange={e => setFilters(v => v.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))}
                                className={inputCls} />
                              <datalist id={`vals-${i}`}>
                                {(suggestions[f.column] ?? []).map(s => <option key={s} value={s} />)}
                              </datalist>
                            </>
                          )}
                          <button type="button" onClick={() => setFilters(v => v.filter((_, j) => j !== i))}
                            className="h-9 w-9 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-danger-foreground flex items-center justify-center" aria-label="Remove">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      <button type="button" onClick={() => setFilters(v => [...v, { column: "", op: "eq", value: "" }])}
                        className="text-xs text-primary hover:underline flex items-center gap-1"><Plus className="w-3 h-3" /> Add a filter</button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className={labelCls}>Skip groups below (optional)</label>
                      <div className="flex gap-1.5">
                        <select value={minVolumeColumn} onChange={e => setMinVolumeColumn(e.target.value)} className={inputCls}>
                          <option value="">No minimum</option>
                          {numberCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                        </select>
                        {minVolumeColumn && (
                          <input type="number" value={minVolume} onChange={e => setMinVolume(e.target.value)} placeholder="100"
                            className="w-24 h-9 px-2 rounded-md bg-background border border-border text-sm text-foreground" />
                        )}
                      </div>
                    </div>
                    <div>
                      <label className={labelCls}>Currency column (optional)</label>
                      <select value={currencyColumn} onChange={e => setCurrencyColumn(e.target.value)} className={inputCls}>
                        <option value="">None</option>
                        {textCols.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                      </select>
                      <p className="text-[10px] text-muted-foreground mt-1">Each currency is checked on its own; money is never added across currencies.</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Step 3 ── */}
          {step === 3 && (
            <form id="alert-form" onSubmit={submit} className="space-y-4">
              <div>
                <label className={labelCls}>Alert name</label>
                <input autoFocus type="text" placeholder="e.g. Revenue drop by program" value={label}
                  onChange={e => setLabel(e.target.value)} className={inputCls} required />
              </div>

              <div>
                <label className={labelCls}>Fire when {query?.value_label || "the value"}…</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {CONDITIONS.map(o => (
                    <button key={o.value} type="button" onClick={() => setConditionType(o.value)}
                      className={cn("flex items-center justify-between px-3 py-2 rounded-lg border text-left text-sm transition-all",
                        conditionType === o.value ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground")}>
                      {o.label}
                      <span className="text-[10px] text-muted-foreground">{o.hint}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {conditionType !== "zero_check" && (
                  <div>
                    <label className={labelCls}>{selectedCondition.hint.includes("%") ? "Change (%)" : "Value"}</label>
                    <input type="number" step="any" value={threshold} onChange={e => setThreshold(e.target.value)} className={inputCls} />
                    {conditionType === "threshold_drop" && <p className="text-[10px] text-muted-foreground mt-1">Negative: −20 means a 20% drop.</p>}
                  </div>
                )}
                <div>
                  <label className={labelCls}>Period checked</label>
                  <select value={period} onChange={e => setPeriod(e.target.value)} className={inputCls}>
                    {PERIODS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Compared with</label>
                  <select value={compareTo} onChange={e => setCompareTo(e.target.value)} className={inputCls}>
                    {COMPARISONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className={labelCls}>Check how often?</label>
                <div className="flex gap-2">
                  {FREQUENCIES.map(o => (
                    <button key={o.value} type="button" onClick={() => setFrequency(o.value)}
                      className={cn("flex-1 h-9 rounded-lg border text-sm transition-all",
                        frequency === o.value ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30")}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className={labelCls}>Notify via</label>
                <div className="flex flex-wrap gap-2">
                  {[{ id: "email", label: "Email", disabled: smtpConfigured === false }, { id: "log", label: "Log only", disabled: false },
                    ...outboundWebhooks.map(w => ({ id: `webhook:${w.name}`, label: w.name, disabled: false }))].map(ch => (
                    <label key={ch.id} title={ch.disabled ? "Set up email in Settings → Email to use this channel" : undefined}
                      className={cn("flex items-center gap-1.5 h-9 px-3 rounded-lg border text-sm transition-all",
                        ch.disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
                        notifyChannels.includes(ch.id) ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30")}>
                      <input type="checkbox" disabled={ch.disabled} checked={notifyChannels.includes(ch.id)} className="sr-only"
                        onChange={e => setNotifyChannels(c => (e.target.checked ? [...c, ch.id] : c.filter(x => x !== ch.id)))} />
                      {ch.label}
                    </label>
                  ))}
                </div>
                {outboundWebhooks.length === 0 && (
                  <p className="text-[10px] text-muted-foreground mt-1">Install the Webhooks utility to send alerts to Slack or any URL.</p>
                )}
              </div>

              {/* Preview */}
              <div className="rounded-lg border border-border">
                <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                  <span className="text-xs font-medium text-foreground">Preview on live data</span>
                  <button type="button" onClick={runPreview} disabled={previewing}
                    className="h-7 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80 flex items-center gap-1.5 disabled:opacity-50">
                    <Play className="w-3 h-3" /> {previewing ? "Running…" : "Preview"}
                  </button>
                </div>
                <div className="px-3 py-2 text-xs">
                  {!preview && <p className="text-muted-foreground">Shows which groups would fire right now. Nothing is sent.</p>}
                  {preview?.status === "error" && <p className="text-danger-foreground">{preview.error}</p>}
                  {preview?.status === "no_data" && <p className="text-muted-foreground">No rows for this period and these filters.</p>}
                  {preview && preview.status === "ok" && (
                    <>
                      <p className="text-muted-foreground mb-2">
                        <span className={preview.fired ? "text-warning-foreground" : "text-success-foreground"}>
                          {preview.fired ? `Would fire for ${preview.fired_count} of ${preview.rows_checked}` : `Would not fire (${preview.rows_checked} checked)`}
                        </span>
                        {preview.period && ` · ${preview.period[0]} to ${preview.period[1]} (end excluded)`}
                        {` · ${ENGINE_LABEL[preview.engine] ?? preview.engine} · ${preview.elapsed_ms} ms`}
                      </p>
                      <div className="max-h-56 overflow-y-auto">
                        <table className="w-full text-[11px]">
                          <thead className="text-muted-foreground">
                            <tr><th className="text-left font-normal py-1">Group</th><th className="text-right font-normal">Now</th>
                              <th className="text-right font-normal">Compared</th><th className="text-right font-normal">Change</th></tr>
                          </thead>
                          <tbody>
                            {(preview.rows ?? []).slice(0, 50).map(r => (
                              <tr key={r.group} className={cn("border-t border-border/50", r.fired && "text-warning-foreground")}>
                                <td className="py-1 pr-2 truncate max-w-[220px]">{r.fired ? "● " : ""}{r.group}</td>
                                <td className="text-right font-mono-deck">{fmt(r.current_value)}</td>
                                <td className="text-right font-mono-deck">{fmt(r.baseline)}</td>
                                <td className="text-right font-mono-deck">{r.change_pct == null ? "–" : `${r.change_pct > 0 ? "+" : ""}${r.change_pct}%`}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                  {preview?.sql && (
                    <button type="button" onClick={() => setShowSql(v => !v)} className="mt-2 text-[10px] text-primary hover:underline">
                      {showSql ? "Hide SQL" : "Show SQL"}
                    </button>
                  )}
                  {showSql && preview?.sql && (
                    <pre className="mt-1 p-2 rounded bg-secondary/40 overflow-x-auto font-mono-deck text-[10px] whitespace-pre-wrap">{preview.sql}</pre>
                  )}
                </div>
              </div>

              {error && <p className="text-xs text-danger-foreground">{error}</p>}
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-border shrink-0">
          <button type="button" onClick={() => (step > 1 ? setStep(s => (s - 1) as 1 | 2 | 3) : onClose())}
            className="h-9 px-4 rounded-lg bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors">
            {step === 1 ? "Cancel" : "Back"}
          </button>
          {step < 3 ? (
            <button type="button" disabled={step === 1 ? !step1Ready : !mappingReady}
              onClick={() => { setError(null); setStep(s => (s + 1) as 2 | 3); }}
              className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
              Continue
            </button>
          ) : (
            <button type="submit" form="alert-form" disabled={saving || !label.trim()}
              className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
              {saving ? "Creating…" : "Create alert"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertBuilder;
