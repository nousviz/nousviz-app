import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Zap,
  AlertTriangle,
  Play,
  Trash2,
  X,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import {
  listAlerts,
  createAlert,
  updateAlert,
  deleteAlert,
  testAlert,
  getAlertSparkline,
  type Alert,
  type AlertCreate,
  type SparklineDay,
} from "@/lib/alerts";

// ── Alert Sparkline ──────────────────────────────────────────────────

const SCORE_COLOR: Record<string, string> = {
  useful:  "bg-green-500",
  neutral: "bg-yellow-500",
  useless: "bg-red-500",
};

function AlertSparklineBar({ alertId }: { alertId: string }) {
  const [data, setData] = useState<{ days: SparklineDay[]; total: number } | null>(null);

  useEffect(() => {
    getAlertSparkline(alertId, 30)
      .then((s) => setData({ days: s.days, total: s.total_triggers }))
      .catch(() => {});
  }, [alertId]);

  if (!data || data.total === 0) return null;

  const max = Math.max(...data.days.map((d) => d.count), 1);

  return (
    <div className="mt-2 flex items-end gap-px h-5" title="Last 30 days trigger activity">
      {data.days.map((day) => (
        <div
          key={day.date}
          className="flex-1"
          style={{ height: day.count > 0 ? `${Math.max(20, (day.count / max) * 100)}%` : "20%" }}
          title={`${day.date}: ${day.count} trigger${day.count !== 1 ? "s" : ""}${day.score ? ` · ${day.score}` : ""}`}
        >
          <div className={cn(
            "w-full h-full rounded-sm",
            day.count === 0
              ? "bg-secondary/40"
              : day.score
              ? SCORE_COLOR[day.score]
              : "bg-primary/60"
          )} />
        </div>
      ))}
    </div>
  );
}

const FREQ_LABEL: Record<string, string> = {
  hourly: "hourly",
  daily:  "daily",
  weekly: "weekly",
};

const PERIOD_LABEL: Record<string, string> = {
  today:              "today",
  yesterday:          "yesterday",
  today_or_yesterday: "today or yesterday",
  this_week:          "this week",
  rolling_7d:         "last 7 days",
};

// ── Fetch table columns from the database ───────────────────────────

interface ColumnInfo {
  name: string;
  data_type: string;
}

const NUMERIC_TYPES = new Set([
  "integer", "bigint", "smallint", "numeric", "real", "double precision",
  "decimal", "int", "int4", "int8", "float4", "float8", "serial", "bigserial",
]);

function useTableColumns(table: string | null) {
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!table) { setColumns([]); setError(null); return; }
    setLoading(true);
    setError(null);
    apiFetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sql: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${table}' ORDER BY ordinal_position`,
        db_engine: "postgres",
      }),
    })
      .then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then(d => {
        const rows: ColumnInfo[] = (d.rows ?? []).map((r: any) => ({
          name: r.column_name,
          data_type: r.data_type,
        }));
        setColumns(rows);
      })
      .catch((e) => { setColumns([]); setError(e.message || "Failed to load columns"); })
      .finally(() => setLoading(false));
  }, [table]);

  const numericColumns = columns.filter(c => NUMERIC_TYPES.has(c.data_type));
  const textColumns = columns.filter(c => !NUMERIC_TYPES.has(c.data_type));

  return { columns, numericColumns, textColumns, loading, error };
}

// ── Custom Alert Builder ─────────────────────────────────────────────

