import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Bell, Plus, Zap, Trash2, ToggleLeft, ToggleRight, Play } from "lucide-react";
import { cn } from "@/lib/utils";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { AlertBuilder } from "@/components/alerts/AlertBuilder";
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
  period_label?: string;
  enabled: boolean;
  trigger_count: number;
  // P230
  db_engine?: string;
  source_kind?: string;
  query_id?: string;
  group_by_columns?: string[];
  last_run_at?: string | null;
  last_status?: string | null;
  last_error?: string | null;
}

interface TestResult {
  fired?: boolean;
  message?: string;
  error?: string;
  rows_checked?: number;
  elapsed_ms?: number;
  triggered_rows?: { group: string; current_value: number; change_pct?: number | null }[];
}

const ENGINE_LABEL: Record<string, string> = { postgres: "Postgres", clickhouse: "ClickHouse", mysql: "MySQL" };

function statusBadge(a: Alert) {
  if (!a.last_status) return null;
  const cls = a.last_status === "error" ? "bg-red-500/10 text-danger-foreground"
    : a.last_status === "fired" ? "bg-yellow-500/10 text-warning-foreground"
      : "bg-secondary text-muted-foreground";
  const text = a.last_status === "no_data" ? "no data" : a.last_status;
  return (
    <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-mono-deck", cls)}
      title={[a.last_run_at ? `Last run ${new Date(a.last_run_at).toLocaleString()}` : "", a.last_error ?? ""].filter(Boolean).join("\n")}>
      last run: {text}
    </span>
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
  // B331: deleting is permanent, so it is confirmed first.
  const [pendingDelete, setPendingDelete] = useState<Alert | null>(null);
  const [deleting, setDeleting] = useState(false);
  // B345: Test runs the scheduled evaluation without sending anything.
  const [testing, setTesting] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<string, TestResult>>({});

  async function testAlert(id: string) {
    setTesting(id);
    try {
      const res = await apiFetch(`/api/alerts/${id}/test`, { method: "POST" });
      const data: TestResult = res.ok ? await res.json() : { error: `Test failed (${res.status})` };
      setTests(t => ({ ...t, [id]: data }));
    } catch {
      setTests(t => ({ ...t, [id]: { error: "Test failed" } }));
    } finally {
      setTesting(null);
    }
  }

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

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteAlert(pendingDelete.id);
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  }

  return (
    <>
      <ConfirmDialog
        open={pendingDelete !== null}
        title={`Delete alert "${pendingDelete?.label ?? ""}"?`}
        message=<>This can't be undone: its settings are removed. To stop it for now, switch it off instead.</>
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
      {showCreate && canWriteAlerts && (
        <AlertBuilder<Alert>
          onClose={() => setShowCreate(false)}
          onCreate={a => setAlertsCache(prev => [...prev, a])}
          outboundWebhooks={outboundWebhooks}
        />
      )}

      <div className="max-w-[1400px] space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-sm text-muted-foreground font-body">
            Threshold and change alerts on any data source: Postgres, ClickHouse or MySQL.
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
                  alert.enabled ? "bg-blue-500/10 text-info-foreground" : "bg-secondary text-muted-foreground"
                )}>
                  <Bell className="w-4 h-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground font-display">{alert.label}</span>
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded font-mono-deck",
                      alert.enabled ? "bg-green-500/10 text-success-foreground" : "bg-secondary text-muted-foreground"
                    )}>
                      {alert.enabled ? "Active" : "Paused"}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    <span className="font-mono-deck">{ENGINE_LABEL[alert.db_engine ?? "postgres"] ?? alert.db_engine}</span>
                    {" · "}{alert.source_kind === "plugin_query" ? `ready-made: ${alert.query_id}` : alert.dataset}
                    {alert.source_kind !== "plugin_query" && <> · <span className="font-mono-deck">{alert.metric === "*" ? "row count" : alert.metric}</span></>}
                    {alert.group_by_columns && alert.group_by_columns.length > 0 && <> · by {alert.group_by_columns.join(", ")}</>}
                    {" · "}{alert.frequency_label || alert.check_frequency}
                    {alert.trigger_count > 0 && <span className="text-warning-foreground"> · fired {alert.trigger_count}×</span>}
                  </p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {statusBadge(alert)}
                    {alert.last_status === "error" && alert.last_error && (
                      <span className="text-[10px] text-danger-foreground truncate max-w-[520px]">{alert.last_error}</span>
                    )}
                    {tests[alert.id] && (
                      <span className={cn("text-[10px]", tests[alert.id].error ? "text-danger-foreground"
                        : tests[alert.id].fired ? "text-warning-foreground" : "text-success-foreground")}>
                        Test: {tests[alert.id].error ?? tests[alert.id].message}
                        {tests[alert.id].triggered_rows?.length
                          ? ` — ${tests[alert.id].triggered_rows!.slice(0, 3).map(r => r.group).join(", ")}` : ""}
                      </span>
                    )}
                  </div>
                </div>

                {canWriteAlerts && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => testAlert(alert.id)}
                      disabled={testing === alert.id}
                      title="Test now (nothing is sent)"
                      className="h-8 px-2 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs disabled:opacity-50"
                    >
                      <Play className="w-3 h-3" /> {testing === alert.id ? "Testing…" : "Test"}
                    </button>
                    <button
                      onClick={() => toggleAlert(alert.id, alert.enabled)}
                      title={alert.enabled ? "Pause" : "Enable"}
                      className="text-muted-foreground hover:text-foreground transition-colors p-1"
                    >
                      {alert.enabled
                        ? <ToggleRight className="w-5 h-5 text-info-foreground" />
                        : <ToggleLeft className="w-5 h-5" />}
                    </button>
                    <button
                      onClick={() => setPendingDelete(alert)}
                      title="Delete"
                      className="h-8 w-8 rounded-md hover:bg-red-500/10 hover:text-danger-foreground flex items-center justify-center text-muted-foreground transition-colors"
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
