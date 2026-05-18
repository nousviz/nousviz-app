/**
 * /settings/maintenance — retention policies operator UI (B279, v0.9.11.17).
 *
 * Lists every retention policy from POLICIES (server-side registry) with
 * live state: current rows, rows that would be pruned next run, paused
 * flag, last-run outcome. Operator can edit the threshold (0-3650 days),
 * flip pause, or trigger an immediate run per policy. Run-all button
 * appears only when ≥1 policy is unpaused.
 *
 * Per operator decision 2026-05-04: every policy ships paused. The page
 * leads with a yellow banner reminding the operator to review previews
 * before unpausing.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  RefreshCw,
  AlertTriangle,
  Play,
  Pause,
  Check,
  Info,
  Database,
  Clock,
  XCircle,
  Bell,
  Plus,
  Send,
  Trash2,
} from "lucide-react";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { DataTable } from "@/components/ui/DataTable";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";

interface RetentionPolicyState {
  key: string;
  table: string;
  field: string;
  description: string;
  retention_days: number;
  paused: boolean;
  rows_total: number;
  rows_would_prune: number;
  last_run_at?: string | null;
  last_run_rows_deleted?: number | null;
  last_run_error?: string | null;
  updated_at?: string | null;
}

interface ListResponse {
  policies: RetentionPolicyState[];
  collected_at: string;
}

export default function MaintenancePanel() {
  const [policies, setPolicies] = useState<RetentionPolicyState[]>([]);
  const [collectedAt, setCollectedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);
  const [pendingDays, setPendingDays] = useState<Record<string, number>>({});
  const [confirmRun, setConfirmRun] = useState<RetentionPolicyState | null>(null);
  const [confirmRunAll, setConfirmRunAll] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const r = await apiFetch("/api/maintenance/retention");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as ListResponse;
      setPolicies(body.policies);
      setCollectedAt(body.collected_at);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const flashToast = (kind: "ok" | "err", msg: string) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5000);
  };

  // ── Actions ──────────────────────────────────────────────────────

  const updatePolicy = useCallback(
    async (key: string, body: { retention_days?: number; paused?: boolean }) => {
      const actionKey = `update-${key}`;
      setActionInFlight(actionKey);
      try {
        const r = await apiFetch(
          `/api/maintenance/retention/${encodeURIComponent(key)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flashToast("err", `Update failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        flashToast("ok", `Updated ${key}.`);
        await load();
      } catch (e) {
        flashToast("err", `Update error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
      }
    },
    [load],
  );

  const runPolicy = useCallback(
    async (key: string) => {
      const actionKey = `run-${key}`;
      setActionInFlight(actionKey);
      try {
        const r = await apiFetch(
          `/api/maintenance/retention/${encodeURIComponent(key)}/run`,
          { method: "POST" },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flashToast("err", `Run failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        const body = (await r.json()) as { rows_deleted: number; duration_ms: number };
        flashToast("ok", `${key} — deleted ${body.rows_deleted} rows in ${body.duration_ms}ms.`);
        await load();
      } catch (e) {
        flashToast("err", `Run error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
        setConfirmRun(null);
      }
    },
    [load],
  );

  const runAll = useCallback(async () => {
    const actionKey = "run-all";
    setActionInFlight(actionKey);
    try {
      const r = await apiFetch("/api/maintenance/retention/run-all", { method: "POST" });
      if (!r.ok) {
        const err = await r.json().catch(() => ({} as { detail?: string }));
        flashToast("err", `Run-all failed (${r.status}): ${err.detail ?? "unknown"}`);
        return;
      }
      const body = (await r.json()) as {
        summary: Record<string, number | string>;
        duration_ms: number;
      };
      const total = Object.values(body.summary)
        .filter((v): v is number => typeof v === "number")
        .reduce((a, b) => a + b, 0);
      flashToast(
        "ok",
        `Run-all done — ${total} total rows deleted across unpaused policies (${body.duration_ms}ms).`,
      );
      await load();
    } catch (e) {
      flashToast("err", `Run-all error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setActionInFlight(null);
      setConfirmRunAll(false);
    }
  }, [load]);

  // ── Derived ──────────────────────────────────────────────────────

  const unpausedCount = useMemo(
    () => policies.filter((p) => !p.paused).length,
    [policies],
  );

  if (loading) {
    return <div className="p-4 text-muted-foreground text-sm">Loading retention policies…</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-display text-foreground flex items-center gap-2">
            <Database className="w-4 h-4 text-muted-foreground" />
            Retention policies
          </h2>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {collectedAt ? (
              <>Snapshot {formatRelativeTime(collectedAt)} · {unpausedCount} of {policies.length} active</>
            ) : (
              "Daily cron prunes log/event/session tables per the policies below."
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unpausedCount > 0 && (
            <button
              onClick={() => setConfirmRunAll(true)}
              disabled={actionInFlight !== null}
              className="h-8 px-3 rounded-md text-xs font-medium border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 flex items-center gap-2 disabled:opacity-50"
              title="Run every UNPAUSED policy now"
            >
              <Play className="w-3.5 h-3.5" />
              Run all unpaused
            </button>
          )}
          <button
            onClick={load}
            disabled={refreshing}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Paused-by-default banner */}
      {policies.every((p) => p.paused) && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-4 py-3 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-foreground font-medium">All retention policies are paused.</p>
            <p className="text-xs text-muted-foreground mt-1">
              Retention ships paused by default. Review each policy's "Would prune" preview, then flip the
              ones you trust on. The daily cron at 04:00 UTC runs every UNPAUSED policy; paused policies
              are no-ops. Failed and high-risk policies (e.g. <code className="font-mono-deck">job_runs:success</code> 7-day default)
              should be the last enabled.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 flex items-center gap-2">
          <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="text-xs text-red-300">Failed to load policies: {error}</p>
        </div>
      )}

      {toast && (
        <div
          className={cn(
            "rounded-lg px-4 py-2 border",
            toast.kind === "ok"
              ? "bg-green-500/10 border-green-500/20 text-green-300"
              : "bg-red-500/10 border-red-500/20 text-red-300",
          )}
        >
          <p className="text-xs">{toast.msg}</p>
        </div>
      )}

      {/* Mobile (<sm): retention policies as stacked cards. B288.1
          (v0.9.11.26.1): replaces the squeezed table view so operators
          can see all the data and tap Run-now / Pause without
          horizontal scroll. */}
      <div className="block sm:hidden space-y-2">
        {policies.map((p) => {
          const updateKey = `update-${p.key}`;
          const runKey = `run-${p.key}`;
          const editing = pendingDays[p.key] !== undefined;
          const daysValue = editing ? pendingDays[p.key] : p.retention_days;
          return (
            <MobileCard
              key={`${p.key}-card`}
              title={
                <div>
                  <div className="font-mono-deck text-foreground text-sm break-words">{p.key}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{p.description}</div>
                </div>
              }
              badge={
                p.paused ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400">
                    <Pause className="w-2.5 h-2.5" />
                    paused
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400">
                    <Check className="w-2.5 h-2.5" />
                    active
                  </span>
                )
              }
              actions={
                <>
                  <button
                    onClick={() => updatePolicy(p.key, { paused: !p.paused })}
                    disabled={actionInFlight === updateKey}
                    className="flex-1 text-xs px-2 py-1.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center justify-center gap-1 disabled:opacity-50"
                  >
                    {p.paused ? (
                      <><Play className="w-3 h-3" /> Activate</>
                    ) : (
                      <><Pause className="w-3 h-3" /> Pause</>
                    )}
                  </button>
                  <button
                    onClick={() => setConfirmRun(p)}
                    disabled={actionInFlight === runKey}
                    className="flex-1 text-xs px-2 py-1.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 flex items-center justify-center gap-1 disabled:opacity-50"
                  >
                    <Play className="w-3 h-3" /> Run now
                  </button>
                </>
              }
            >
              <MobileCardRow label="Keep">
                <input
                  type="number"
                  min={0}
                  max={3650}
                  value={daysValue}
                  onChange={(e) => setPendingDays((prev) => ({ ...prev, [p.key]: Number(e.target.value) }))}
                  onBlur={() => {
                    if (!editing) return;
                    const v = pendingDays[p.key];
                    if (v !== p.retention_days && Number.isFinite(v)) {
                      updatePolicy(p.key, { retention_days: v });
                    }
                    setPendingDays((prev) => {
                      const next = { ...prev };
                      delete next[p.key];
                      return next;
                    });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                    if (e.key === "Escape") {
                      setPendingDays((prev) => {
                        const next = { ...prev };
                        delete next[p.key];
                        return next;
                      });
                    }
                  }}
                  className="w-16 bg-secondary/40 border border-border rounded px-1.5 py-0.5 text-right tabular-nums font-mono-deck text-foreground"
                />
                <span className="text-muted-foreground ml-1">d</span>
              </MobileCardRow>
              <MobileCardRow label="Rows" valueClassName="tabular-nums font-mono-deck text-muted-foreground">
                {p.rows_total.toLocaleString()}
              </MobileCardRow>
              <MobileCardRow
                label="Would prune"
                valueClassName={cn(
                  "tabular-nums font-mono-deck",
                  p.rows_would_prune > 0 ? "text-yellow-400" : "text-muted-foreground",
                )}
              >
                {p.rows_would_prune > 0 ? p.rows_would_prune.toLocaleString() : "—"}
              </MobileCardRow>
              <MobileCardRow label="Last run">
                {p.last_run_at ? (
                  <div title={formatAbsoluteTime(p.last_run_at)}>
                    <div className="text-foreground">{formatRelativeTime(p.last_run_at)}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {p.last_run_rows_deleted ?? 0} deleted
                    </div>
                  </div>
                ) : (
                  <span className="text-muted-foreground">never</span>
                )}
              </MobileCardRow>
              {p.last_run_error && (
                <div className="text-[10px] text-red-400 break-words" title={p.last_run_error}>
                  last error: {p.last_run_error}
                </div>
              )}
            </MobileCard>
          );
        })}
      </div>

      {/* Desktop (sm+): policies table */}
      <div className="hidden sm:block bg-card border border-border rounded-lg overflow-hidden">
        <DataTable minWidth="780px">
          <thead className="bg-secondary/30 border-b border-border">
            <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
              <th className="text-left font-semibold px-3 py-2 sticky left-0 bg-card z-10">Policy</th>
              <th className="text-right font-semibold px-3 py-2 w-20">Keep</th>
              <th className="text-right font-semibold px-3 py-2 w-24">Rows</th>
              <th className="text-right font-semibold px-3 py-2 w-32">Would prune</th>
              <th className="text-left font-semibold px-3 py-2 w-32">Last run</th>
              <th className="text-left font-semibold px-3 py-2 w-20">Status</th>
              <th className="text-right font-semibold px-3 py-2 w-44 sticky right-0 bg-card z-10">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {policies.map((p) => {
              const updateKey = `update-${p.key}`;
              const runKey = `run-${p.key}`;
              const editing = pendingDays[p.key] !== undefined;
              const daysValue = editing ? pendingDays[p.key] : p.retention_days;
              return (
                <tr key={p.key} className={cn(p.paused ? "" : "bg-blue-500/5")}>
                  <td className="px-3 py-2 sticky left-0 bg-card z-10 shadow-[inset_-1px_0_0_var(--border)]">
                    <div className="font-mono-deck text-foreground">{p.key}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">{p.description}</div>
                    {p.last_run_error && (
                      <div className="text-[10px] text-red-400 mt-0.5 truncate" title={p.last_run_error}>
                        last error: {p.last_run_error}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      min={0}
                      max={3650}
                      value={daysValue}
                      onChange={(e) =>
                        setPendingDays((prev) => ({ ...prev, [p.key]: Number(e.target.value) }))
                      }
                      onBlur={() => {
                        if (!editing) return;
                        const v = pendingDays[p.key];
                        if (v !== p.retention_days && Number.isFinite(v)) {
                          updatePolicy(p.key, { retention_days: v });
                        }
                        setPendingDays((prev) => {
                          const next = { ...prev };
                          delete next[p.key];
                          return next;
                        });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                        if (e.key === "Escape") {
                          setPendingDays((prev) => {
                            const next = { ...prev };
                            delete next[p.key];
                            return next;
                          });
                        }
                      }}
                      className="w-14 bg-secondary/40 border border-border rounded px-1.5 py-0.5 text-right tabular-nums font-mono-deck text-foreground"
                    />
                    <span className="text-muted-foreground ml-1">d</span>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums font-mono-deck text-muted-foreground">
                    {p.rows_total.toLocaleString()}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 text-right tabular-nums font-mono-deck",
                      p.rows_would_prune > 0 ? "text-yellow-400" : "text-muted-foreground",
                    )}
                  >
                    {p.rows_would_prune > 0 ? p.rows_would_prune.toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {p.last_run_at ? (
                      <div title={formatAbsoluteTime(p.last_run_at)}>
                        <div className="text-foreground">{formatRelativeTime(p.last_run_at)}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {p.last_run_rows_deleted ?? 0} deleted
                        </div>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">never</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {p.paused ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400">
                        <Pause className="w-2.5 h-2.5" />
                        paused
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400">
                        <Check className="w-2.5 h-2.5" />
                        active
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right sticky right-0 bg-card z-10 shadow-[inset_1px_0_0_var(--border)]">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => updatePolicy(p.key, { paused: !p.paused })}
                        disabled={actionInFlight === updateKey}
                        className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
                        title={p.paused ? "Activate this policy" : "Pause this policy"}
                      >
                        {p.paused ? (
                          <>
                            <Play className="w-2.5 h-2.5" />
                            Activate
                          </>
                        ) : (
                          <>
                            <Pause className="w-2.5 h-2.5" />
                            Pause
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => setConfirmRun(p)}
                        disabled={actionInFlight === runKey}
                        className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
                        title="Run this policy now (bypasses paused state)"
                      >
                        <Play className="w-2.5 h-2.5" />
                        Run now
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      </div>

      {/* Cron schedule footnote */}
      <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
        <Clock className="w-3 h-3" />
        Daily cron runs at 04:00 UTC. plugin_audit_log is deliberately excluded — kept indefinitely.
      </div>

      {/* Per-policy run confirmation modal */}
      {confirmRun && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg p-5 max-w-md w-full space-y-3">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-display text-foreground">Run {confirmRun.key} now?</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  This will delete{" "}
                  <span className="text-yellow-400 font-mono-deck font-semibold">
                    {confirmRun.rows_would_prune.toLocaleString()}
                  </span>{" "}
                  row{confirmRun.rows_would_prune === 1 ? "" : "s"} from{" "}
                  <code className="font-mono-deck">{confirmRun.table}</code> matching the
                  current retention threshold ({confirmRun.retention_days}d). The policy is
                  currently <strong>{confirmRun.paused ? "paused" : "active"}</strong> — running
                  manually bypasses that flag.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setConfirmRun(null)}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => runPolicy(confirmRun.key)}
                disabled={actionInFlight !== null}
                className="h-8 px-3 rounded-md bg-blue-500 text-white text-xs hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Play className="w-3 h-3" />
                Run now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Run-all confirmation modal */}
      {confirmRunAll && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg p-5 max-w-md w-full space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-display text-foreground">Run all unpaused policies?</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  This will run every UNPAUSED policy and delete approximately{" "}
                  <span className="text-yellow-400 font-mono-deck font-semibold">
                    {policies
                      .filter((p) => !p.paused)
                      .reduce((s, p) => s + p.rows_would_prune, 0)
                      .toLocaleString()}
                  </span>{" "}
                  row(s) total. Paused policies are skipped.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setConfirmRunAll(false)}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={runAll}
                disabled={actionInFlight !== null}
                className="h-8 px-3 rounded-md bg-blue-500 text-white text-xs hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Play className="w-3 h-3" />
                Run all
              </button>
            </div>
          </div>
        </div>
      )}

      {/* B274 (v0.9.11.20): diagnostic alert subscriptions — wires
          critical /system/health findings to outbound webhooks. */}
      <DiagnosticAlertSubscriptionsSection />

      {/* B284 (v0.9.11.23): per-job-run failure alert subscriptions —
          fires a webhook with error excerpt + suggested-fix whenever a
          plugin sync run terminates with error/timeout/cancelled. */}
      <JobRunAlertsSection />
    </div>
  );
}


// ── B274 (v0.9.11.20): diagnostic alert subscriptions section ──────

interface DiagnosticAlertSubscription {
  webhook_id: string;
  name: string;
  url?: string | null;
  is_active: boolean;
  channel_type?: string;
  subscribed: boolean;
  updated_at?: string | null;
}

function DiagnosticAlertSubscriptionsSection() {
  const [subs, setSubs] = useState<DiagnosticAlertSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const r = await apiFetch("/api/maintenance/diagnostic-alerts/subscriptions");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as { subscriptions: DiagnosticAlertSubscription[] };
      setSubs(body.subscriptions ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const flash = (kind: "ok" | "err", msg: string) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5000);
  };

  const toggleSubscription = useCallback(
    async (webhook_id: string, name: string, enabled: boolean) => {
      const key = `toggle-${webhook_id}`;
      setActionInFlight(key);
      try {
        const r = await apiFetch(
          `/api/maintenance/diagnostic-alerts/subscriptions/${encodeURIComponent(webhook_id)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled }),
          },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flash("err", `Update failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        flash("ok", `${name}: ${enabled ? "subscribed" : "unsubscribed"}`);
        await load();
      } catch (e) {
        flash("err", `Update error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
      }
    },
    [load],
  );

  const sendTest = useCallback(async () => {
    setActionInFlight("test");
    try {
      const r = await apiFetch("/api/maintenance/diagnostic-alerts/test", {
        method: "POST",
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({} as { detail?: string }));
        flash("err", `Test failed (${r.status}): ${err.detail ?? "unknown"}`);
        return;
      }
      const body = (await r.json()) as { delivered: number; subscribed_webhooks: number };
      flash(
        body.delivered > 0 ? "ok" : "err",
        `Test alert: ${body.delivered}/${body.subscribed_webhooks} webhook(s) delivered.`,
      );
    } catch (e) {
      flash("err", `Test error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setActionInFlight(null);
    }
  }, []);

  const subscribedCount = subs.filter((s) => s.subscribed).length;

  return (
    <div className="space-y-3 pt-4 border-t border-border/50">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-display text-foreground flex items-center gap-2">
            <Database className="w-4 h-4 text-muted-foreground" />
            Diagnostic alert subscriptions
          </h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Webhooks that receive critical findings from /system/health. Opt-in per webhook.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {subscribedCount > 0 && (
            <button
              onClick={sendTest}
              disabled={actionInFlight !== null}
              className="h-8 px-3 rounded-md text-xs font-medium border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 flex items-center gap-1.5 disabled:opacity-50"
              title="Fire a synthetic critical finding to every subscribed webhook"
            >
              <Play className="w-3 h-3" />
              Send test alert
            </button>
          )}
          <button
            onClick={load}
            disabled={refreshing}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
          <p className="text-[11px] text-red-300">Failed to load: {error}</p>
        </div>
      )}

      {toast && (
        <div
          className={cn(
            "rounded-lg px-4 py-2 border",
            toast.kind === "ok"
              ? "bg-green-500/10 border-green-500/20 text-green-300"
              : "bg-red-500/10 border-red-500/20 text-red-300",
          )}
        >
          <p className="text-xs">{toast.msg}</p>
        </div>
      )}

      {loading ? (
        <p className="text-xs text-muted-foreground">Loading subscriptions…</p>
      ) : subs.length === 0 ? (
        <div className="bg-card border border-border rounded-lg px-4 py-5 text-center">
          <p className="text-xs text-muted-foreground">
            No outbound webhooks configured. Install the webhooks plugin and add an outbound
            endpoint to enable diagnostic alerts.
          </p>
        </div>
      ) : (
        <>
          {/* Mobile (<sm): diagnostic-alerts subscriptions as cards */}
          <div className="block sm:hidden space-y-2">
            {subs.map((s) => (
              <MobileCard
                key={`${s.webhook_id}-card`}
                title={
                  <div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono-deck text-foreground text-sm break-words">{s.name}</span>
                      {s.channel_type === "slack" && (
                        <span
                          className="text-[9px] font-mono-deck px-1 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-400"
                          title="Block Kit formatting (B283)"
                        >
                          slack
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono-deck">{s.webhook_id.slice(0, 8)}…</div>
                  </div>
                }
                badge={
                  s.is_active ? (
                    <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-green-500/30 bg-green-500/10 text-green-400">
                      active
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-border bg-secondary text-muted-foreground">
                      inactive
                    </span>
                  )
                }
                actions={
                  <button
                    onClick={() => toggleSubscription(s.webhook_id, s.name, !s.subscribed)}
                    disabled={actionInFlight === `toggle-${s.webhook_id}` || !s.is_active}
                    className={cn(
                      "w-full text-xs px-2 py-1.5 rounded border flex items-center justify-center gap-1 disabled:opacity-50",
                      s.subscribed
                        ? "border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                        : "border-border bg-secondary/40 hover:bg-secondary text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {s.subscribed ? (
                      <><Check className="w-3 h-3" /> Subscribed</>
                    ) : (
                      <><Pause className="w-3 h-3" /> Off</>
                    )}
                  </button>
                }
              >
                <MobileCardRow label="URL" valueClassName="font-mono-deck text-muted-foreground truncate max-w-[14rem]">
                  <span title={s.url ?? ""}>{s.url ?? "—"}</span>
                </MobileCardRow>
              </MobileCard>
            ))}
          </div>

          {/* Desktop (sm+): subscriptions table */}
          <div className="hidden sm:block bg-card border border-border rounded-lg overflow-hidden">
          <DataTable minWidth="600px">
            <thead className="bg-secondary/30 border-b border-border">
              <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="text-left font-semibold px-3 py-2 sticky left-0 bg-card z-10">Webhook</th>
                <th className="text-left font-semibold px-3 py-2">URL</th>
                <th className="text-left font-semibold px-3 py-2 w-28">Status</th>
                <th className="text-right font-semibold px-3 py-2 w-32 sticky right-0 bg-card z-10">Subscribed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {subs.map((s) => (
                <tr key={s.webhook_id}>
                  <td className="px-3 py-2 sticky left-0 bg-card z-10 shadow-[inset_-1px_0_0_var(--border)]">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono-deck text-foreground">{s.name}</span>
                      {s.channel_type === "slack" && (
                        <span
                          className="text-[9px] font-mono-deck px-1 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-400"
                          title="Block Kit formatting (B283)"
                        >
                          slack
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono-deck">{s.webhook_id.slice(0, 8)}…</div>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="font-mono-deck text-muted-foreground truncate block max-w-[24rem]"
                      title={s.url ?? ""}
                    >
                      {s.url ?? "—"}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    {s.is_active ? (
                      <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-green-500/30 bg-green-500/10 text-green-400">
                        active
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-border bg-secondary text-muted-foreground">
                        inactive
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right sticky right-0 bg-card z-10 shadow-[inset_1px_0_0_var(--border)]">
                    <button
                      onClick={() => toggleSubscription(s.webhook_id, s.name, !s.subscribed)}
                      disabled={actionInFlight === `toggle-${s.webhook_id}` || !s.is_active}
                      className={cn(
                        "text-[11px] px-2 py-1 rounded border flex items-center gap-1 ml-auto disabled:opacity-50",
                        s.subscribed
                          ? "border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                          : "border-border bg-secondary/40 hover:bg-secondary text-muted-foreground hover:text-foreground",
                      )}
                      title={
                        s.is_active
                          ? s.subscribed
                            ? "Click to unsubscribe"
                            : "Click to subscribe"
                          : "Webhook is inactive — activate it in the webhooks plugin first"
                      }
                    >
                      {s.subscribed ? (
                        <>
                          <Check className="w-3 h-3" />
                          Subscribed
                        </>
                      ) : (
                        <>
                          <Pause className="w-3 h-3" />
                          Off
                        </>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          </div>
        </>
      )}
    </div>
  );
}


// ── B284 (v0.9.11.23): per-job-run failure alert subscriptions ──────

const ALERTABLE_STATUSES = ["error", "timeout", "cancelled"] as const;
type AlertableStatus = (typeof ALERTABLE_STATUSES)[number];

interface JobAlertSubscription {
  id: string;
  plugin_id: string;
  on_status: string[];
  webhook_id: string;
  webhook_name?: string | null;
  webhook_url?: string | null;
  webhook_active: boolean;
  webhook_channel_type?: string | null;
  enabled: boolean;
  updated_at?: string | null;
}

interface AvailableWebhook {
  id: string;
  name: string;
  url?: string | null;
  is_active: boolean;
}

function JobRunAlertsSection() {
  const [subs, setSubs] = useState<JobAlertSubscription[]>([]);
  const [webhooks, setWebhooks] = useState<AvailableWebhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<JobAlertSubscription | null>(null);
  const [formPluginId, setFormPluginId] = useState("*");
  const [formStatuses, setFormStatuses] = useState<Set<AlertableStatus>>(
    new Set(["error", "timeout"]),
  );
  const [formWebhookId, setFormWebhookId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const [r1, r2] = await Promise.all([
        apiFetch("/api/maintenance/job-alerts"),
        apiFetch("/api/maintenance/job-alerts/webhooks"),
      ]);
      if (!r1.ok) throw new Error(`HTTP ${r1.status}`);
      if (!r2.ok) throw new Error(`HTTP ${r2.status}`);
      const body1 = (await r1.json()) as { subscriptions: JobAlertSubscription[] };
      const body2 = (await r2.json()) as { webhooks: AvailableWebhook[] };
      setSubs(body1.subscriptions ?? []);
      setWebhooks(body2.webhooks ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const flash = (kind: "ok" | "err", msg: string) => {
    setToast({ kind, msg });
    setTimeout(() => setToast(null), 5000);
  };

  const resetForm = () => {
    setFormPluginId("*");
    setFormStatuses(new Set(["error", "timeout"]));
    setFormWebhookId("");
    setFormError(null);
  };

  const openCreateForm = () => {
    resetForm();
    if (webhooks.length > 0 && !formWebhookId) {
      const firstActive = webhooks.find((w) => w.is_active);
      setFormWebhookId(firstActive?.id ?? webhooks[0].id);
    }
    setShowCreateForm(true);
  };

  const submitCreate = useCallback(async () => {
    setFormError(null);
    if (formStatuses.size === 0) {
      setFormError("Pick at least one status to alert on.");
      return;
    }
    if (!formWebhookId) {
      setFormError("Pick a webhook.");
      return;
    }
    const pluginId = formPluginId.trim() || "*";
    setActionInFlight("create");
    try {
      const r = await apiFetch("/api/maintenance/job-alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plugin_id: pluginId,
          on_status: Array.from(formStatuses),
          webhook_id: formWebhookId,
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({} as { detail?: string }));
        setFormError(`Create failed (${r.status}): ${err.detail ?? "unknown"}`);
        return;
      }
      flash("ok", `Subscription created for plugin=${pluginId}.`);
      setShowCreateForm(false);
      resetForm();
      await load();
    } catch (e) {
      setFormError(`Create error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setActionInFlight(null);
    }
  }, [formPluginId, formStatuses, formWebhookId, load]);

  const toggleEnabled = useCallback(
    async (sub: JobAlertSubscription) => {
      const key = `toggle-${sub.id}`;
      setActionInFlight(key);
      try {
        const r = await apiFetch(
          `/api/maintenance/job-alerts/${encodeURIComponent(sub.id)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: !sub.enabled }),
          },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flash("err", `Update failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        flash("ok", `Subscription ${!sub.enabled ? "enabled" : "disabled"}.`);
        await load();
      } catch (e) {
        flash("err", `Update error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
      }
    },
    [load],
  );

  const deleteSubscription = useCallback(
    async (sub: JobAlertSubscription) => {
      const key = `delete-${sub.id}`;
      setActionInFlight(key);
      try {
        const r = await apiFetch(
          `/api/maintenance/job-alerts/${encodeURIComponent(sub.id)}`,
          { method: "DELETE" },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flash("err", `Delete failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        flash("ok", `Subscription deleted.`);
        await load();
      } catch (e) {
        flash("err", `Delete error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
        setConfirmDelete(null);
      }
    },
    [load],
  );

  const sendTest = useCallback(
    async (sub: JobAlertSubscription) => {
      const key = `test-${sub.id}`;
      setActionInFlight(key);
      try {
        const r = await apiFetch(
          `/api/maintenance/job-alerts/${encodeURIComponent(sub.id)}/test`,
          { method: "POST" },
        );
        if (!r.ok) {
          const err = await r.json().catch(() => ({} as { detail?: string }));
          flash("err", `Test failed (${r.status}): ${err.detail ?? "unknown"}`);
          return;
        }
        const body = (await r.json()) as { delivered: number; skipped: number; reason?: string };
        if (body.delivered > 0) {
          flash("ok", `Test alert delivered to ${sub.webhook_name ?? "webhook"}.`);
        } else {
          flash("err", `Test alert not delivered${body.reason ? `: ${body.reason}` : ""}.`);
        }
      } catch (e) {
        flash("err", `Test error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
      }
    },
    [],
  );

  const toggleStatus = (s: AlertableStatus) => {
    setFormStatuses((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  return (
    <div className="space-y-3 pt-4 border-t border-border/50">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-display text-foreground flex items-center gap-2">
            <Bell className="w-4 h-4 text-muted-foreground" />
            Job-run failure alerts
          </h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Fire a webhook with the error excerpt + suggested fix whenever a plugin sync run
            terminates with error / timeout / cancelled. Use <code className="font-mono-deck">*</code> for "any plugin".
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openCreateForm}
            disabled={actionInFlight !== null || webhooks.length === 0}
            className="h-8 px-3 rounded-md text-xs font-medium border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 flex items-center gap-1.5 disabled:opacity-50"
            title={
              webhooks.length === 0
                ? "Install the webhooks plugin and add an outbound webhook first"
                : "Add a new job-alert subscription"
            }
          >
            <Plus className="w-3 h-3" />
            Add subscription
          </button>
          <button
            onClick={load}
            disabled={refreshing}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
          <p className="text-[11px] text-red-300">Failed to load: {error}</p>
        </div>
      )}

      {toast && (
        <div
          className={cn(
            "rounded-lg px-4 py-2 border",
            toast.kind === "ok"
              ? "bg-green-500/10 border-green-500/20 text-green-300"
              : "bg-red-500/10 border-red-500/20 text-red-300",
          )}
        >
          <p className="text-xs">{toast.msg}</p>
        </div>
      )}

      {loading ? (
        <p className="text-xs text-muted-foreground">Loading subscriptions…</p>
      ) : webhooks.length === 0 ? (
        <div className="bg-card border border-border rounded-lg px-4 py-5 text-center">
          <p className="text-xs text-muted-foreground">
            No outbound webhooks configured. Install the webhooks plugin and add an outbound
            endpoint to enable job-run alerts.
          </p>
        </div>
      ) : subs.length === 0 ? (
        <div className="bg-card border border-border rounded-lg px-4 py-5 text-center">
          <p className="text-xs text-muted-foreground">
            No subscriptions yet. Click <strong>Add subscription</strong> to get pinged when a
            plugin sync fails.
          </p>
        </div>
      ) : (
        <>
          {/* Mobile (<sm): job-alerts subscriptions as cards */}
          <div className="block sm:hidden space-y-2">
            {subs.map((s) => {
              const orphan = !s.webhook_name;
              return (
                <MobileCard
                  key={`${s.id}-card`}
                  className={cn(!s.enabled && "opacity-60")}
                  title={
                    <div className="font-mono-deck text-foreground text-sm break-words">
                      {s.plugin_id === "*" ? <span className="text-blue-400">any plugin</span> : s.plugin_id}
                    </div>
                  }
                  badge={
                    !s.enabled ? (
                      <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-border bg-secondary text-muted-foreground">
                        disabled
                      </span>
                    ) : !s.webhook_active ? (
                      <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400">
                        webhook inactive
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-green-500/30 bg-green-500/10 text-green-400">
                        active
                      </span>
                    )
                  }
                  actions={
                    <>
                      <button
                        onClick={() => sendTest(s)}
                        disabled={actionInFlight !== null || orphan || !s.webhook_active}
                        className="flex-1 text-xs px-2 py-1.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center justify-center gap-1 disabled:opacity-40"
                      >
                        <Send className="w-3 h-3" /> Test
                      </button>
                      <button
                        onClick={() => toggleEnabled(s)}
                        disabled={actionInFlight === `toggle-${s.id}`}
                        className="flex-1 text-xs px-2 py-1.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        {s.enabled ? (
                          <><Pause className="w-3 h-3" /> Disable</>
                        ) : (
                          <><Play className="w-3 h-3" /> Enable</>
                        )}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(s)}
                        disabled={actionInFlight === `delete-${s.id}`}
                        className="flex-1 text-xs px-2 py-1.5 rounded border border-red-500/30 hover:bg-red-500/10 text-red-400 flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    </>
                  }
                >
                  <MobileCardRow label="Alert on">
                    <div className="flex flex-wrap gap-1 justify-end">
                      {s.on_status.map((st) => (
                        <span
                          key={st}
                          className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                        >
                          {st}
                        </span>
                      ))}
                    </div>
                  </MobileCardRow>
                  {orphan ? (
                    <MobileCardRow label="Webhook" valueClassName="text-red-400 italic text-[11px]">
                      missing (id: {s.webhook_id.slice(0, 8)}…)
                    </MobileCardRow>
                  ) : (
                    <>
                      <MobileCardRow label="Webhook">
                        <div className="flex items-center gap-1.5 justify-end flex-wrap">
                          <span className="font-mono-deck text-foreground">{s.webhook_name}</span>
                          {s.webhook_channel_type === "slack" && (
                            <span
                              className="text-[9px] font-mono-deck px-1 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-400"
                              title="Block Kit formatting (B283)"
                            >
                              slack
                            </span>
                          )}
                        </div>
                      </MobileCardRow>
                      {s.webhook_url && (
                        <MobileCardRow label="URL" valueClassName="text-[10px] text-muted-foreground truncate max-w-[14rem]">
                          <span title={s.webhook_url}>{s.webhook_url}</span>
                        </MobileCardRow>
                      )}
                    </>
                  )}
                </MobileCard>
              );
            })}
          </div>

          {/* Desktop (sm+): job-alerts subscriptions table */}
          <div className="hidden sm:block bg-card border border-border rounded-lg overflow-hidden">
          <DataTable minWidth="780px">
            <thead className="bg-secondary/30 border-b border-border">
              <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="text-left font-semibold px-3 py-2 sticky left-0 bg-card z-10">Plugin</th>
                <th className="text-left font-semibold px-3 py-2 w-44">Alert on</th>
                <th className="text-left font-semibold px-3 py-2">Webhook</th>
                <th className="text-left font-semibold px-3 py-2 w-24">Status</th>
                <th className="text-right font-semibold px-3 py-2 w-56 sticky right-0 bg-card z-10">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {subs.map((s) => {
                const orphan = !s.webhook_name;
                return (
                  <tr key={s.id} className={cn(!s.enabled && "opacity-60")}>
                    <td className="px-3 py-2 sticky left-0 bg-card z-10 shadow-[inset_-1px_0_0_var(--border)]">
                      <div className="font-mono-deck text-foreground">
                        {s.plugin_id === "*" ? (
                          <span className="text-blue-400">any plugin</span>
                        ) : (
                          s.plugin_id
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {s.on_status.map((st) => (
                          <span
                            key={st}
                            className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                          >
                            {st}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {orphan ? (
                        <span className="text-[11px] text-red-400 italic">
                          webhook missing (id: {s.webhook_id.slice(0, 8)}…)
                        </span>
                      ) : (
                        <>
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono-deck text-foreground">{s.webhook_name}</span>
                            {s.webhook_channel_type === "slack" && (
                              <span
                                className="text-[9px] font-mono-deck px-1 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-400"
                                title="Block Kit formatting (B283)"
                              >
                                slack
                              </span>
                            )}
                          </div>
                          <div
                            className="text-[10px] text-muted-foreground truncate max-w-[20rem]"
                            title={s.webhook_url ?? ""}
                          >
                            {s.webhook_url ?? "—"}
                          </div>
                        </>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {!s.enabled ? (
                        <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-border bg-secondary text-muted-foreground">
                          disabled
                        </span>
                      ) : !s.webhook_active ? (
                        <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400">
                          webhook inactive
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono-deck px-1.5 py-0.5 rounded border border-green-500/30 bg-green-500/10 text-green-400">
                          active
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right sticky right-0 bg-card z-10 shadow-[inset_1px_0_0_var(--border)]">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => sendTest(s)}
                          disabled={actionInFlight !== null || orphan || !s.webhook_active}
                          className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-40"
                          title={
                            orphan
                              ? "Webhook missing — can't test"
                              : !s.webhook_active
                                ? "Webhook inactive — activate it in the webhooks plugin first"
                                : "Fire a synthetic alert payload now"
                          }
                        >
                          <Send className="w-2.5 h-2.5" />
                          Test
                        </button>
                        <button
                          onClick={() => toggleEnabled(s)}
                          disabled={actionInFlight === `toggle-${s.id}`}
                          className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
                          title={s.enabled ? "Disable this subscription" : "Enable this subscription"}
                        >
                          {s.enabled ? (
                            <>
                              <Pause className="w-2.5 h-2.5" />
                              Disable
                            </>
                          ) : (
                            <>
                              <Play className="w-2.5 h-2.5" />
                              Enable
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(s)}
                          disabled={actionInFlight === `delete-${s.id}`}
                          className="text-[10px] px-1.5 py-0.5 rounded border border-red-500/30 hover:bg-red-500/10 text-red-400 flex items-center gap-1 disabled:opacity-50"
                          title="Delete this subscription"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
          </div>
        </>
      )}

      {/* Create-subscription modal */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg p-5 max-w-lg w-full space-y-4">
            <div className="flex items-start gap-3">
              <Bell className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-sm font-display text-foreground">Add job-alert subscription</h3>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Fire the chosen webhook whenever a plugin sync ends in one of the selected
                  terminal statuses.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Plugin
                </label>
                <input
                  type="text"
                  value={formPluginId}
                  onChange={(e) => setFormPluginId(e.target.value)}
                  placeholder="* (any plugin) or a slug like 'github-issues'"
                  className="w-full bg-secondary/40 border border-border rounded px-2 py-1.5 text-xs font-mono-deck text-foreground"
                />
                <p className="text-[10px] text-muted-foreground mt-1">
                  Use <code className="font-mono-deck">*</code> to receive alerts from every
                  plugin, or a specific plugin slug.
                </p>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Alert on
                </label>
                <div className="flex flex-wrap gap-2">
                  {ALERTABLE_STATUSES.map((s) => (
                    <label
                      key={s}
                      className={cn(
                        "text-[11px] font-mono-deck px-2 py-1 rounded border cursor-pointer flex items-center gap-1.5",
                        formStatuses.has(s)
                          ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                          : "border-border bg-secondary/40 text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={formStatuses.has(s)}
                        onChange={() => toggleStatus(s)}
                        className="hidden"
                      />
                      {formStatuses.has(s) && <Check className="w-3 h-3" />}
                      {s}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Webhook
                </label>
                <select
                  value={formWebhookId}
                  onChange={(e) => setFormWebhookId(e.target.value)}
                  className="w-full bg-secondary/40 border border-border rounded px-2 py-1.5 text-xs font-mono-deck text-foreground"
                >
                  <option value="">Select a webhook…</option>
                  {webhooks.map((w) => (
                    <option key={w.id} value={w.id} disabled={!w.is_active}>
                      {w.name}
                      {!w.is_active ? " (inactive)" : ""}
                    </option>
                  ))}
                </select>
              </div>

              {formError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
                  <p className="text-[11px] text-red-300">{formError}</p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setShowCreateForm(false);
                  resetForm();
                }}
                disabled={actionInFlight === "create"}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={submitCreate}
                disabled={actionInFlight === "create"}
                className="h-8 px-3 rounded-md bg-blue-500 text-white text-xs hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus className="w-3 h-3" />
                Create subscription
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg p-5 max-w-md w-full space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-display text-foreground">Delete subscription?</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  This will stop alerts for plugin{" "}
                  <code className="font-mono-deck">{confirmDelete.plugin_id}</code> on{" "}
                  <code className="font-mono-deck">
                    {confirmDelete.on_status.join(", ")}
                  </code>{" "}
                  via webhook{" "}
                  <code className="font-mono-deck">
                    {confirmDelete.webhook_name ?? confirmDelete.webhook_id.slice(0, 8)}
                  </code>
                  . You can recreate it later.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setConfirmDelete(null)}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteSubscription(confirmDelete)}
                disabled={actionInFlight !== null}
                className="h-8 px-3 rounded-md bg-red-500 text-white text-xs hover:bg-red-600 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
