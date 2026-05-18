/**
 * SyncStatusCard — Unified sync status + schedule UI for the plugin Settings tab.
 *
 * B205 (v0.9.6): replaces the previous "Last sync" + "Sync schedule" blocks
 * which read from divergent data sources (job_runs vs sync_schedule_registry)
 * and could disagree on "when did sync last run".
 *
 * States:
 *   Idle       — last-sync summary + [Sync Now]
 *   Queued     — spinner + "Queued — waiting for worker" + [Cancel]
 *   Running    — progress bar + message + elapsed + heartbeat dot + [Cancel]
 *   Cancelling — amber spinner + "Cancelling…" + (no buttons)
 *   Completed  — transient banner above card on cold transition
 *   Failed     — red row with error excerpt + [Retry] + [View log]
 *
 * Polls /api/plugins/:id/sync/status every 3s while a run is active, every
 * 30s when idle. The card also embeds a collapsible "Schedule settings"
 * subsection with a friendly Every-N-(Minutes/Hours/Days) builder and a
 * "Use custom cron" toggle for power users.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  RefreshCw,
  Clock,
  XCircle,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────

interface ProgressData {
  pct?: number;
  message?: string;
  rows_done?: number;
  rows_total?: number;
}

interface CurrentRun {
  run_id: number;
  status: "queued" | "running" | "cancelling";
  source: string | null;
  started_at: string | null;
  heartbeat_at: string | null;
  progress: ProgressData;
  elapsed_sec: number | null;
}

interface LastSuccess {
  run_id: number;
  completed_at: string | null;
  duration_ms: number | null;
  rows_written: number | null;
  source: string | null;
}

interface LastFailure {
  run_id: number;
  completed_at: string | null;
  status: string;
  /**
   * B313 (v0.10.4): clean headline (typically the exception class +
   * message). Backend extracts this from the traceback stored in
   * job_runs.error.
   */
  error: string | null;
  /**
   * Full traceback text the backend returned alongside `error`. Only
   * set when the original stderr looked like a Python traceback;
   * surfaces render it behind a "Show details" disclosure.
   */
  error_details?: string | null;
  source: string | null;
}

interface SyncStatus {
  current: CurrentRun | null;
  last_success: LastSuccess | null;
  last_failure: LastFailure | null;
  last_sync: string | null;
}

interface ScheduleData {
  plugin_id: string;
  manifest_cron: string | null;
  manifest_cron_display: string | null;
  override_cron: string | null;
  override_cron_display: string | null;
  effective_cron: string | null;
  effective_cron_display: string | null;
  source: "manifest" | "override";
  registry: {
    next_fire_at: string | null;
    last_enqueued_at: string | null;
    last_run_id: number | null;
    last_error: string | null;
    updated_at: string | null;
  } | null;
  scheduler_alive: boolean;
}

type IntervalUnit = "minutes" | "hours" | "days";

// ── Helpers ───────────────────────────────────────────────────────────

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const diffMs = d.getTime() - Date.now();
  const abs = Math.abs(diffMs);
  const mins = Math.round(abs / 60000);
  const hrs = Math.floor(mins / 60);
  const days = Math.floor(hrs / 24);
  if (abs < 60000) return diffMs >= 0 ? "in <1 min" : "<1 min ago";
  if (mins < 60) return diffMs >= 0 ? `in ${mins} min` : `${mins} min ago`;
  if (hrs < 24) return diffMs >= 0 ? `in ${hrs}h ${mins % 60}m` : `${hrs}h ${mins % 60}m ago`;
  return diffMs >= 0 ? `in ${days}d ${hrs % 24}h` : `${days}d ${hrs % 24}h ago`;
}

function formatElapsed(sec: number | null): string {
  if (sec === null || sec < 0) return "—";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  return formatElapsed(Math.round(ms / 1000));
}

function heartbeatAge(iso: string | null): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
}

function progressPct(p: ProgressData): number | null {
  if (typeof p.pct === "number" && !isNaN(p.pct)) return Math.max(0, Math.min(100, p.pct));
  if (
    typeof p.rows_done === "number" &&
    typeof p.rows_total === "number" &&
    p.rows_total > 0
  ) {
    return Math.max(0, Math.min(100, (p.rows_done / p.rows_total) * 100));
  }
  return null;
}

