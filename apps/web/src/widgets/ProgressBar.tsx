/**
 * ProgressBar — generic value/max progress widget (P109 v0.8.2).
 *
 * Dashboard YAML usage:
 *
 *   - id: reports_backfill
 *     type: progress_bar
 *     label: Reports backfill
 *     query: >
 *       SELECT progress->>'rows_done' AS value,
 *              progress->>'rows_expected' AS max,
 *              status AS status
 *       FROM job_runs
 *       WHERE job_id = 'sync:my-plugin'
 *       ORDER BY started_at DESC LIMIT 1
 *     live: true
 *     refresh_seconds: 2
 *
 * Query must return one row with a `value` and `max` column (both numeric).
 * Optional `status` column ('success' | 'error' | 'cancelled' | …) styles
 * the bar with the matching state colour.
 */

import { cn } from "@/lib/utils";

export type ProgressStatus = "running" | "success" | "error" | "cancelled" | "skipped" | "timeout";

interface ProgressBarProps {
  label?: string;
  value: number;
  max: number;
  status?: ProgressStatus;
  loading?: boolean;
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.max(lo, Math.min(hi, n));
}

const STATUS_COLORS: Record<ProgressStatus, { fill: string; text: string }> = {
  running:   { fill: "bg-blue-500",   text: "text-blue-400" },
  success:   { fill: "bg-green-500",  text: "text-green-400" },
  error:     { fill: "bg-red-500",    text: "text-red-400" },
  cancelled: { fill: "bg-gray-500",   text: "text-gray-400" },
  skipped:   { fill: "bg-gray-500",   text: "text-gray-400" },
  timeout:   { fill: "bg-amber-500",  text: "text-amber-400" },
};

export default function ProgressBar({
  label,
  value,
  max,
  status = "running",
  loading = false,
}: ProgressBarProps) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.running;
  const valid = !Number.isNaN(value) && !Number.isNaN(max);
  const calculating = !valid || max <= 0;
  const exceeded = valid && value > max;
  const v = valid ? clamp(value, 0, Math.max(max, 1)) : 0;
  const m = valid && max > 0 ? max : 1;
  const pct = calculating ? 0 : Math.round((v / m) * 100);

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      {label && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground">{label}</span>
          {!calculating && (
            <span className={cn("text-xs font-mono-deck", colors.text)}>
              {pct}%{exceeded ? " (exceeded)" : ""}
            </span>
          )}
        </div>
      )}
      <div className="h-2 w-full bg-secondary rounded overflow-hidden">
        {loading || calculating ? (
          <div className="h-full w-full bg-secondary animate-pulse" />
        ) : (
          <div
            className={cn("h-full transition-[width] duration-300 ease-out", colors.fill)}
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={v}
            aria-valuemin={0}
            aria-valuemax={m}
          />
        )}
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] text-muted-foreground font-mono-deck">
          {calculating
            ? "calculating…"
            : `${v.toLocaleString()} / ${max.toLocaleString()}`}
        </span>
        {status !== "running" && (
          <span className={cn("text-[10px] uppercase tracking-wider", colors.text)}>
            {status}
          </span>
        )}
      </div>
    </div>
  );
}
