/**
 * JobLiveProgress — Live progress block for an in-flight plugin sync.
 *
 * B205 (v0.9.6): embedded in the /system/jobs row expansion so operators
 * can monitor in-flight syncs without navigating to the per-plugin page.
 *
 * Polls /api/plugins/:slug/sync/status every 3s while a run is active,
 * stays mounted but quiet (no fetches) when idle. Returns null when there's
 * nothing in flight — the parent expansion already shows the historical
 * "Last run" / "Crontab entry" / "Sources" panels.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { RefreshCw, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

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

interface SyncStatus {
  current: CurrentRun | null;
  last_success: { run_id: number; completed_at: string | null } | null;
  last_failure: { run_id: number; completed_at: string | null; status: string; error: string | null } | null;
  last_sync: string | null;
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

function heartbeatAge(iso: string | null): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
}

function progressPct(p: ProgressData): number | null {
  if (typeof p.pct === "number" && !isNaN(p.pct)) return Math.max(0, Math.min(100, p.pct));
  if (typeof p.rows_done === "number" && typeof p.rows_total === "number" && p.rows_total > 0) {
    return Math.max(0, Math.min(100, (p.rows_done / p.rows_total) * 100));
  }
  return null;
}

export default function JobLiveProgress({ pluginSlug }: { pluginSlug: string }) {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const cancellingRef = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const r = await apiFetch(`/api/plugins/${pluginSlug}/sync/status`);
      if (r.ok) {
        const data: SyncStatus = await r.json();
        setStatus(data);
      }
    } catch {
      /* ignore network blip */
    }
  }, [pluginSlug]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      const isActive = status?.current != null;
      // No active run? Don't poll — the parent jobs list already polls every
      // 30s and will refresh us via re-render.
      if (!isActive) return;
      await refresh();
      if (!cancelled) setTimeout(tick, 3000);
    };
    if (status?.current) {
      const id = setTimeout(tick, 3000);
      return () => {
        cancelled = true;
        clearTimeout(id);
      };
    }
  }, [status?.current, refresh]);

  const cancelRun = async () => {
    if (!status?.current || cancellingRef.current) return;
    cancellingRef.current = true;
    try {
      const r = await apiFetch(`/api/jobs/runs/${status.current.run_id}/cancel`, {
        method: "POST",
      });
      if (r.ok) {
        await refresh();
      }
    } finally {
      cancellingRef.current = false;
    }
  };

  const current = status?.current;
  if (!current) return null;

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
    <div className="rounded-md border border-border bg-secondary/30 p-3 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs flex-1 min-w-0">
          <RefreshCw
            className={cn(
              "w-3.5 h-3.5 shrink-0 animate-spin",
              current.status === "cancelling" ? "text-amber-400" : "text-foreground"
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
            onClick={(e) => {
              e.stopPropagation();
              cancelRun();
            }}
            className="h-7 px-2.5 rounded-md bg-secondary text-[11px] text-foreground hover:bg-red-500/20 hover:text-red-300 transition-colors flex items-center gap-1 shrink-0"
          >
            <XCircle className="w-3 h-3" />
            Cancel
          </button>
        )}
      </div>

      {current.status === "running" && (
        <div className="w-full h-1.5 bg-secondary rounded overflow-hidden">
          {pct !== null ? (
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${pct}%` }}
            />
          ) : (
            <div className="h-full w-1/3 bg-primary/60 animate-pulse" />
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] font-mono-deck text-muted-foreground">
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