// Try to parse an effective cron into the friendly form. Mirrors the
// backend's _cron_to_display + _interval_to_cron.
function cronToInterval(cron: string | null): { value: number; unit: IntervalUnit } | null {
  if (!cron) return null;
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return null;
  const [minute, hour, dom, month, dow] = parts;

  // Every N days: 0 0 */N * *
  if (minute === "0" && hour === "0" && dom.startsWith("*/") && month === "*" && dow === "*") {
    const n = parseInt(dom.slice(2), 10);
    if (Number.isFinite(n) && n >= 1) return { value: n, unit: "days" };
  }
  // Other shapes need (dom, month, dow) all wildcards.
  if (dom !== "*" || month !== "*" || dow !== "*") return null;

  // Every N minutes: */N * * * *
  if (minute.startsWith("*/") && hour === "*") {
    const n = parseInt(minute.slice(2), 10);
    if (Number.isFinite(n) && n >= 1) return { value: n, unit: "minutes" };
  }
  // Every N hours: 0 */N * * *
  if (minute === "0" && hour.startsWith("*/")) {
    const n = parseInt(hour.slice(2), 10);
    if (Number.isFinite(n) && n >= 1) return { value: n, unit: "hours" };
  }
  return null;
}

// ── Card ──────────────────────────────────────────────────────────────

