/**
 * /system/jobs centralized job-state dashboard (B277).
 *
 * Layout (v0.9.11.16.3 — sections + actions):
 *   1. KPI strip — Running / Queued / Stuck / Errors 24h
 *   2. Jobs grouped into visual sections (one row per plugin):
 *        ⚠ STUCK     — orphan + stalled detection, force-stop button
 *        ⚙ RUNNING   — currently executing, cooperative stop button
 *        ⏱ QUEUED    — queued, waiting for worker
 *        ⚡ NEXT UP   — idle plugins about to fire (next 60min)
 *        ✗ ISSUES    — failing plugins (errors in 24h, not currently active)
 *        · IDLE      — collapsed footer, no current activity
 *   3. Schedule editor — collapsible legacy ScheduledJobs widget
 *
 * Each plugin appears in EXACTLY ONE section. Action buttons inline:
 *   - Run now    → POST /api/jobs/{plugin}-sync/fire-now (any plugin row)
 *   - Stop       → POST /api/jobs/{run_id}/cancel (per running run)
 *   - Force stop → POST /api/jobs/{run_id}/cancel?force=true (stuck only)
 *   - Logs ↗     → /system/logs?source=sync&since=<last_error_at>
 *
 * Stuck detection (per memory rule check_inflight_before_pg_restart):
 *   - >1 row marked 'running' for the same job_id → orphan
 *   - 1 running but elapsed > 3× recent average → stalled
 *   - 1 running but already past next scheduled fire (will_overlap_next)
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import {
  RefreshCw,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  PauseCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Hourglass,
  ArrowRight,
  Zap,
  Play,
  Square,
  AlertOctagon,
} from "lucide-react";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import ScheduledJobs from "@/widgets/ScheduledJobs";

// ── Response shape (mirrors JobsDashboardResponse on the backend) ────

interface NowItem {
  id: number;
  job_id: string;
  status: "running" | "queued" | "cancelling" | string;
  started_at: string;
  elapsed_ms: number;
  schedule_cron?: string | null;
  next_fire_at?: string | null;
  will_overlap_next: boolean;
  // v0.9.11.16.4: heartbeat liveness — worker writes heartbeat_at every
  // 10s. worker_alive true when the most recent heartbeat is within the
  // last 90s. The cancel endpoint refuses force-cancel when this is
  // true; the UI uses it to auto-pick Stop (cooperative) vs Force stop.
  heartbeat_at?: string | null;
  heartbeat_age_sec?: number | null;
  worker_alive?: boolean;
}

interface RecentItem {
  id: number;
  job_id: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  error_short?: string | null;
}

interface UpcomingItem {
  plugin_id: string;
  schedule_cron: string;
  next_fire_at: string;
  ms_until_fire: number;
  avg_duration_ms?: number | null;
  may_overlap: boolean;
}

interface FailingItem {
  job_id: string;
  runs_24h: number;
  errors_24h: number;
  error_rate_pct: number;
  last_error?: string | null;
  last_error_at?: string | null;
}

interface DashboardResponse {
  collected_at: string;
  now: NowItem[];
  recent: RecentItem[];
  upcoming: UpcomingItem[];
  failing: FailingItem[];
}

// ── Helpers ─────────────────────────────────────────────────────────

function fmtDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rs = s % 60;
  if (m < 60) return rs > 0 ? `${m}m ${rs}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

function pluginIdFromJobId(jobId: string): string | null {
  if (jobId.startsWith("sync:")) return jobId.substring("sync:".length);
  return null;
}

function fireNowJobIdFromPluginId(pluginId: string): string {
  return `${pluginId}-sync`;
}

function logsHref(jobId: string, since?: string | null): string {
  const params = new URLSearchParams();
  if (pluginIdFromJobId(jobId)) params.set("source", "sync");
  if (since) params.set("since", since);
  const qs = params.toString();
  return qs ? `/system/logs?${qs}` : "/system/logs";
}

// Per-plugin rollup of dashboard state.
interface PluginRollup {
  job_id: string;
  plugin_id: string | null;
  running: NowItem[];
  queued: NowItem[];
  next_fire: UpcomingItem | null;
  recent_runs: RecentItem[];
  recent_successes: number;
  recent_errors: number;
  recent_avg_duration_ms: number | null;
  errors_summary: FailingItem | null;
  primary_section: SectionId;
  stuck_reason: string | null;
}

type SectionId = "stuck" | "running" | "queued" | "next" | "issues" | "idle";

// "Next up" window — how far ahead to surface idle-plugin upcoming fires.
const NEXT_UP_WINDOW_MS = 60 * 60 * 1000;

function buildRollup(data: DashboardResponse, nowMs: number): PluginRollup[] {
  const ids = new Set<string>();
  data.now.forEach((n) => ids.add(n.job_id));
  data.recent.forEach((r) => ids.add(r.job_id));
  data.upcoming.forEach((u) => ids.add(`sync:${u.plugin_id}`));
  data.failing.forEach((f) => ids.add(f.job_id));

  const out: PluginRollup[] = [];
  ids.forEach((job_id) => {
    const plugin_id = pluginIdFromJobId(job_id);
    const running = data.now.filter(
      (n) => n.job_id === job_id && (n.status === "running" || n.status === "cancelling"),
    );
    const queued = data.now.filter((n) => n.job_id === job_id && n.status === "queued");
    const next_fire = plugin_id ? data.upcoming.find((u) => u.plugin_id === plugin_id) ?? null : null;
    const recent_runs = data.recent.filter((r) => r.job_id === job_id);
    const successes = recent_runs.filter((r) => r.status === "success").length;
    const errors = recent_runs.filter((r) => r.status === "error" || r.status === "timeout").length;
    const durations = recent_runs
      .map((r) => r.duration_ms)
      .filter((d): d is number => typeof d === "number" && d > 0);
    const avg = durations.length
      ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
      : null;
    const errors_summary = data.failing.find((f) => f.job_id === job_id) ?? null;

    // Stuck detection — heartbeat-driven (v0.9.11.16.4). Worker writes
    // heartbeat_at every 10s; if all running rows show stale heartbeats,
    // those workers are confirmed dead and the rows are orphaned.
    let stuck_reason: string | null = null;
    const allDead = running.length > 0 && running.every((r) => r.worker_alive === false);
    const someDead = running.some((r) => r.worker_alive === false);
    if (running.length > 1 && allDead) {
      const ages = running
        .map((r) => r.heartbeat_age_sec)
        .filter((a): a is number => a != null);
      const ageDesc = ages.length
        ? ` (last heartbeats ${ages.map((s) => fmtDuration(s * 1000)).join(", ")} ago)`
        : " (no heartbeat ever recorded)";
      stuck_reason = `${running.length} 'running' rows for the same job, all with dead workers${ageDesc} — orphaned (Postgres restart or scheduler crash). Force-stop cleans them up.`;
    } else if (running.length > 1) {
      stuck_reason = `${running.length} 'running' rows for the same job (${someDead ? "some workers dead" : "all workers alive"}). Investigate: this should not happen under normal operation.`;
    } else if (running.length === 1 && running[0].worker_alive === false) {
      const age = running[0].heartbeat_age_sec;
      const ageStr = age != null ? fmtDuration(age * 1000) : "ever";
      stuck_reason = `Worker unresponsive — no heartbeat for ${ageStr}. Force-stop is safe; cooperative stop would hang.`;
    } else if (running.length === 1) {
      const elapsed = Math.max(0, nowMs - Date.parse(running[0].started_at));
      if (avg && elapsed > avg * 3) {
        stuck_reason = `Running ${fmtDuration(elapsed)} — over 3× the recent average (${fmtDuration(avg)}). Worker is alive (heartbeating); cooperative stop will work.`;
      } else if (running[0].will_overlap_next) {
        stuck_reason = `Already past the next scheduled fire — this run will overlap.`;
      }
    }

    // Section assignment (each plugin lands in exactly one). Order
    // matters: more-imminent state wins. v0.9.11.18.1 — Next up is
    // temporal ("about to fire") and outranks Issues ("errored but
    // currently idle"); the recent-errors red chip still renders on
    // Next-up rows so the failure context isn't lost. Without this,
    // a plugin scheduled to fire in 22 minutes that had a couple of
    // errors earlier disappeared into Issues, which read like
    // "ignore until you have time" — wrong for an imminent run.
    let primary_section: SectionId;
    if (stuck_reason) {
      primary_section = "stuck";
    } else if (running.length > 0) {
      primary_section = "running";
    } else if (queued.length > 0) {
      primary_section = "queued";
    } else if (
      next_fire &&
      Date.parse(next_fire.next_fire_at) - nowMs <= NEXT_UP_WINDOW_MS
    ) {
      primary_section = "next";
    } else if (errors_summary && errors_summary.errors_24h > 0) {
      primary_section = "issues";
    } else {
      primary_section = "idle";
    }

    out.push({
      job_id,
      plugin_id,
      running,
      queued,
      next_fire,
      recent_runs,
      recent_successes: successes,
      recent_errors: errors,
      recent_avg_duration_ms: avg,
      errors_summary,
      primary_section,
      stuck_reason,
    });
  });

  return out;
}

// ── Component ───────────────────────────────────────────────────────

export default function JobsDashboard() {
  const [searchParams] = useSearchParams();
  // B313 (v0.10.4.1): chips in /system/logs link here with ?run_id=N.
  // Without this read the page just lands on the dashboard with no idea
  // which run the operator wanted to inspect.
  const runIdParam = searchParams.get("run_id");
  const runIdFromUrl = runIdParam ? Number(runIdParam) : null;

  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [showIdle, setShowIdle] = useState(false);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [actionToast, setActionToast] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  // B313: anchor we scroll into view once the data resolves the run_id.
  const targetRunRef = useRef<HTMLDivElement | null>(null);
  const targetRunHandled = useRef(false);
  // v0.9.11.22.5: brief "✓ Updated" pulse after a manual refresh
  // completes. Without this, the spinner ran for ~50-100ms on a fast
  // network and the click felt like it had no effect — operator
  // reported "the refresh button doesn't seem to do anything".
  const [justRefreshedAt, setJustRefreshedAt] = useState<number | null>(null);

  const load = useCallback(async (fresh: boolean = false) => {
    setRefreshing(true);
    setError(null);
    // Min-duration spinner so a fast (e.g. 80ms) request still gives
    // visible feedback that something happened. Runs in parallel with
    // the actual fetch so the perceived latency is max(spinner, fetch).
    const minSpinnerMs = fresh ? 600 : 0;
    const minSpinner = minSpinnerMs > 0
      ? new Promise((res) => setTimeout(res, minSpinnerMs))
      : Promise.resolve();
    try {
      const url = fresh ? "/api/jobs/dashboard?fresh=true" : "/api/jobs/dashboard";
      const r = await apiFetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as DashboardResponse;
      await minSpinner;
      setData(body);
      if (fresh) {
        setJustRefreshedAt(Date.now());
        // Auto-clear the "Updated" badge after 2.5s.
        window.setTimeout(() => {
          setJustRefreshedAt((prev) =>
            prev !== null && Date.now() - prev >= 2400 ? null : prev,
          );
        }, 2500);
      }
    } catch (e) {
      await minSpinner;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = window.setInterval(() => load(), 30_000);
    return () => window.clearInterval(id);
  }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  // B313 (v0.10.4.1): if URL has ?run_id=N, find the parent job_id from
  // the loaded data, expand its row, and scroll the matching recent run
  // into view. Runs once per (data, runIdFromUrl) — guarded so the 30s
  // refresh tick doesn't re-scroll on every poll.
  useEffect(() => {
    if (!runIdFromUrl || !data || targetRunHandled.current) return;
    const match =
      data.recent.find((r) => r.id === runIdFromUrl) ??
      data.now.find((r) => r.id === runIdFromUrl);
    if (!match) return;
    setExpandedJob(match.job_id);
    targetRunHandled.current = true;
    // Scroll after the next paint so the expanded section has laid out.
    window.setTimeout(() => {
      targetRunRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 100);
  }, [runIdFromUrl, data]);

  // ── Actions ──────────────────────────────────────────────────────
  // Stop one running run cooperatively. Force=true bypasses cooperative
  // cancel — for orphaned runs where the worker is confirmed gone.
  const stopRun = useCallback(
    async (runId: number, force: boolean) => {
      const key = `cancel-${runId}-${force ? "force" : "soft"}`;
      setActionInFlight(key);
      setActionToast(null);
      try {
        const url = force
          ? `/api/jobs/${runId}/cancel?force=true`
          : `/api/jobs/${runId}/cancel`;
        const r = await apiFetch(url, { method: "POST" });
        if (!r.ok) {
          const body = await r.json().catch(() => ({} as { detail?: string }));
          setActionToast(`Stop failed (${r.status}): ${body?.detail ?? "unknown"}`);
        } else {
          const body = await r.json().catch(() => ({} as { status?: string }));
          setActionToast(
            force
              ? `Run #${runId} force-cancelled.`
              : body?.status === "cancelling"
              ? `Run #${runId} cancelling — worker exits on next checkpoint.`
              : `Run #${runId} cancelled.`,
          );
          await load(true);
        }
      } catch (e) {
        setActionToast(`Stop error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
        setTimeout(() => setActionToast(null), 5000);
      }
    },
    [load],
  );

  // Stop all running runs for a plugin in one click.
  const stopAllForPlugin = useCallback(
    async (running: NowItem[], force: boolean) => {
      if (!running.length) return;
      const key = `stop-all-${running[0].job_id}-${force ? "force" : "soft"}`;
      setActionInFlight(key);
      setActionToast(null);
      let ok = 0;
      let fail = 0;
      for (const r of running) {
        try {
          const url = force
            ? `/api/jobs/${r.id}/cancel?force=true`
            : `/api/jobs/${r.id}/cancel`;
          const resp = await apiFetch(url, { method: "POST" });
          if (resp.ok) ok++;
          else fail++;
        } catch {
          fail++;
        }
      }
      setActionToast(
        fail === 0
          ? `${ok} run${ok === 1 ? "" : "s"} ${force ? "force-cancelled" : "stopping"}.`
          : `${ok} ok / ${fail} failed.`,
      );
      setActionInFlight(null);
      await load(true);
      setTimeout(() => setActionToast(null), 5000);
    },
    [load],
  );

  // Trigger a fresh run via the existing fire-now endpoint.
  const runNow = useCallback(
    async (pluginId: string) => {
      const key = `run-${pluginId}`;
      setActionInFlight(key);
      setActionToast(null);
      try {
        const fireNowJobId = fireNowJobIdFromPluginId(pluginId);
        const r = await apiFetch(`/api/jobs/${fireNowJobId}/fire-now`, { method: "POST" });
        if (!r.ok) {
          const body = await r.json().catch(() => ({} as { detail?: string }));
          setActionToast(`Fire-now failed (${r.status}): ${body?.detail ?? "unknown"}`);
        } else {
          const body = await r.json().catch(() => ({} as { status?: string }));
          setActionToast(
            body?.status === "queued"
              ? `Queued run for ${pluginId}.`
              : `Triggered ${pluginId}.`,
          );
          await load(true);
        }
      } catch (e) {
        setActionToast(`Fire-now error: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setActionInFlight(null);
        setTimeout(() => setActionToast(null), 5000);
      }
    },
    [load],
  );

  const rollup = useMemo(() => (data ? buildRollup(data, nowMs) : []), [data, nowMs]);

  // Bucket rollup by section.
  const sectionRows = useMemo(() => {
    const buckets: Record<SectionId, PluginRollup[]> = {
      stuck: [],
      running: [],
      queued: [],
      next: [],
      issues: [],
      idle: [],
    };
    rollup.forEach((p) => buckets[p.primary_section].push(p));
    // Sort within sections.
    buckets.stuck.sort((a, b) => b.running.length - a.running.length);
    buckets.running.sort((a, b) => {
      const aMs = a.running[0] ? Date.parse(a.running[0].started_at) : 0;
      const bMs = b.running[0] ? Date.parse(b.running[0].started_at) : 0;
      return aMs - bMs;
    });
    buckets.queued.sort((a, b) => b.queued.length - a.queued.length);
    buckets.next.sort((a, b) => {
      const aT = a.next_fire ? Date.parse(a.next_fire.next_fire_at) : Infinity;
      const bT = b.next_fire ? Date.parse(b.next_fire.next_fire_at) : Infinity;
      return aT - bT;
    });
    buckets.issues.sort((a, b) => {
      const aT = a.errors_summary?.last_error_at
        ? Date.parse(a.errors_summary.last_error_at)
        : 0;
      const bT = b.errors_summary?.last_error_at
        ? Date.parse(b.errors_summary.last_error_at)
        : 0;
      return bT - aT;
    });
    buckets.idle.sort((a, b) => a.job_id.localeCompare(b.job_id));
    return buckets;
  }, [rollup]);

  const stuckCount = sectionRows.stuck.length;
  const runningCount = rollup.reduce((s, p) => s + p.running.length, 0);
  const queuedCount = rollup.reduce((s, p) => s + p.queued.length, 0);
  // v0.9.11.22.6: scheduled-but-not-yet-enqueued plugins firing within
  // the next hour. Distinct from `queued` which only counts rows
  // already in the worker pickup queue. Operator feedback: KPI strip
  // showed "0 queued" while several plugins sat in the Next up section,
  // confusing the two states.
  const nextUpCount = sectionRows.next.length;
  const errors24h = rollup.reduce((s, p) => s + (p.errors_summary?.errors_24h ?? 0), 0);

  if (loading && !data) {
    return <div className="p-4 text-muted-foreground text-sm">Loading job state…</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header strip */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-display text-foreground">Job state</h2>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {data?.collected_at ? (
              <>Snapshot {formatRelativeTime(data.collected_at)} · auto-refreshes every 30s</>
            ) : (
              "Per-plugin rollup of running, queued, recent, and upcoming syncs."
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {justRefreshedAt !== null && !refreshing && (
            <span
              className="text-[11px] text-green-400 flex items-center gap-1 transition-opacity"
              role="status"
            >
              <CheckCircle2 className="w-3 h-3" />
              Updated
            </span>
          )}
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 flex items-center gap-2">
          <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="text-xs text-red-300">Failed to load dashboard: {error}</p>
        </div>
      )}

      {actionToast && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg px-4 py-2">
          <p className="text-xs text-blue-300">{actionToast}</p>
        </div>
      )}

      {/* ── KPI strip ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard
          icon={<Activity className={cn("w-4 h-4", runningCount > 0 ? "text-blue-400" : "text-muted-foreground")} />}
          label="Running"
          value={runningCount.toString()}
          tone={runningCount > 0 ? "text-blue-400" : "text-foreground"}
          tooltip="Jobs actively executing right now (worker has claimed and is running them)."
        />
        <KpiCard
          icon={<Hourglass className={cn("w-4 h-4", queuedCount > 0 ? "text-yellow-400" : "text-muted-foreground")} />}
          label="Queued"
          value={queuedCount.toString()}
          tone={queuedCount > 0 ? "text-yellow-400" : "text-foreground"}
          tooltip="Jobs already inserted into the worker queue, awaiting pickup. Usually 0 — workers poll every 2s. >0 means the queue is backing up."
        />
        <KpiCard
          icon={<Zap className={cn("w-4 h-4", nextUpCount > 0 ? "text-blue-400" : "text-muted-foreground")} />}
          label="Next up"
          value={nextUpCount.toString()}
          tone={nextUpCount > 0 ? "text-foreground" : "text-foreground"}
          tooltip="Plugins scheduled to fire within the next 60 minutes — not yet enqueued. Different from Queued (which counts rows already in the worker queue)."
        />
        <KpiCard
          icon={<AlertTriangle className={cn("w-4 h-4", stuckCount > 0 ? "text-red-400" : "text-muted-foreground")} />}
          label="Stuck"
          value={stuckCount.toString()}
          tone={stuckCount > 0 ? "text-red-400" : "text-foreground"}
          tooltip="Plugins where state suggests an orphaned or stalled run. Investigate via the per-row warning in the Stuck section."
        />
        <KpiCard
          icon={<XCircle className={cn("w-4 h-4", errors24h > 0 ? "text-red-400" : "text-muted-foreground")} />}
          label="Errors (24h)"
          value={errors24h.toString()}
          tone={errors24h > 0 ? "text-red-400" : "text-foreground"}
          tooltip="Total error count across all plugins over the last 24 hours."
        />
      </div>

      {/* ── Sectioned jobs ──────────────────────────────────────────── */}
      <Section
        id="stuck"
        title="Stuck"
        subtitle="Orphaned or stalled jobs — investigate or force-stop"
        icon={<AlertOctagon className="w-4 h-4 text-red-400" />}
        rows={sectionRows.stuck}
        emptyText="No stuck jobs."
        hideWhenEmpty
        expandedJob={expandedJob}
        onToggle={setExpandedJob}
        actionInFlight={actionInFlight}
        onStopAll={stopAllForPlugin}
        onRunNow={runNow}
        onStopRun={stopRun}
        nowMs={nowMs}
        highlightRunId={runIdFromUrl}
        highlightAnchorRef={targetRunRef}
      />

      <Section
        id="running"
        title="Running"
        subtitle="Currently executing — stop cooperatively if needed"
        icon={<Activity className="w-4 h-4 text-blue-400" />}
        rows={sectionRows.running}
        emptyText="Nothing running right now."
        expandedJob={expandedJob}
        onToggle={setExpandedJob}
        actionInFlight={actionInFlight}
        onStopAll={stopAllForPlugin}
        onRunNow={runNow}
        onStopRun={stopRun}
        nowMs={nowMs}
        highlightRunId={runIdFromUrl}
        highlightAnchorRef={targetRunRef}
      />

      <Section
        id="queued"
        title="Queued"
        subtitle="Waiting for a worker to pick up"
        icon={<Hourglass className="w-4 h-4 text-yellow-400" />}
        rows={sectionRows.queued}
        emptyText="No jobs queued."
        hideWhenEmpty
        expandedJob={expandedJob}
        onToggle={setExpandedJob}
        actionInFlight={actionInFlight}
        onStopAll={stopAllForPlugin}
        onRunNow={runNow}
        onStopRun={stopRun}
        nowMs={nowMs}
        highlightRunId={runIdFromUrl}
        highlightAnchorRef={targetRunRef}
      />

      <Section
        id="next"
        title="Next up"
        subtitle="Plugins about to fire (next 60 minutes). Recent errors stay flagged in red on the row."
        icon={<Zap className="w-4 h-4 text-foreground" />}
        rows={sectionRows.next}
        emptyText="Nothing scheduled to fire in the next hour."
        expandedJob={expandedJob}
        onToggle={setExpandedJob}
        actionInFlight={actionInFlight}
        onStopAll={stopAllForPlugin}
        onRunNow={runNow}
        onStopRun={stopRun}
        nowMs={nowMs}
        highlightRunId={runIdFromUrl}
        highlightAnchorRef={targetRunRef}
      />

      <Section
        id="issues"
        title="Issues"
        subtitle="Errors in the last 24h, currently idle — no upcoming fire in the next hour"
        icon={<XCircle className="w-4 h-4 text-red-400" />}
        rows={sectionRows.issues}
        emptyText="No errors in the last 24 hours."
        hideWhenEmpty
        expandedJob={expandedJob}
        onToggle={setExpandedJob}
        actionInFlight={actionInFlight}
        onStopAll={stopAllForPlugin}
        onRunNow={runNow}
        onStopRun={stopRun}
        nowMs={nowMs}
        highlightRunId={runIdFromUrl}
        highlightAnchorRef={targetRunRef}
      />

      {/* Idle (collapsed footer) */}
      {sectionRows.idle.length > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => setShowIdle((v) => !v)}
            className="w-full px-4 py-2.5 flex items-center gap-2 text-left text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/20"
          >
            {showIdle ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            <CheckCircle2 className="w-3.5 h-3.5 text-muted-foreground" />
            <span>
              Idle · {sectionRows.idle.length} plugin{sectionRows.idle.length === 1 ? "" : "s"}
            </span>
            <span className="text-muted-foreground/70">— no current activity, healthy recent runs</span>
          </button>
          {showIdle && (
            <div className="divide-y divide-border/50 border-t border-border/50">
              {sectionRows.idle.map((p) => (
                <PluginRollupRow
                  key={p.job_id}
                  plugin={p}
                  expanded={expandedJob === p.job_id}
                  onToggle={() => setExpandedJob((prev) => (prev === p.job_id ? null : p.job_id))}
                  actionInFlight={actionInFlight}
                  onStopAll={stopAllForPlugin}
                  onRunNow={runNow}
                  onStopRun={stopRun}
                  nowMs={nowMs}
                  highlightRunId={runIdFromUrl}
                  highlightAnchorRef={targetRunRef}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Schedule editor (collapsible) */}
      <div className="bg-card border border-border rounded-lg">
        <button
          onClick={() => setShowEditor((v) => !v)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-secondary/20 transition-colors"
        >
          <div className="flex items-center gap-2 min-w-0">
            {showEditor ? (
              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            )}
            <span className="text-sm text-foreground">Schedule editor</span>
            <span className="text-[11px] text-muted-foreground truncate">
              cron schedule overrides + per-plugin scheduler state
            </span>
          </div>
        </button>
        {showEditor && (
          <div className="px-4 pb-4 border-t border-border/50 pt-3">
            <ScheduledJobs />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Section wrapper ─────────────────────────────────────────────────

interface SectionProps {
  id: SectionId;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  rows: PluginRollup[];
  emptyText: string;
  hideWhenEmpty?: boolean;
  expandedJob: string | null;
  onToggle: (job_id: string | null) => void;
  actionInFlight: string | null;
  onStopAll: (running: NowItem[], force: boolean) => void;
  onRunNow: (pluginId: string) => void;
  onStopRun: (runId: number, force: boolean) => void;
  nowMs: number;
  highlightRunId?: number | null;
  highlightAnchorRef?: React.MutableRefObject<HTMLDivElement | null>;
}

function Section({
  id,
  title,
  subtitle,
  icon,
  rows,
  emptyText,
  hideWhenEmpty,
  expandedJob,
  onToggle,
  actionInFlight,
  onStopAll,
  onRunNow,
  onStopRun,
  nowMs,
  highlightRunId,
  highlightAnchorRef,
}: SectionProps) {
  if (hideWhenEmpty && rows.length === 0) return null;
  const isStuck = id === "stuck";
  return (
    <div
      className={cn(
        "bg-card border rounded-lg overflow-hidden",
        isStuck ? "border-red-500/30" : "border-border",
      )}
    >
      <div
        className={cn(
          "px-4 py-2.5 border-b flex items-center gap-2",
          isStuck ? "border-red-500/20 bg-red-500/5" : "border-border/50",
        )}
      >
        <div className="h-7 w-7 rounded-md bg-secondary/40 flex items-center justify-center shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
            {title}
            <span
              className={cn(
                "text-[10px] font-mono-deck px-1.5 py-0.5 rounded tabular-nums",
                rows.length === 0
                  ? "bg-secondary text-muted-foreground"
                  : isStuck
                  ? "bg-red-500/15 text-red-400"
                  : "bg-secondary text-foreground",
              )}
            >
              {rows.length}
            </span>
          </h3>
          <p className="text-[11px] text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <div className="px-4 py-4 text-center">
          <p className="text-xs text-muted-foreground">{emptyText}</p>
        </div>
      ) : (
        <div className="divide-y divide-border/50">
          {rows.map((p) => (
            <PluginRollupRow
              key={p.job_id}
              plugin={p}
              expanded={expandedJob === p.job_id}
              onToggle={() => onToggle(expandedJob === p.job_id ? null : p.job_id)}
              actionInFlight={actionInFlight}
              onStopAll={onStopAll}
              onRunNow={onRunNow}
              onStopRun={onStopRun}
              nowMs={nowMs}
              highlightRunId={highlightRunId}
              highlightAnchorRef={highlightAnchorRef}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── KPI card ────────────────────────────────────────────────────────

function KpiCard({
  icon,
  label,
  value,
  tone,
  tooltip,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: string;
  tooltip?: string;
}) {
  return (
    <div
      className="bg-card border border-border rounded-lg px-4 py-3 flex items-center gap-3"
      title={tooltip}
    >
      <div className="h-8 w-8 rounded-md bg-secondary/40 flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
          {label}
        </p>
        <p className={cn("text-sm font-display truncate", tone)}>{value}</p>
      </div>
    </div>
  );
}

// ── Per-plugin rollup row ───────────────────────────────────────────

function statusGlyph(status: string): { ch: string; tone: string } {
  if (status === "success") return { ch: "■", tone: "text-green-400" };
  if (status === "error") return { ch: "■", tone: "text-red-400" };
  if (status === "timeout") return { ch: "■", tone: "text-red-400/70" };
  if (status === "cancelled" || status === "skipped") return { ch: "□", tone: "text-muted-foreground" };
  if (status === "paused") return { ch: "▣", tone: "text-yellow-400" };
  if (status === "running" || status === "cancelling") return { ch: "▸", tone: "text-blue-400" };
  return { ch: "■", tone: "text-muted-foreground" };
}

function PluginRollupRow({
  plugin,
  expanded,
  onToggle,
  actionInFlight,
  onStopAll,
  onRunNow,
  onStopRun,
  nowMs,
  highlightRunId,
  highlightAnchorRef,
}: {
  plugin: PluginRollup;
  expanded: boolean;
  onToggle: () => void;
  actionInFlight: string | null;
  onStopAll: (running: NowItem[], force: boolean) => void;
  onRunNow: (pluginId: string) => void;
  onStopRun: (runId: number, force: boolean) => void;
  nowMs: number;
  highlightRunId?: number | null;
  highlightAnchorRef?: React.MutableRefObject<HTMLDivElement | null>;
}) {
  const isStuck = plugin.primary_section === "stuck";
  const sparkRuns = [...plugin.recent_runs].slice(0, 24).reverse();
  const totalRecent = plugin.recent_runs.length;
  const elapsed = plugin.running[0]
    ? Math.max(0, nowMs - Date.parse(plugin.running[0].started_at))
    : null;

  // v0.9.11.16.4: liveness-driven action picker. If any running row's
  // worker is dead, force-stop is the right action (cooperative would
  // hang waiting for a worker that won't poll). If all workers alive,
  // cooperative stop is right (force would 409 server-side anyway).
  const anyRunningDead =
    plugin.running.length > 0 && plugin.running.some((r) => r.worker_alive === false);
  const allRunningAlive =
    plugin.running.length > 0 && plugin.running.every((r) => r.worker_alive === true);
  const useForce = anyRunningDead;

  const stopAllSoftKey = `stop-all-${plugin.job_id}-soft`;
  const stopAllForceKey = `stop-all-${plugin.job_id}-force`;
  const runNowKey = plugin.plugin_id ? `run-${plugin.plugin_id}` : null;

  return (
    <div className={cn(isStuck && "bg-red-500/5")}>
      <button
        onClick={onToggle}
        className="w-full px-4 py-2.5 flex items-start gap-3 text-left hover:bg-secondary/20 transition-colors"
      >
        <ChevronRight
          className={cn(
            "w-3.5 h-3.5 text-muted-foreground shrink-0 mt-1 transition-transform",
            expanded && "rotate-90",
          )}
        />
        <div className="flex-1 min-w-0 space-y-1">
          {/* Top line: plugin id + state counts */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-foreground font-mono-deck truncate">{plugin.job_id}</span>
            {plugin.running.length > 0 && (
              <span
                className={cn(
                  "text-[11px] font-mono-deck flex items-center gap-1",
                  anyRunningDead ? "text-red-400" : "text-blue-400",
                )}
              >
                <Loader2 className={cn("w-3 h-3", !anyRunningDead && "animate-spin")} />
                {plugin.running.length} running
                {elapsed != null && plugin.running.length === 1 && (
                  <span className="text-muted-foreground"> · {fmtDuration(elapsed)}</span>
                )}
                {anyRunningDead && (
                  <span className="text-red-400"> · worker dead</span>
                )}
                {!anyRunningDead && allRunningAlive && plugin.running.length === 1 && (
                  <span className="text-green-400"> · live</span>
                )}
              </span>
            )}
            {plugin.queued.length > 0 && (
              <span className="text-[11px] text-yellow-400 font-mono-deck flex items-center gap-1">
                <Hourglass className="w-3 h-3" />
                {plugin.queued.length} queued
              </span>
            )}
            {plugin.errors_summary && plugin.errors_summary.errors_24h > 0 && (
              <span className="text-[11px] text-red-400 font-mono-deck flex items-center gap-1">
                <XCircle className="w-3 h-3" />
                {plugin.errors_summary.errors_24h} error{plugin.errors_summary.errors_24h === 1 ? "" : "s"} 24h
              </span>
            )}
          </div>

          {/* Stuck banner */}
          {plugin.stuck_reason && (
            <p className="text-[11px] text-red-400 flex items-start gap-1.5">
              <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
              <span>{plugin.stuck_reason}</span>
            </p>
          )}

          {/* Activity summary line */}
          <div className="flex items-center gap-3 flex-wrap text-[11px]">
            {sparkRuns.length > 0 && (
              <span className="font-mono-deck flex items-center gap-px text-[10px] leading-none">
                {sparkRuns.map((r) => {
                  const g = statusGlyph(r.status);
                  return (
                    <span
                      key={r.id}
                      className={g.tone}
                      title={`${formatAbsoluteTime(r.started_at)} — ${r.status}${
                        r.error_short ? `: ${r.error_short}` : ""
                      }`}
                    >
                      {g.ch}
                    </span>
                  );
                })}
              </span>
            )}
            {totalRecent > 0 && (
              <span
                className={cn(
                  "font-mono-deck",
                  plugin.recent_errors > 0 ? "text-red-400" : "text-green-400",
                )}
              >
                {plugin.recent_successes}/{totalRecent} success (12h)
              </span>
            )}
            {plugin.recent_avg_duration_ms != null && (
              <span className="text-muted-foreground">
                avg {fmtDuration(plugin.recent_avg_duration_ms)}
              </span>
            )}
            {plugin.next_fire && (
              <span
                className={cn(
                  "flex items-center gap-1",
                  plugin.next_fire.may_overlap ? "text-yellow-400" : "text-muted-foreground",
                )}
                title={formatAbsoluteTime(plugin.next_fire.next_fire_at)}
              >
                <Zap className="w-3 h-3" />
                next {formatRelativeTime(plugin.next_fire.next_fire_at)}
                {plugin.next_fire.schedule_cron && ` · ${plugin.next_fire.schedule_cron}`}
                {plugin.next_fire.may_overlap && " · may overlap"}
              </span>
            )}
            {!plugin.next_fire && plugin.primary_section === "idle" && (
              <span className="text-muted-foreground">no upcoming fire in next 6h</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-1.5 shrink-0 mt-0.5"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Stop / Force stop — picked automatically based on heartbeat.
              When ALL running workers are alive: cooperative stop (Square
              icon, neutral). When ANY running worker is dead: force stop
              (AlertOctagon icon, red). The cancel endpoint enforces this
              same gate server-side with a 409 if force is used against a
              live worker — UI never has to ask the operator. */}
          {plugin.running.length > 0 && useForce && (
            <button
              onClick={() => onStopAll(plugin.running, true)}
              disabled={actionInFlight === stopAllForceKey}
              className="text-[11px] px-2 py-1 rounded border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center gap-1 disabled:opacity-50"
              title="Worker(s) confirmed gone (no heartbeat) — force-mark these runs cancelled. Server gates this on liveness, so the action is safe."
            >
              <AlertOctagon className="w-3 h-3" />
              Force stop {plugin.running.length > 1 ? plugin.running.length : ""}
            </button>
          )}
          {plugin.running.length > 0 && !useForce && allRunningAlive && (
            <button
              onClick={() => onStopAll(plugin.running, false)}
              disabled={actionInFlight === stopAllSoftKey}
              className="text-[11px] px-2 py-1 rounded border border-border bg-secondary/40 hover:bg-secondary text-foreground flex items-center gap-1 disabled:opacity-50"
              title="Cooperative cancel — worker exits at its next checkpoint"
            >
              <Square className="w-3 h-3" />
              Stop
            </button>
          )}
          {/* Mixed-liveness fallback: server will pick per row. */}
          {plugin.running.length > 0 && !useForce && !allRunningAlive && (
            <button
              onClick={() => onStopAll(plugin.running, false)}
              disabled={actionInFlight === stopAllSoftKey}
              className="text-[11px] px-2 py-1 rounded border border-border bg-secondary/40 hover:bg-secondary text-foreground flex items-center gap-1 disabled:opacity-50"
              title="Cooperative cancel — heartbeat data unavailable"
            >
              <Square className="w-3 h-3" />
              Stop
            </button>
          )}
          {/* Run now — any plugin row */}
          {plugin.plugin_id && (
            <button
              onClick={() => onRunNow(plugin.plugin_id!)}
              disabled={actionInFlight === runNowKey}
              className="text-[11px] px-2 py-1 rounded border border-border bg-secondary/40 hover:bg-secondary text-foreground flex items-center gap-1 disabled:opacity-50"
              title={
                plugin.running.length > 0
                  ? "Trigger a new run alongside the existing one"
                  : "Trigger a fresh run now"
              }
            >
              <Play className="w-3 h-3" />
              Run now
            </button>
          )}
          {/* Logs deep-link */}
          <a
            href={logsHref(
              plugin.job_id,
              plugin.errors_summary?.last_error_at ?? plugin.recent_runs[0]?.started_at,
            )}
            className={cn(
              "text-[11px] flex items-center gap-1 px-1",
              plugin.errors_summary && plugin.errors_summary.errors_24h > 0
                ? "text-red-400 hover:underline"
                : "text-muted-foreground hover:text-foreground",
            )}
            title="Open logs filtered to this job"
          >
            Logs <ArrowRight className="w-3 h-3" />
          </a>
          {plugin.plugin_id && (
            <a
              href={`/plugin/${plugin.plugin_id}/settings`}
              className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 px-1"
              title="Open plugin settings"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="bg-secondary/20 border-t border-border/50 px-4 py-3 space-y-3">
          {(plugin.running.length > 0 || plugin.queued.length > 0) && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1.5">
                In flight
              </p>
              <div className="space-y-1">
                {plugin.running.map((r) => (
                  <InFlightRow
                    key={r.id}
                    item={r}
                    nowMs={nowMs}
                    kind="running"
                    onStopRun={onStopRun}
                    actionInFlight={actionInFlight}
                  />
                ))}
                {plugin.queued.map((r) => (
                  <InFlightRow
                    key={r.id}
                    item={r}
                    nowMs={nowMs}
                    kind="queued"
                    onStopRun={onStopRun}
                    actionInFlight={actionInFlight}
                  />
                ))}
              </div>
            </div>
          )}

          {plugin.recent_runs.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1.5">
                Recent runs (last 12h)
              </p>
              <div className="space-y-0.5">
                {plugin.recent_runs.slice(0, 10).map((r) => (
                  <RecentRunRow
                    key={r.id}
                    run={r}
                    highlight={r.id === highlightRunId}
                    anchorRef={
                      r.id === highlightRunId ? highlightAnchorRef : undefined
                    }
                  />
                ))}
              </div>
              {plugin.recent_runs.length > 10 && (
                <p className="text-[10px] text-muted-foreground mt-1">
                  Showing 10 of {plugin.recent_runs.length} runs — open Logs ↗ for the full history.
                </p>
              )}
            </div>
          )}

          {plugin.errors_summary?.last_error && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-red-400 font-semibold mb-1.5">
                Most recent error
              </p>
              <p
                className="text-[11px] font-mono-deck text-red-400 whitespace-pre-wrap break-words bg-red-500/5 border border-red-500/20 rounded px-2 py-1.5"
                title={plugin.errors_summary.last_error}
              >
                {plugin.errors_summary.last_error}
              </p>
              {plugin.errors_summary.last_error_at && (
                <p className="text-[10px] text-muted-foreground mt-1">
                  {formatRelativeTime(plugin.errors_summary.last_error_at)} ·{" "}
                  {formatAbsoluteTime(plugin.errors_summary.last_error_at)}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InFlightRow({
  item,
  nowMs,
  kind,
  onStopRun,
  actionInFlight,
}: {
  item: NowItem;
  nowMs: number;
  kind: "running" | "queued";
  onStopRun: (runId: number, force: boolean) => void;
  actionInFlight: string | null;
}) {
  const elapsed = Math.max(0, nowMs - Date.parse(item.started_at));
  // v0.9.11.16.4: pick stop mode based on this run's heartbeat. Worker
  // dead (heartbeat stale) → force; alive → cooperative.
  const useForce = kind === "running" && item.worker_alive === false;
  return (
    <div className="flex items-center gap-2 text-[11px]">
      {kind === "running" ? (
        <Loader2 className={cn("w-3 h-3 shrink-0", item.worker_alive === false ? "text-red-400" : "text-blue-400 animate-spin")} />
      ) : (
        <Hourglass className="w-3 h-3 text-yellow-400 shrink-0" />
      )}
      <span className="font-mono-deck text-muted-foreground tabular-nums shrink-0 w-10">
        #{item.id}
      </span>
      <span
        className={cn(
          "font-mono-deck shrink-0 w-16",
          kind === "running" ? "text-blue-400" : "text-yellow-400",
        )}
      >
        {item.status}
      </span>
      <span className="font-mono-deck text-muted-foreground tabular-nums shrink-0 w-20">
        {fmtDuration(elapsed)}
      </span>
      {kind === "running" && (
        <span
          className={cn(
            "text-[10px] font-mono-deck shrink-0 px-1.5 py-0.5 rounded",
            item.worker_alive
              ? "text-green-400 bg-green-500/10"
              : item.worker_alive === false
              ? "text-red-400 bg-red-500/10"
              : "text-muted-foreground bg-secondary/40",
          )}
          title={
            item.heartbeat_at
              ? `Last heartbeat ${formatAbsoluteTime(item.heartbeat_at)}`
              : "No heartbeat recorded"
          }
        >
          {item.worker_alive
            ? `worker live · ${item.heartbeat_age_sec ?? "?"}s ago`
            : item.worker_alive === false
            ? `worker dead · ${item.heartbeat_age_sec != null ? fmtDuration(item.heartbeat_age_sec * 1000) : "no beat"} ago`
            : "no liveness data"}
        </span>
      )}
      <span
        className="text-muted-foreground flex-1 truncate"
        title={formatAbsoluteTime(item.started_at)}
      >
        started {formatRelativeTime(item.started_at)}
      </span>
      {useForce ? (
        <button
          onClick={() => onStopRun(item.id, true)}
          disabled={actionInFlight === `cancel-${item.id}-force`}
          className="text-[10px] px-1.5 py-0.5 rounded border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center gap-1 disabled:opacity-50"
          title="Worker confirmed dead — force-mark cancelled"
        >
          <AlertOctagon className="w-2.5 h-2.5" />
          Force stop
        </button>
      ) : (
        <button
          onClick={() => onStopRun(item.id, false)}
          disabled={actionInFlight === `cancel-${item.id}-soft`}
          className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-secondary text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
          title="Cooperative cancel — worker exits at next checkpoint"
        >
          <Square className="w-2.5 h-2.5" />
          Stop
        </button>
      )}
    </div>
  );
}

function RecentRunRow({
  run,
  highlight,
  anchorRef,
}: {
  run: RecentItem;
  highlight?: boolean;
  anchorRef?: React.MutableRefObject<HTMLDivElement | null>;
}) {
  const tone =
    run.status === "success"
      ? "text-green-400"
      : run.status === "error" || run.status === "timeout"
      ? "text-red-400"
      : "text-muted-foreground";
  const Icon =
    run.status === "success"
      ? CheckCircle2
      : run.status === "error" || run.status === "timeout"
      ? XCircle
      : run.status === "paused"
      ? PauseCircle
      : CheckCircle2;
  return (
    <div
      ref={anchorRef}
      className={cn(
        "flex items-center gap-2 text-[11px] rounded px-1 py-0.5",
        highlight && "ring-1 ring-amber-400/60 bg-amber-400/5",
      )}
    >
      <Icon className={cn("w-3 h-3 shrink-0", tone)} />
      <span
        className="font-mono-deck text-muted-foreground tabular-nums shrink-0 w-24"
        title={formatAbsoluteTime(run.started_at)}
      >
        {formatRelativeTime(run.started_at)}
      </span>
      <span className={cn("font-mono-deck shrink-0 w-14", tone)}>{run.status}</span>
      <span className="font-mono-deck text-muted-foreground shrink-0 w-16 tabular-nums">
        {fmtDuration(run.duration_ms)}
      </span>
      {run.error_short ? (
        <span className="font-mono-deck text-red-400 truncate flex-1" title={run.error_short}>
          {run.error_short}
        </span>
      ) : (
        <span className="flex-1" />
      )}
    </div>
  );
}
