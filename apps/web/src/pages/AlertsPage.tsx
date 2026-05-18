import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import {
  Bell, Plus, Zap, X, Trash2, ToggleLeft, ToggleRight,
  Database, Plug, Link2, AlertTriangle, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import { useCurrentUser } from "@/hooks/useCurrentUser";

// ── Types ─────────────────────────────────────────────────────────────

interface Alert {
  id: string;
  label: string;
  plugin_id: string;
  dataset: string;
  metric: string;
  condition_type: string;
  threshold?: number;
  compare_to: string;
  check_frequency: string;
  frequency_label?: string;
  enabled: boolean;
  trigger_count: number;
}

interface SourceColumn { name: string; type: string; }

interface DataSource {
  id: string;
  label: string;
  source_type: "postgres" | "plugin_postgres" | "plugin" | "connection";
  source_label: string;
  table: string;
  plugin_id?: string;
  row_estimate?: number;
  status?: string;
  last_sync?: string;
  last_error?: string;
  columns: SourceColumn[];
}

interface SourcesResponse {
  postgres: DataSource[];
  connections: DataSource[];
  plugins: DataSource[];
}

// ── Helpers ───────────────────────────────────────────────────────────

const NUMERIC_TYPES = new Set([
  "integer","bigint","smallint","numeric","decimal",
  "real","double precision","float","int4","int8","int2",
]);
function isNumeric(t: string) {
  return NUMERIC_TYPES.has(t.toLowerCase()) || t.toLowerCase().includes("int");
}

function sourceIcon(type: string) {
  if (type === "postgres")        return Database;
  if (type === "plugin_postgres") return Plug;
  if (type === "connection")      return Link2;
  return Plug;
}

function sourceBadgeClass(type: string) {
  if (type === "postgres")        return "bg-blue-500/10 text-blue-400";
  if (type === "plugin_postgres") return "bg-green-500/10 text-green-400";
  if (type === "connection")      return "bg-purple-500/10 text-purple-400";
  return "bg-green-500/10 text-green-400";
}

// ── Modal ─────────────────────────────────────────────────────────────

const CONDITION_OPTIONS = [
  { value: "threshold_drop",  label: "Drops by more than…",         hint: "% compared to baseline" },
  { value: "threshold_rise",  label: "Rises by more than…",         hint: "% compared to baseline" },
  { value: "absolute_below",  label: "Falls below a fixed value…",  hint: "absolute number" },
  { value: "absolute_above",  label: "Rises above a fixed value…",  hint: "absolute number" },
  { value: "zero_check",      label: "Drops to zero",               hint: "no threshold needed" },
];

const COMPARE_OPTIONS = [
  { value: "7d_avg",      label: "7-day average" },
  { value: "14d_avg",     label: "14-day average" },
  { value: "30d_avg",     label: "30-day average" },
  { value: "prev_period", label: "Previous period" },
];

const FREQUENCY_OPTIONS = [
  { value: "hourly", label: "Every hour" },
  { value: "daily",  label: "Once a day" },
];

function CreateAlertModal({ onClose, onCreate, outboundWebhooks }: {
  onClose: () => void;
  onCreate: (a: Alert) => void;
  outboundWebhooks: { id: string; name: string }[];
}) {
  const [step, setStep]                     = useState<1|2|3>(1);
  const [sources, setSources]               = useState<SourcesResponse | null>(null);
  const [selectedSource, setSelectedSource] = useState<DataSource | null>(null);
  const [metric, setMetric]                 = useState("");
  const [label, setLabel]                   = useState("");
  const [conditionType, setConditionType]   = useState("threshold_drop");
  const [threshold, setThreshold]           = useState("20");
  const [compareTo, setCompareTo]           = useState("7d_avg");
  const [frequency, setFrequency]           = useState("daily");
  const [notifyChannels, setNotifyChannels]  = useState<string[]>(["email"]);
  const [saving, setSaving]                 = useState(false);
  const [error, setError]                   = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/api/alerts/sources")
      .then(r => r.json())
      .then(setSources)
      .catch(() => setSources({ postgres: [], connections: [], plugins: [] }));
  }, []);

  // Tier 1: plugin-owned sources (declared datasets + plugin-tagged postgres tables)
  const pluginSources: DataSource[] = sources ? [
    ...sources.plugins,
    ...sources.postgres.filter(s => s.source_type === "plugin_postgres"),
  ] : [];
  // Group plugin sources by display name
  const pluginGroups = pluginSources.reduce<Record<string, DataSource[]>>((acc, s) => {
    (acc[s.source_label] ||= []).push(s);
    return acc;
  }, {});

  // Tier 2: registered connections
  const connSources: DataSource[] = sources?.connections ?? [];

  // Tier 3: core postgres tables (not owned by a plugin)
  const coreSources: DataSource[] = sources
    ? sources.postgres.filter(s => s.source_type !== "plugin_postgres")
    : [];

  const hasPluginOrConn = pluginSources.length > 0 || connSources.length > 0;
  const [showCoreTables, setShowCoreTables] = useState(false);

  const numericCols = selectedSource?.columns.filter(c => isNumeric(c.type)) ?? [];
  const allCols     = selectedSource?.columns ?? [];
  const selectedCondition = CONDITION_OPTIONS.find(o => o.value === conditionType)!;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim() || !selectedSource || !metric) return;
    setSaving(true); setError(null);
    try {
      const res = await apiFetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: label.trim().toLowerCase().replace(/\s+/g, "_"),
          label: label.trim(),
          plugin_id: selectedSource.plugin_id || "core",
          dataset: selectedSource.table,
          metric,
          condition_type: conditionType,
          threshold: conditionType !== "zero_check" ? parseFloat(threshold) : undefined,
          compare_to: compareTo,
          check_frequency: frequency,
          notify_channels: notifyChannels,
          enabled: true,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      onCreate(await res.json());
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create alert");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-2 sm:p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-[500px] shadow-2xl flex flex-col max-h-[88vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            {/* Step dots */}
            {([1,2,3] as const).map(s => (
              <div key={s} className="flex items-center gap-1.5">
                <div className={cn(
                  "h-2 w-2 rounded-full transition-colors",
                  s < step ? "bg-green-500" : s === step ? "bg-primary" : "bg-border"
                )} />
                {s < 3 && <div className="h-px w-4 bg-border" />}
              </div>
            ))}
            <span className="text-xs text-muted-foreground ml-1">
              {step === 1 ? "Choose data" : step === 2 ? "Pick column" : "Set condition"}
            </span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">

          {/* ── Step 1: data source ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-base text-foreground">What data should this alert watch?</h2>
                <p className="text-xs text-muted-foreground mt-1">Select a table or dataset from your connected sources.</p>
              </div>

              {!sources && (
                <p className="text-sm text-muted-foreground py-6 text-center">Loading sources…</p>
              )}

              {sources && coreSources.length === 0 && pluginSources.length === 0 && connSources.length === 0 && (
                <div className="py-8 text-center">
                  <Database className="w-8 h-8 mx-auto mb-2 opacity-20 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">No data sources found.</p>
                  <p className="text-xs text-muted-foreground mt-1">Run migrations or install a plugin to add data.</p>
                </div>
              )}

              {/* ── Tier 1: Plugin datasets ── */}
              {Object.entries(pluginGroups).map(([groupLabel, items]) => (
                <div key={groupLabel}>
                  <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
                    <Plug className="w-3 h-3" /> {groupLabel}
                  </p>
                  <div className="space-y-1">
                    {items.map(s => {
                      const active = selectedSource?.id === s.id;
                      return (
                        <button key={s.id} type="button"
                          onClick={() => { setSelectedSource(s); setMetric(""); }}
                          className={cn(
                            "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all",
                            active ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                   : "border-border hover:border-primary/30 hover:bg-secondary/30"
                          )}
                        >
                          <div className={cn("h-8 w-8 rounded-md flex items-center justify-center shrink-0", sourceBadgeClass(s.source_type))}>
                            <Plug className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-foreground">{s.label}</p>
                            <p className="text-[11px] text-muted-foreground">
                              {s.columns.length > 0 ? `${s.columns.length} columns` : "schema unknown"}
                              {s.row_estimate ? ` · ~${s.row_estimate.toLocaleString()} rows` : ""}
                            </p>
                            {s.source_type === "plugin_postgres" && (
                              <p className="text-[10px] text-yellow-500/80 mt-0.5 flex items-center gap-1">
                                <AlertTriangle className="w-2.5 h-2.5 shrink-0" />
                                Removed if {s.plugin_id} is uninstalled
                              </p>
                            )}
                          </div>
                          {active && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}

              {/* ── Tier 2: Connections ── */}
              {connSources.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">
                    <Link2 className="w-3 h-3" /> Connections
                  </p>
                  <div className="space-y-1">
                    {connSources.map(s => {
                      const active = selectedSource?.id === s.id;
                      return (
                        <button key={s.id} type="button"
                          onClick={() => { setSelectedSource(s); setMetric(""); }}
                          className={cn(
                            "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all",
                            active ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                   : "border-border hover:border-primary/30 hover:bg-secondary/30"
                          )}
                        >
                          <div className="h-8 w-8 rounded-md flex items-center justify-center shrink-0 bg-purple-500/10 text-purple-400">
                            <Link2 className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-foreground">{s.label}</p>
                            <p className="text-[11px] text-muted-foreground">
                              {s.last_error ? "⚠ connection error" : s.status ?? ""}
                            </p>
                          </div>
                          {active && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── Tier 3: Core PostgreSQL tables ── */}
              {coreSources.length > 0 && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowCoreTables(v => !v)}
                    className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors mb-1.5"
                  >
                    <Database className="w-3 h-3" />
                    {hasPluginOrConn ? `Core tables (${coreSources.length})` : `PostgreSQL (${coreSources.length})`}
                    <ChevronRight className={cn("w-3 h-3 transition-transform", showCoreTables && "rotate-90")} />
                  </button>
                  {(!hasPluginOrConn || showCoreTables) && (
                    <div className="space-y-1">
                      {coreSources.map(s => {
                        const active = selectedSource?.id === s.id;
                        return (
                          <button key={s.id} type="button"
                            onClick={() => { setSelectedSource(s); setMetric(""); }}
                            className={cn(
                              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all",
                              active ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                     : "border-border hover:border-primary/30 hover:bg-secondary/30"
                            )}
                          >
                            <div className="h-8 w-8 rounded-md flex items-center justify-center shrink-0 bg-blue-500/10 text-blue-400">
                              <Database className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-foreground">{s.label}</p>
                              <p className="text-[11px] text-muted-foreground">
                                {s.columns.length > 0 ? `${s.columns.length} columns` : "schema unknown"}
                                {s.row_estimate ? ` · ~${s.row_estimate.toLocaleString()} rows` : ""}
                              </p>
                            </div>
                            {active && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Step 2: column ── */}
          {step === 2 && selectedSource && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-base text-foreground">Which value should we monitor?</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Pick a numeric column from <span className="text-foreground">{selectedSource.label}</span>.
                  {numericCols.length > 0 && numericCols.length < allCols.length && " Non-numeric columns are greyed out."}
                </p>
              </div>

              {selectedSource.last_error && (
                <div className="flex items-start gap-2 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-3 py-2.5 text-xs text-yellow-400">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  {selectedSource.last_error}
                </div>
              )}

              {allCols.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  Column schema not available for this source. Type a column name manually below.
                </p>
              ) : (
                <div className="space-y-1">
                  {allCols.map(c => {
                    const numeric = isNumeric(c.type);
                    const active  = metric === c.name;
                    return (
                      <button
                        key={c.name}
                        type="button"
                        onClick={() => numeric && setMetric(c.name)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 rounded-lg border text-left transition-all",
                          active
                            ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                            : numeric
                              ? "border-border hover:border-primary/30 hover:bg-secondary/30"
                              : "border-border opacity-35 cursor-not-allowed"
                        )}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-sm text-foreground truncate">{c.name}</span>
                          <span className="text-[10px] font-mono-deck text-muted-foreground shrink-0">{c.type}</span>
                        </div>
                        {active && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Manual fallback if schema unknown */}
              {allCols.length === 0 && (
                <input
                  type="text"
                  placeholder="Column name, e.g. revenue"
                  value={metric}
                  onChange={e => setMetric(e.target.value)}
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              )}
            </div>
          )}

          {/* ── Step 3: rule config ── */}
          {step === 3 && selectedSource && (
            <form id="alert-form" onSubmit={submit} className="space-y-4">
              {/* Breadcrumb */}
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-secondary/40 rounded-lg px-3 py-2">
                {(() => { const Icon = sourceIcon(selectedSource.source_type); return <Icon className="w-3.5 h-3.5 shrink-0" />; })()}
                <span>{selectedSource.label}</span>
                <ChevronRight className="w-3 h-3 opacity-50" />
                <span className="font-mono-deck text-foreground">{metric}</span>
              </div>

              <div>
                <h2 className="font-display text-base text-foreground">When should this fire?</h2>
                <p className="text-xs text-muted-foreground mt-1">Name the alert and define its trigger condition.</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Alert name</label>
                <input
                  autoFocus
                  type="text"
                  placeholder="e.g. Revenue drop"
                  value={label}
                  onChange={e => setLabel(e.target.value)}
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Fire when the value…</label>
                <div className="space-y-1.5">
                  {CONDITION_OPTIONS.map(o => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setConditionType(o.value)}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-left text-sm transition-all",
                        conditionType === o.value
                          ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground hover:bg-secondary/30"
                      )}
                    >
                      {o.label}
                      <span className="text-[10px] text-muted-foreground">{o.hint}</span>
                    </button>
                  ))}
                </div>
              </div>

              {conditionType !== "zero_check" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                      {selectedCondition.hint.includes("%") ? "Threshold (%)" : "Threshold (value)"}
                    </label>
                    <input
                      type="number"
                      value={threshold}
                      onChange={e => setThreshold(e.target.value)}
                      className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1.5">Compare against</label>
                    <select
                      value={compareTo}
                      onChange={e => setCompareTo(e.target.value)}
                      className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      {COMPARE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Check how often?</label>
                <div className="flex gap-2">
                  {FREQUENCY_OPTIONS.map(o => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setFrequency(o.value)}
                      className={cn(
                        "flex-1 h-9 rounded-lg border text-sm transition-all",
                        frequency === o.value
                          ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30 hover:bg-secondary/30"
                      )}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Notify via</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: "email", label: "Email" },
                    { id: "log", label: "Log only" },
                  ].map(ch => (
                    <label key={ch.id} className={cn(
                      "flex items-center gap-1.5 h-9 px-3 rounded-lg border text-sm cursor-pointer transition-all",
                      notifyChannels.includes(ch.id)
                        ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                        : "border-border text-muted-foreground hover:border-primary/30"
                    )}>
                      <input
                        type="checkbox"
                        checked={notifyChannels.includes(ch.id)}
                        onChange={e => {
                          if (e.target.checked) setNotifyChannels(c => [...c, ch.id]);
                          else setNotifyChannels(c => c.filter(x => x !== ch.id));
                        }}
                        className="sr-only"
                      />
                      {ch.label}
                    </label>
                  ))}
                  {outboundWebhooks.map(wh => {
                    const chId = `webhook:${wh.name}`;
                    return (
                      <label key={chId} className={cn(
                        "flex items-center gap-1.5 h-9 px-3 rounded-lg border text-sm cursor-pointer transition-all",
                        notifyChannels.includes(chId)
                          ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30"
                      )}>
                        <input
                          type="checkbox"
                          checked={notifyChannels.includes(chId)}
                          onChange={e => {
                            if (e.target.checked) setNotifyChannels(c => [...c, chId]);
                            else setNotifyChannels(c => c.filter(x => x !== chId));
                          }}
                          className="sr-only"
                        />
                        {wh.name}
                      </label>
                    );
                  })}
                </div>
                {outboundWebhooks.length === 0 && (
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Install the Webhooks plugin to add outbound webhook destinations.
                  </p>
                )}
              </div>

              {error && <p className="text-xs text-red-400">{error}</p>}
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-border shrink-0">
          <button
            type="button"
            onClick={() => step > 1 ? setStep(s => (s - 1) as 1|2|3) : onClose()}
            className="h-9 px-4 rounded-lg bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors"
          >
            {step === 1 ? "Cancel" : "Back"}
          </button>

          {step < 3 ? (
            <button
              type="button"
              disabled={step === 1 ? !selectedSource : !metric}
              onClick={() => setStep(s => (s + 1) as 2|3)}
              className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          ) : (
            <button
              type="submit"
              form="alert-form"
              disabled={saving || !label.trim() || !selectedSource || !metric}
              className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? "Creating…" : "Create alert"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────

// v0.10.0.7.3 (Phase 14 / P14.1): exported cache keys so other pages
// (and the sidebar) can prefetch + invalidate without re-deriving the
// identity.
export const ALERTS_LIST_QUERY_KEY = ["alerts", "list"] as const;
export const OUTBOUND_WEBHOOKS_QUERY_KEY = ["plugins", "webhooks", "endpoints", "outbound"] as const;

export default function AlertsPage() {
  useMarkBootReadyOnMount();
  // B305 (v0.10.0.6): viewers can read alerts but the backend 403s
  // writes. Hide the write-action buttons so the UI matches reality.
  const { hasPermission } = useCurrentUser();
  const canWriteAlerts = hasPermission("alerts.write");
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [pluginFilter, setPluginFilter] = useState<string>("all");

  // v0.10.0.7.3 — three fetches via the shared cache. The /api/plugins
  // call hits the SAME key PluginsPage uses, so an operator who already
  // visited Plugins gets this for free.
  const { data: alertsData, isLoading } = useApiQuery<{ alerts: Alert[] }>(
    ALERTS_LIST_QUERY_KEY,
    "/api/alerts",
  );
  const { data: pluginsData } = useApiQuery<{ plugins: { id: string; name?: string; display_name?: string }[] }>(
    ["plugins", "list"],     // shared with PluginsPage
    "/api/plugins",
  );
  const { data: webhooksData } = useApiQuery<{ endpoints: { id: string; name: string }[] }>(
    OUTBOUND_WEBHOOKS_QUERY_KEY,
    "/api/plugins/webhooks/endpoints?direction=outbound",
  );

  const alerts: Alert[] = alertsData?.alerts ?? [];
  const loading = isLoading;
  const installedPlugins = (pluginsData?.plugins ?? []).map((p) => ({
    id: p.id,
    name: p.display_name || p.name || p.id,
  }));
  const outboundWebhooks = (webhooksData?.endpoints ?? []).map((e) => ({ id: e.id, name: e.name }));

  // Optimistic-update helper: keep the UI snappy by writing the expected
  // new state into the cache immediately, then refetch in the background
  // so the server's source-of-truth lands a tick later.
  const setAlertsCache = (updater: (prev: Alert[]) => Alert[]) => {
    queryClient.setQueryData(ALERTS_LIST_QUERY_KEY, (prev: { alerts?: Alert[] } | undefined) => ({
      ...(prev ?? {}),
      alerts: updater(prev?.alerts ?? []),
    }));
  };

  async function toggleAlert(id: string, enabled: boolean) {
    setAlertsCache(prev => prev.map(a => a.id === id ? { ...a, enabled: !enabled } : a));
    await apiFetch(`/api/alerts/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !enabled }),
    });
    queryClient.invalidateQueries({ queryKey: ALERTS_LIST_QUERY_KEY });
  }

  async function deleteAlert(id: string) {
    setAlertsCache(prev => prev.filter(a => a.id !== id));
    await apiFetch(`/api/alerts/${id}`, { method: "DELETE" });
    queryClient.invalidateQueries({ queryKey: ALERTS_LIST_QUERY_KEY });
  }

  return (
    <>
      {showCreate && canWriteAlerts && (
        <CreateAlertModal
          onClose={() => setShowCreate(false)}
          onCreate={a => setAlertsCache(prev => [...prev, a])}
          outboundWebhooks={outboundWebhooks}
        />
      )}

      <div className="max-w-[1400px] space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-sm text-muted-foreground font-body">
            Threshold and anomaly alerts on any data source.
          </p>
          {canWriteAlerts && (
            <button
              onClick={() => setShowCreate(true)}
              className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> New Alert
            </button>
          )}
        </div>

        {/* Plugin filter pills */}
        {installedPlugins.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => setPluginFilter("all")}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-body transition-colors",
                pluginFilter === "all" ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
              )}
            >
              All
            </button>
            <button
              onClick={() => setPluginFilter("core")}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-body transition-colors",
                pluginFilter === "core" ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
              )}
            >
              Core
            </button>
            {installedPlugins.map(p => (
              <button
                key={p.id}
                onClick={() => setPluginFilter(p.id)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-body transition-colors",
                  pluginFilter === p.id ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
                )}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-md bg-card border border-border animate-pulse">
                <div className="h-8 w-8 rounded-md bg-secondary shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 w-40 bg-secondary rounded" />
                  <div className="h-2.5 w-64 bg-secondary/60 rounded" />
                </div>
                <div className="h-5 w-16 rounded-full bg-secondary shrink-0" />
              </div>
            ))}
          </div>
        )}

        {!loading && alerts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="h-16 w-16 rounded-2xl bg-secondary flex items-center justify-center mb-4">
              <Zap className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-display text-lg text-foreground mb-2">No alerts yet</h3>
            <p className="text-sm text-muted-foreground font-body max-w-sm mb-6">
              {canWriteAlerts
                ? "Create an alert on any connected data source. Get notified when a value drops, spikes, or hits zero."
                : "No alerts are configured yet. Ask an analyst or admin to create one."}
            </p>
            {canWriteAlerts && (
              <button
                onClick={() => setShowCreate(true)}
                className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
              >
                <Plus className="w-4 h-4" /> Create Alert
              </button>
            )}
          </div>
        )}

        {!loading && alerts.length > 0 && (
          <div className="space-y-2">
            {alerts.filter(alert => {
              if (pluginFilter === "all") return true;
              if (pluginFilter === "core") return !alert.plugin_id;
              return alert.plugin_id === pluginFilter;
            }).map(alert => (
              <div key={alert.id} className="bg-card rounded-lg border border-border px-4 py-3 flex items-center gap-4">
                <div className={cn(
                  "h-8 w-8 rounded-lg flex items-center justify-center shrink-0",
                  alert.enabled ? "bg-blue-500/10 text-blue-400" : "bg-secondary text-muted-foreground"
                )}>
                  <Bell className="w-4 h-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground font-display">{alert.label}</span>
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded font-mono-deck",
                      alert.enabled ? "bg-green-500/10 text-green-400" : "bg-secondary text-muted-foreground"
                    )}>
                      {alert.enabled ? "Active" : "Paused"}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {alert.dataset} · <span className="font-mono-deck">{alert.metric}</span> · {alert.frequency_label || alert.check_frequency}
                    {alert.trigger_count > 0 && <span className="text-yellow-400"> · fired {alert.trigger_count}×</span>}
                  </p>
                </div>

                {canWriteAlerts && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => toggleAlert(alert.id, alert.enabled)}
                      title={alert.enabled ? "Pause" : "Enable"}
                      className="text-muted-foreground hover:text-foreground transition-colors p-1"
                    >
                      {alert.enabled
                        ? <ToggleRight className="w-5 h-5 text-blue-400" />
                        : <ToggleLeft className="w-5 h-5" />}
                    </button>
                    <button
                      onClick={() => deleteAlert(alert.id)}
                      title="Delete"
                      className="h-8 w-8 rounded-md hover:bg-red-500/10 hover:text-red-400 flex items-center justify-center text-muted-foreground transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