export default function SyncStatusCard({
  pluginId,
  isUtility,
}: {
  pluginId: string;
  isUtility: boolean;
}) {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [schedule, setSchedule] = useState<ScheduleData | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [completionBanner, setCompletionBanner] = useState<{
    kind: "success" | "failure";
    message: string;
  } | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const prevCurrentRef = useRef<CurrentRun | null>(null);
  const tickRef = useRef(0);

  // Polling: 3s while current run is non-null, 30s otherwise.
  // Re-fetch schedule on the slower cadence too — next_fire_at moves.
  const refreshStatus = useCallback(async () => {
    try {
      const r = await apiFetch(`/api/plugins/${pluginId}/sync/status`);
      if (r.ok) {
        const data: SyncStatus = await r.json();
        setStatus(data);

        // Detect cold transition: had a current run, now we don't.
        const prev = prevCurrentRef.current;
        if (prev && !data.current) {
          // The run we were watching just terminated. Decide success vs failure
          // by comparing run_id with last_success/last_failure.
          if (data.last_success && data.last_success.run_id === prev.run_id) {
            const rows = data.last_success.rows_written ?? 0;
            const dur = formatDuration(data.last_success.duration_ms);
            setCompletionBanner({
              kind: "success",
              message: `Synced ${rows.toLocaleString()} row${rows !== 1 ? "s" : ""} in ${dur}`,
            });
          } else if (data.last_failure && data.last_failure.run_id === prev.run_id) {
            const errExcerpt = data.last_failure.error
              ? data.last_failure.error.slice(0, 200)
              : `Sync ${data.last_failure.status}`;
            setCompletionBanner({
              kind: "failure",
              message: errExcerpt,
            });
          }
        }
        prevCurrentRef.current = data.current;
      }
    } catch {
      /* network blip — keep polling */
    }
  }, [pluginId]);

  const refreshSchedule = useCallback(async () => {
    try {
      const r = await apiFetch(`/api/plugins/${pluginId}/sync-schedule`);
      if (r.ok) {
        const data: ScheduleData = await r.json();
        setSchedule(data);
      }
    } catch {
      /* idem */
    }
  }, [pluginId]);

  // Initial fetch.
  useEffect(() => {
    refreshStatus();
    refreshSchedule();
  }, [refreshStatus, refreshSchedule]);

  // Polling loop with cadence switch.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      const isActive = status?.current != null;
      const cadenceMs = isActive ? 3000 : 30000;
      // Always refresh status; refresh schedule only on the slower tick to
      // keep DB load trivial when many plugin tabs are open.
      await refreshStatus();
      tickRef.current += 1;
      if (tickRef.current % 5 === 0 || !isActive) {
        await refreshSchedule();
      }
      if (!cancelled) setTimeout(tick, cadenceMs);
    };
    const id = setTimeout(tick, status?.current ? 3000 : 30000);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
    // status?.current is the cadence trigger — re-establish loop when it
    // flips between null and non-null.
  }, [status?.current, refreshStatus, refreshSchedule]);

  // Auto-dismiss the completion banner after 10s.
  useEffect(() => {
    if (!completionBanner) return;
    const t = setTimeout(() => setCompletionBanner(null), 10_000);
    return () => clearTimeout(t);
  }, [completionBanner]);

  if (isUtility) return null; // utility plugins don't sync

  const current = status?.current;
  const lastSuccess = status?.last_success;
  const lastFailure = status?.last_failure;

  const triggerSync = async () => {
    setTriggerError(null);
    try {
      const r = await apiFetch(`/api/plugins/${pluginId}/sync`, { method: "POST" });
      if (r.status === 409) {
        // Already running — just refresh; the card will swap to the live view.
        await refreshStatus();
        return;
      }
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        setTriggerError(typeof err.detail === "string" ? err.detail : "Failed to trigger sync");
        return;
      }
      // Optimistic: immediately refresh so the card transitions to Queued.
      await refreshStatus();
    } catch (e) {
      setTriggerError(e instanceof Error ? e.message : "Failed to trigger sync");
    }
  };

  const cancelRun = async (runId: number) => {
    try {
      const r = await apiFetch(`/api/jobs/runs/${runId}/cancel`, { method: "POST" });
      if (r.ok) {
        await refreshStatus();
      }
    } catch {
      /* surface inline if it becomes a real problem */
    }
  };

  return (
    <div className="space-y-3">
      {/* Completion banner — transient, above the card */}
      {completionBanner && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-xs font-body flex items-center gap-2",
            completionBanner.kind === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
              : "bg-red-500/10 border-red-500/20 text-red-300"
          )}
        >
          {completionBanner.kind === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span className="flex-1">{completionBanner.message}</span>
          <button
            onClick={() => setCompletionBanner(null)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Dismiss"
          >
            <XCircle className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main card */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-sm text-foreground">Sync</h3>
          {schedule && (
            schedule.scheduler_alive ? (
              <span className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                scheduler online
              </span>
            ) : (
              <span className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                scheduler not detected
              </span>
            )
          )}
        </div>

        {/* State row */}
        {current ? (
          <ActiveRunRow current={current} onCancel={cancelRun} />
        ) : (
          <IdleRow
            lastSuccess={lastSuccess ?? null}
            lastFailure={lastFailure ?? null}
            onTrigger={triggerSync}
          />
        )}

        {triggerError && (
          <div className="text-xs text-red-400">{triggerError}</div>
        )}

        {/* Schedule summary — always visible */}
        {schedule && (schedule.effective_cron || schedule.manifest_cron) && (
          <div className="text-xs text-muted-foreground pt-2 border-t border-border space-y-1">
            <div className="flex items-center justify-between">
              <span>
                Schedule:{" "}
                <span className="text-foreground">
                  {schedule.effective_cron_display ?? (
                    <code className="font-mono-deck text-[11px]">{schedule.effective_cron}</code>
                  )}
                </span>
                <span className="ml-2 text-[10px] uppercase tracking-wider">
                  {schedule.source === "override" ? (
                    <span className="text-blue-400">Custom override</span>
                  ) : (
                    <span className="text-muted-foreground">Manifest default</span>
                  )}
                </span>
              </span>
              {schedule.registry?.next_fire_at && (
                <span className="font-mono-deck">
                  Next: {formatRelative(schedule.registry.next_fire_at)}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Schedule settings — collapsible */}
        {schedule && (
          <div className="pt-2 border-t border-border">
            <button
              type="button"
              onClick={() => setScheduleOpen((o) => !o)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {scheduleOpen ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
              Schedule settings
            </button>
            {scheduleOpen && (
              <div className="pt-3">
                <ScheduleEditor
                  pluginId={pluginId}
                  schedule={schedule}
                  onChange={refreshSchedule}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Idle row ──────────────────────────────────────────────────────────

function IdleRow({
  lastSuccess,
  lastFailure,
  onTrigger,
}: {
  lastSuccess: LastSuccess | null;
  lastFailure: LastFailure | null;
  onTrigger: () => void;
}) {
  const showFailure =
    lastFailure &&
    (!lastSuccess ||
      (lastFailure.completed_at &&
        lastSuccess.completed_at &&
        lastFailure.completed_at > lastSuccess.completed_at));

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-xs text-muted-foreground space-y-1 flex-1 min-w-0">
        {lastSuccess ? (
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 shrink-0" />
            <span>
              Last sync{" "}
              <span className="text-foreground">{formatRelative(lastSuccess.completed_at)}</span>
              {typeof lastSuccess.rows_written === "number" && lastSuccess.rows_written > 0 && (
                <span className="text-muted-foreground">
                  {" "}
                  · {lastSuccess.rows_written.toLocaleString()} rows
                </span>
              )}
              {typeof lastSuccess.duration_ms === "number" && (
                <span className="text-muted-foreground">
                  {" "}
                  · {formatDuration(lastSuccess.duration_ms)}
                </span>
              )}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 shrink-0" />
            <span>Never synced</span>
          </div>
        )}
        {showFailure && lastFailure && (
          <div className="space-y-1">
            <div className="flex items-start gap-1.5 text-red-400">
              <AlertCircle className="w-3 h-3 shrink-0 mt-0.5" />
              <span className="break-words">
                Last attempt {lastFailure.status}: {lastFailure.error ?? "(no error message)"}
              </span>
            </div>
            {lastFailure.error_details && (
              <details className="ml-4 text-[10px] text-muted-foreground">
                <summary className="cursor-pointer hover:text-foreground transition-colors select-none">
                  Show traceback
                </summary>
                <pre className="mt-1 p-2 rounded bg-secondary/30 whitespace-pre-wrap break-all font-mono-deck text-[10px] max-h-60 overflow-y-auto">
                  {lastFailure.error_details}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>
      <button
        onClick={onTrigger}
        className="h-8 px-4 rounded-md bg-secondary text-xs text-foreground font-body hover:bg-secondary/80 transition-colors flex items-center gap-2 shrink-0"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Sync Now
      </button>
    </div>
  );
}

// ── Active run row (queued / running / cancelling) ───────────────────

function ActiveRunRow({
  current,
  onCancel,
}: {
  current: CurrentRun;
  onCancel: (runId: number) => void;
}) {
  const pct = progressPct(current.progress);
  const hbAge = heartbeatAge(current.heartbeat_at);
  const hbColor =
    hbAge === null
      ? "bg-muted-foreground"
      : hbAge < 30
        ? "bg-emerald-400"
        : hbAge < 120
          ? "bg-amber-400"
          : "bg-red-400";
  const hbTip =
    hbAge === null
      ? "No heartbeat yet"
      : hbAge < 30
        ? `Heartbeat ${hbAge}s ago`
        : `Last heartbeat ${hbAge}s ago — script may be busy with a long step.`;

  const stateLabel =
    current.status === "queued"
      ? "Queued — waiting for worker"
      : current.status === "cancelling"
        ? "Cancelling…"
        : current.progress.message || "Running…";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs flex-1 min-w-0">
          <RefreshCw
            className={cn(
              "w-3.5 h-3.5 shrink-0",
              current.status === "cancelling" ? "text-amber-400" : "text-foreground",
              "animate-spin"
            )}
          />
          <span
            className={cn(
              "truncate",
              current.status === "cancelling" ? "text-amber-400" : "text-foreground"
            )}
          >
            {stateLabel}
          </span>
          {current.status === "running" && (
            <span title={hbTip} className={cn("w-2 h-2 rounded-full shrink-0", hbColor)} />
          )}
        </div>
        {current.status !== "cancelling" && (
          <button
            onClick={() => onCancel(current.run_id)}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground font-body hover:bg-red-500/20 hover:text-red-300 transition-colors flex items-center gap-1.5 shrink-0"
          >
            <XCircle className="w-3.5 h-3.5" />
            Cancel
          </button>
        )}
      </div>

      {/* Progress bar — determinate when pct known, indeterminate otherwise */}
      {current.status === "running" && (
        <div className="w-full h-1.5 bg-secondary rounded overflow-hidden">
          {pct !== null ? (
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${pct}%` }}
            />
          ) : (
            <div className="h-full w-1/3 bg-primary/60 animate-[indeterminate_1.4s_ease-in-out_infinite]" />
          )}
        </div>
      )}

      {/* Stats row */}
      <div className="flex items-center justify-between text-[11px] font-mono-deck text-muted-foreground">
        <span>run #{current.run_id}</span>
        <span>
          {pct !== null && <span>{pct.toFixed(0)}% · </span>}
          {typeof current.progress.rows_done === "number" &&
            typeof current.progress.rows_total === "number" && (
              <span>
                {current.progress.rows_done.toLocaleString()}/
                {current.progress.rows_total.toLocaleString()}
                {" · "}
              </span>
            )}
          elapsed {formatElapsed(current.elapsed_sec)}
        </span>
      </div>
    </div>
  );
}

// ── Schedule editor (friendly builder + custom-cron toggle) ──────────

function ScheduleEditor({
  pluginId,
  schedule,
  onChange,
}: {
  pluginId: string;
  schedule: ScheduleData;
  onChange: () => void;
}) {
  const initialInterval = cronToInterval(schedule.effective_cron);
  const initialMode: "interval" | "cron" = initialInterval ? "interval" : "cron";

  const [mode, setMode] = useState<"interval" | "cron">(initialMode);
  const [intervalValue, setIntervalValue] = useState(initialInterval?.value ?? 1);
  const [intervalUnit, setIntervalUnit] = useState<IntervalUnit>(
    initialInterval?.unit ?? "hours"
  );
  const [cronText, setCronText] = useState(schedule.effective_cron ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // When schedule prop changes (after a save / reset), re-sync editor state.
  useEffect(() => {
    const fresh = cronToInterval(schedule.effective_cron);
    if (fresh) {
      setIntervalValue(fresh.value);
      setIntervalUnit(fresh.unit);
      setMode((m) => (m === "cron" ? m : "interval")); // don't yank user out of cron mode
    }
    setCronText(schedule.effective_cron ?? "");
  }, [schedule.effective_cron]);

  const isOverride = schedule.source === "override";

  const save = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const body =
        mode === "interval"
          ? { interval_value: intervalValue, interval_unit: intervalUnit }
          : { cron: cronText.trim() || null };
      const r = await apiFetch(`/api/plugins/${pluginId}/sync-schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof data.detail === "string" ? data.detail : `HTTP ${r.status}`);
        return;
      }
      setMessage(
        data.preview_next_fires?.[0]
          ? `Saved. Next fire: ${formatRelative(data.preview_next_fires[0])}`
          : "Saved."
      );
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setSaving(false);
    }
  };

  const resetToDefault = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const r = await apiFetch(`/api/plugins/${pluginId}/sync-schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cron: null }),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : `HTTP ${r.status}`);
        return;
      }
      setMessage("Reset to manifest default.");
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 text-xs">
      {/* Mode toggle */}
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="radio"
            checked={mode === "interval"}
            onChange={() => setMode("interval")}
            className="accent-primary"
          />
          <span className="text-foreground">Simple</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="radio"
            checked={mode === "cron"}
            onChange={() => setMode("cron")}
            className="accent-primary"
          />
          <span className="text-foreground">Custom cron</span>
        </label>
      </div>

      {mode === "interval" ? (
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Run every</span>
          <input
            type="number"
            min={1}
            max={intervalUnit === "minutes" ? 59 : intervalUnit === "hours" ? 23 : 31}
            value={intervalValue}
            onChange={(e) => setIntervalValue(Math.max(1, parseInt(e.target.value, 10) || 1))}
            className="w-16 h-7 px-2 rounded-md bg-background border border-border text-center text-foreground"
            disabled={saving}
          />
          <select
            value={intervalUnit}
            onChange={(e) => setIntervalUnit(e.target.value as IntervalUnit)}
            className="h-7 px-2 rounded-md bg-background border border-border text-foreground"
            disabled={saving}
          >
            <option value="minutes">Minutes</option>
            <option value="hours">Hours</option>
            <option value="days">Days</option>
          </select>
        </div>
      ) : (
        <div className="space-y-1">
          <input
            type="text"
            value={cronText}
            onChange={(e) => setCronText(e.target.value)}
            placeholder={schedule.manifest_cron || "0 */6 * * *"}
            disabled={saving}
            className="w-full h-7 px-2 rounded-md bg-background border border-border text-foreground font-mono-deck"
          />
          <p className="text-[10px] text-muted-foreground">
            5-field cron expression. Leave empty + save to clear the override.
          </p>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="h-7 px-3 rounded-md bg-primary text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {isOverride && (
          <button
            type="button"
            onClick={resetToDefault}
            disabled={saving}
            className="h-7 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Reset to default
          </button>
        )}
        {schedule.registry?.last_run_id && (
          <a
            href={`/system/jobs`}
            className="ml-auto text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-1"
            title={`Last enqueued ${formatRelative(schedule.registry.last_enqueued_at)}`}
          >
            <ExternalLink className="w-3 h-3" />
            View in jobs
          </a>
        )}
      </div>

      {message && <div className="text-emerald-400">{message}</div>}
      {error && <div className="text-red-400">{error}</div>}

      {schedule.registry?.last_error && (
        <div className="text-red-400 pt-1 border-t border-border">
          Last scheduler error: {schedule.registry.last_error}
        </div>
      )}
    </div>
  );
}