function AlertBuilder({
  pluginId,
  tables,
  onCreated,
  onCancel,
}: {
  pluginId: string;
  tables: string[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const firstTable = tables[0] ?? "";

  const [form, setForm] = useState<AlertCreate>({
    name: "",
    label: "",
    description: "",
    plugin_id: pluginId,
    dataset: firstTable,
    metric: "",
    aggregation: "sum",
    condition_type: "threshold_drop",
    threshold: -20,
    compare_to: "7d_avg",
    scope: "all",
    group_by: undefined,
    min_baseline: 0,
    cooldown_hours: 24,
    notify_channels: ["email"],
    enabled: true,
  });
  const [saving, setSaving] = useState(false);

  const { numericColumns, textColumns, loading: columnsLoading, error: columnsError } = useTableColumns(form.dataset || null);

  // Set default metric when columns load
  useEffect(() => {
    if (numericColumns.length > 0 && !numericColumns.find(c => c.name === form.metric)) {
      setForm(f => ({ ...f, metric: numericColumns[0].name }));
    }
  }, [numericColumns]);

  // Set default group_by when columns load and scope is per_group
  useEffect(() => {
    if (form.scope === "per_group" && textColumns.length > 0 && !textColumns.find(c => c.name === form.group_by)) {
      setForm(f => ({ ...f, group_by: textColumns[0].name }));
    }
  }, [textColumns, form.scope]);

  const handleSubmit = async () => {
    if (!form.label) return;
    setSaving(true);
    try {
      await createAlert({
        ...form,
        name: form.label.toLowerCase().replace(/\s+/g, "_"),
      });
      onCreated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-card rounded-lg border border-primary/20 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm text-foreground flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" /> Custom Alert Builder
        </h3>
        <button onClick={onCancel} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
      </div>

      {/* Name */}
      <input
        type="text"
        value={form.label}
        onChange={(e) => setForm({ ...form, label: e.target.value })}
        placeholder="Alert name"
        className="w-full h-10 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
      />

      <textarea
        value={form.description || ""}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
        placeholder="Description (optional)"
        rows={2}
        className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body resize-none"
      />

      {/* What to monitor */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Dataset</label>
          <select
            value={form.dataset}
            onChange={(e) => setForm({ ...form, dataset: e.target.value, metric: "" })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground"
          >
            {tables.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Metric</label>
          <select
            value={form.metric}
            onChange={(e) => setForm({ ...form, metric: e.target.value })}
            disabled={columnsLoading}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground disabled:opacity-50"
          >
            {columnsLoading && <option>Loading…</option>}
            {numericColumns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
            {!columnsLoading && numericColumns.length === 0 && <option>No numeric columns</option>}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Aggregation</label>
          <select value={form.aggregation} onChange={(e) => setForm({ ...form, aggregation: e.target.value })} className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground">
            {["sum", "avg", "count", "min", "max"].map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Compare to</label>
          <select value={form.compare_to} onChange={(e) => setForm({ ...form, compare_to: e.target.value })} className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground">
            <option value="7d_avg">7-day average</option>
            <option value="14d_avg">14-day average</option>
            <option value="30d_avg">30-day average</option>
          </select>
        </div>
      </div>

      {columnsError && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          Failed to load columns for <span className="font-mono-deck">{form.dataset}</span>: {columnsError}
        </div>
      )}

      {/* Condition */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Condition</label>
          <select value={form.condition_type} onChange={(e) => setForm({ ...form, condition_type: e.target.value })} className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground">
            <option value="threshold_drop">Drops by %</option>
            <option value="threshold_rise">Rises by %</option>
            <option value="absolute_below">Falls below value</option>
            <option value="absolute_above">Exceeds value</option>
            <option value="zero_check">Equals zero</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">
            {form.condition_type?.includes("threshold") ? "Threshold %" : "Value"}
          </label>
          <input
            type="number"
            value={form.threshold ?? ""}
            onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground"
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Scope</label>
          <select
            value={form.scope}
            onChange={(e) => setForm({ ...form, scope: e.target.value, group_by: e.target.value === "all" ? undefined : (textColumns[0]?.name || undefined) })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          >
            <option value="all">All combined</option>
            <option value="per_group">Per dimension</option>
          </select>
        </div>
        {form.scope === "per_group" && (
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Group by</label>
            <select
              value={form.group_by || ""}
              onChange={(e) => setForm({ ...form, group_by: e.target.value })}
              disabled={columnsLoading}
              className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground disabled:opacity-50"
            >
              {textColumns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
              {!columnsLoading && textColumns.length === 0 && <option>No text columns</option>}
            </select>
          </div>
        )}
      </div>

      {/* Advanced */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Min baseline</label>
          <input
            type="number"
            value={form.min_baseline ?? 0}
            onChange={(e) => setForm({ ...form, min_baseline: Number(e.target.value) })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground"
          />
          <p className="text-[10px] text-muted-foreground mt-0.5">Ignore if avg below this</p>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Cooldown (hours)</label>
          <input
            type="number"
            value={form.cooldown_hours ?? 24}
            onChange={(e) => setForm({ ...form, cooldown_hours: Number(e.target.value) })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground"
          />
          <p className="text-[10px] text-muted-foreground mt-0.5">Don't re-alert within</p>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Check frequency</label>
          <select value={form.check_frequency} onChange={(e) => setForm({ ...form, check_frequency: e.target.value })} className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground">
            <option value="daily">Daily</option>
            <option value="hourly">Hourly</option>
          </select>
        </div>
      </div>

      {/* Submit */}
      <div className="flex items-center justify-end gap-2 pt-2">
        <button onClick={onCancel} className="h-9 px-4 rounded-md text-sm text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
        <button
          onClick={handleSubmit}
          disabled={!form.label || !form.metric || saving}
          className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {saving ? "Creating..." : "Create Alert"}
        </button>
      </div>
    </div>
  );
}

// ── Main Plugin Alerts Page ──────────────────────────────────────────

export default function PluginAlerts({ pluginId, tables = [] }: { pluginId: string; tables?: string[] }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [, setLoading] = useState(true);
  const [showBuilder, setShowBuilder] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAlerts(pluginId);
      setAlerts(data);
    } catch {
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [pluginId]);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const enabledCount = alerts.filter((a) => a.enabled).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            {enabledCount} active alert{enabledCount !== 1 ? "s" : ""}
          </span>
        </div>
        {!showBuilder && tables.length > 0 && (
          <button
            onClick={() => setShowBuilder(true)}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Custom Alert
          </button>
        )}
      </div>

      {/* No tables — plugin has no datasets */}
      {tables.length === 0 && alerts.length === 0 && (
        <div className="py-12 text-center border border-dashed border-border rounded-lg">
          <AlertTriangle className="w-8 h-8 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">This plugin has no datasets to alert on.</p>
          <p className="text-xs text-muted-foreground mt-1">Plugins must declare database tables in their manifest to enable alerts.</p>
        </div>
      )}

      {/* Custom alert builder */}
      {showBuilder && (
        <AlertBuilder
          pluginId={pluginId}
          tables={tables}
          onCreated={() => { setShowBuilder(false); fetchAlerts(); }}
          onCancel={() => setShowBuilder(false)}
        />
      )}

      {/* Existing alerts */}
      {alerts.length > 0 && (
        <div>
          <h3 className="font-display text-sm text-muted-foreground mb-3 uppercase tracking-wider">
            Alerts
          </h3>
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className={cn(
                "bg-card rounded-lg border p-4",
                alert.enabled ? "border-green-500/20" : "border-border"
              )}>
                <div className="flex items-start gap-3">
                  <button
                    onClick={async () => { await updateAlert(alert.id, { enabled: !alert.enabled }); fetchAlerts(); }}
                    className={cn("mt-0.5 w-10 h-5 rounded-full transition-colors shrink-0 relative", alert.enabled ? "bg-green-500" : "bg-secondary")}
                  >
                    <div className={cn("w-4 h-4 rounded-full bg-white absolute top-0.5 transition-transform", alert.enabled ? "translate-x-5" : "translate-x-0.5")} />
                  </button>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-display text-sm text-foreground">{alert.label}</h3>
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Clock className="w-3 h-3" />{FREQ_LABEL[alert.check_frequency] ?? alert.frequency_label} · {PERIOD_LABEL[alert.check_period] ?? alert.period_label}
                      </span>
                      {alert.enabled && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400">
                          Active
                        </span>
                      )}
                    </div>
                    {alert.description && <p className="text-xs text-muted-foreground mt-0.5">{alert.description}</p>}
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-muted-foreground">
                      <span className="font-mono-deck">{alert.dataset}</span>
                      <span>{alert.aggregation}({alert.metric})</span>
                      <span>{alert.condition_type === "threshold_drop" ? "drops" : alert.condition_type === "threshold_rise" ? "rises" : alert.condition_type === "zero_check" ? "= zero" : ""} {alert.threshold != null && alert.condition_type !== "zero_check" ? `${alert.threshold}%` : ""}</span>
                      {alert.group_by && <span>per {alert.group_by}</span>}
                    </div>
                    <AlertSparklineBar alertId={alert.id} />
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={async () => {
                        const result = await testAlert(alert.id);
                        // Could show test result inline — for now just trigger
                        void result;
                      }}
                      className="h-7 px-2 rounded text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" /> Test
                    </button>
                    <button
                      onClick={async () => { await deleteAlert(alert.id); fetchAlerts(); }}
                      className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-red-400"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
