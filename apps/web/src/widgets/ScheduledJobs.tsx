import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle, AlertTriangle, XCircle, Copy, Check, Info, Play } from "lucide-react";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import JobLiveProgress from "./JobLiveProgress";

const API = import.meta.env.VITE_API_URL ?? "";

interface Job {
  id: string;
  name: string;
  description: string;
  owner?: string;                       // "Core" | "Plugin: Hello Nousviz" etc.
  command: string;
  recommended_schedule: string;
  recommended_label: string;
  last_run: string | null;
  last_run_label: string;
  status: "ok" | "stale" | "never";
  cron_active: boolean;
  cron_source?: "pm2" | "crontab" | "manifest" | "override" | null;
  sources?: { slug: string; name: string; total: number; last_scraped: string | null }[];
  // P108: next scheduled firing time computed server-side from croniter
  next_run_at?: string | null;
  // B150 (v0.9.3.2): plugin scheduler state. Present only for plugin rows.
  scheduler?: {
    cron_expression: string;
    cron_source: string;
    next_fire_at: string | null;
    last_enqueued_at: string | null;
    last_run_id: number | null;
    last_error: string | null;
    age_sec: number | null;
  } | null;
}

function isPluginRow(job: Job): boolean {
  return job.id.endsWith("-sync");
}

function pluginSlug(job: Job): string {
  return job.id.replace(/-sync$/, "");
}

interface CrontabEntry {
  schedule: string;
  command: string;
}

type CronSource = "pm2" | "crontab" | "both" | "none";

// Left-gutter icon: green check for ok, yellow warning for overdue,
// grey X for never-run. The "overdue" signal uses the backend's existing
// `status: stale` classification (2× the declared schedule) but labels
// it "Overdue" in the UI — "stale" was jargon that wasn't clear to operators.
const STATUS_CONFIG = {
  ok:    { icon: CheckCircle,    color: "text-green-400",          bg: "bg-green-500/10" },
  stale: { icon: AlertTriangle,  color: "text-yellow-400",         bg: "bg-yellow-500/10" },
  never: { icon: XCircle,        color: "text-muted-foreground",   bg: "bg-secondary" },
};

/**
 * Short title-case label for the schedule status pill.
 * Consistent casing with the topbar health dropdown — no more lowercase
 * "scheduled" next to capitalised neighbours.
 */
function scheduleLabel(job: Job): string {
  if (job.status === "stale") return "Overdue";
  if (!job.cron_active) {
    return job.recommended_schedule ? "Scheduled" : "Manual";
  }
  return "Active";
}

function scheduleLabelClasses(job: Job): string {
  if (job.status === "stale") {
    return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
  }
  if (job.cron_active) {
    return "bg-green-500/15 text-green-400 border-green-500/30";
  }
  return "bg-blue-500/10 text-blue-400 border-blue-500/20";
}

export default function ScheduledJobs() {
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [, setCrontab] = useState<CrontabEntry[]>([]);
  const [hasCrontab, setHasCrontab] = useState(false);
  const [cronSource, setCronSource] = useState<CronSource>("none");
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  // B209 (v0.9.6.1): banner shown when ?run_id=<id> arrives but no job's
  // last run matches (i.e. the operator clicked through to an older run).
  const [olderRunBanner, setOlderRunBanner] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      const r = await apiFetch(`${API}/api/jobs`);
      const data = await r.json();
      setJobs(data.jobs || []);
      setCrontab(data.crontab || []);
      setHasCrontab(!!data.has_crontab);
      setCronSource((data.cron_source as CronSource) || "none");
    } catch {
      /* keep previous state */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
    // P108/P109 UI polish: auto-refresh every 30s so next_run_at counts
    // down live and cron_active changes show up without a manual reload.
    const timer = setInterval(loadJobs, 30_000);
    return () => clearInterval(timer);
  }, [loadJobs]);

  // B209: deep-link from /system/logs `run` chip → /system/jobs?run_id=<id>.
  // After jobs load, find the row whose scheduler.last_run_id matches and
  // auto-expand it. If no match (run_id is older than each job's latest),
  // show a banner pointing the operator at the per-plugin history.
  useEffect(() => {
    const target = searchParams.get("run_id");
    if (!target || !jobs.length) return;
    const numeric = parseInt(target, 10);
    if (!Number.isFinite(numeric)) return;
    const match = jobs.find((j) => j.scheduler?.last_run_id === numeric);
    if (match) {
      setExpandedId(match.id);
      setOlderRunBanner(null);
    } else {
      setOlderRunBanner(
        `Run #${target} is older than each job's latest run. Showing all jobs — open the relevant plugin to see history.`,
      );
    }
  }, [searchParams, jobs]);

  const copyCommand = (id: string, cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // P108 UI: manually trigger a job via /api/jobs/{id}/fire-now.
  // B205 (v0.9.6): handle 409 (active run) by auto-expanding the row so the
  // operator sees the live progress card instead of a "fire now failed" toast.
  const fireNow = useCallback(async (jobId: string) => {
    setActionInFlight(jobId);
    setActionMessage(null);
    try {
      const r = await apiFetch(`${API}/api/jobs/${jobId}/fire-now`, {
        method: "POST",
      });
      if (r.status === 409) {
        // Active-run guard: open the row's expansion so live progress shows.
        setExpandedId(jobId);
        setActionMessage(`Sync already running for ${jobId} — see live progress below.`);
        loadJobs();
      } else if (!r.ok) {
        const body = await r.json().catch(() => ({} as { detail?: string }));
        setActionMessage(
          `Fire now failed (${r.status}): ${body?.detail || "unknown error"}`
        );
      } else {
        const data = await r.json().catch(() => ({} as { status?: string }));
        if (data?.status === "queued") {
          // Auto-expand so operator immediately sees the queued run.
          setExpandedId(jobId);
          setActionMessage(`Queued sync for ${jobId}.`);
        } else {
          setActionMessage(`Triggered ${jobId}.`);
        }
        loadJobs();
      }
    } catch (e) {
      setActionMessage(`Fire now error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setActionInFlight(null);
      setTimeout(() => setActionMessage(null), 4000);
    }
  }, [loadJobs]);

  if (loading) return <div className="p-4 text-muted-foreground text-sm">Loading jobs...</div>;

  // Build full crontab string for easy copy
  const fullCrontab = jobs
    .map(j => `# ${j.name} — ${j.recommended_label}\n${j.recommended_schedule} cd ~/nousviz && .venv/bin/python3 ${j.command} >> logs/${j.id}.log 2>&1`)
    .join("\n\n");

  const isPm2Deploy = cronSource === "pm2" || cronSource === "both";

  return (
    <div className="space-y-4">
      {/* P108 UI: transient toast for fire-now outcome */}
      {actionMessage && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg px-4 py-2">
          <p className="text-xs text-blue-300">{actionMessage}</p>
        </div>
      )}

      {/* B209: banner shown when arriving via /system/logs run-chip and the
          run_id is older than each job's latest run. */}
      {olderRunBanner && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-2 flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-300 flex-1">{olderRunBanner}</p>
          <button
            onClick={() => setOlderRunBanner(null)}
            className="text-amber-400/60 hover:text-amber-300 text-[10px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Status banner — only show "no cron" warning on bare-metal deploys without PM2 */}
      {cronSource === "none" && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-4 py-3 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-foreground font-medium">No cron jobs configured</p>
            <p className="text-xs text-muted-foreground mt-1">
              Data syncs are running manually. Set up cron jobs to keep data fresh automatically.{" "}
              <a
                href="/docs/plugin-sync-scheduling"
                className="underline hover:text-foreground"
              >
                Set up scheduling →
              </a>
            </p>
          </div>
        </div>
      )}

      {/* B150 (v0.9.3.2): split the deploy note in two — plugin scheduling
          went through the manifest-driven scheduler in v0.9.3 (B147),
          while core jobs (alert-runner, health-monitor) still use pm2's
          cron_restart. Show both when both are in play. */}
      {isPm2Deploy && (
        <div className="bg-secondary/40 border border-border rounded-lg px-4 py-3 flex items-start gap-3">
          <Info className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p className="text-sm text-foreground font-medium">How scheduling works</p>
            <p className="text-xs text-muted-foreground">
              <span className="text-foreground">Plugin syncs</span> are scheduled by NousViz from each plugin&apos;s{" "}
              <code className="font-mono-deck bg-secondary px-1 rounded">plugin.yaml</code>. To change a plugin&apos;s schedule, open its{" "}
              <span className="text-foreground">Settings tab → Sync schedule</span> and save an override.
            </p>
            <p className="text-xs text-muted-foreground">
              <span className="text-foreground">Core jobs</span> (alert runner, health monitor) run under PM2.
              To edit one, update its{" "}
              <code className="font-mono-deck bg-secondary px-1 rounded">cron_restart</code> in{" "}
              <code className="font-mono-deck bg-secondary px-1 rounded">ecosystem.config.js</code> and run{" "}
              <code className="font-mono-deck bg-secondary px-1 rounded">pm2 reload ecosystem.config.js --update-env</code>.
            </p>
          </div>
        </div>
      )}
      {hasCrontab && (
        <p className="text-[11px] text-muted-foreground">
          Schedules detected from {cronSource === "both" ? "PM2 and the system crontab" : "the system crontab"}.
        </p>
      )}

      {/* Job cards */}
      <div className="space-y-3">
        {jobs.map(job => {
          const cfg = STATUS_CONFIG[job.status];
          const StatusIcon = cfg.icon;
          const expanded = expandedId === job.id;

          return (
            <div
              key={job.id}
              className="bg-card border border-border rounded-lg overflow-hidden"
            >
              <button
                onClick={() => setExpandedId(expanded ? null : job.id)}
                className="w-full px-4 py-3 flex items-center gap-4 text-left hover:bg-secondary/20 transition-colors"
              >
                <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center shrink-0", cfg.bg)}>
                  <StatusIcon className={cn("w-4.5 h-4.5", cfg.color)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-sm font-medium text-foreground">{job.name}</h4>
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full border",
                      scheduleLabelClasses(job),
                    )}>
                      {scheduleLabel(job)}
                    </span>
                    {job.owner && (
                      <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 rounded-full bg-secondary/50 border border-border">
                        {job.owner}
                      </span>
                    )}
                  </div>
                  <p
                    className="text-xs text-muted-foreground mt-0.5"
                    title={job.last_run ? formatAbsoluteTime(job.last_run) : undefined}
                  >
                    {job.last_run ? `Last run ${formatRelativeTime(job.last_run)}` : "Never run"}
                    {!job.cron_active && isPluginRow(job) && (
                      <>
                        {" · "}
                        <a
                          href={`/plugin/${pluginSlug(job)}/settings`}
                          onClick={(e) => e.stopPropagation()}
                          className="underline hover:text-foreground"
                        >
                          Set up scheduling →
                        </a>
                      </>
                    )}
                    {/* B150 (v0.9.3.2): show scheduler error inline when the
                        registry has a last_error (e.g. invalid cron). Operators
                        can fix it via the Settings tab → Sync schedule. */}
                    {isPluginRow(job) && job.scheduler?.last_error && (
                      <>
                        {" · "}
                        <span className="text-yellow-400">
                          Schedule error: {job.scheduler.last_error}
                        </span>
                      </>
                    )}
                  </p>
                  {job.status === "stale" && job.last_run && (
                    <p className="text-[11px] text-yellow-400 mt-0.5 flex items-start gap-1.5">
                      <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>
                        Overdue — expected to run {job.recommended_label.toLowerCase()}, but last ran {formatRelativeTime(job.last_run)}.{" "}
                        {job.cron_active ? (
                          "The scheduled run may be failing silently — check the server-side log file for this job."
                        ) : isPluginRow(job) ? (
                          <>
                            The NousViz scheduler hasn&apos;t registered this plugin yet, or it&apos;s reporting an error.{" "}
                            <a
                              href={`/plugin/${pluginSlug(job)}/settings`}
                              onClick={(e) => e.stopPropagation()}
                              className="underline hover:text-foreground"
                            >
                              Open Settings → Sync schedule
                            </a>
                            {" "}to inspect.
                          </>
                        ) : (
                          "Auto-sync isn't currently scheduled for this job. Configure it in ecosystem.config.js."
                        )}
                      </span>
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground font-mono-deck">{job.recommended_schedule}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{job.recommended_label}</p>
                    {job.next_run_at && (
                      <p
                        className="text-[10px] text-muted-foreground mt-0.5"
                        title={formatAbsoluteTime(job.next_run_at)}
                      >
                        Next: {formatRelativeTime(job.next_run_at)}
                      </p>
                    )}
                  </div>
                  {job.id.endsWith("-sync") && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        fireNow(job.id);
                      }}
                      disabled={actionInFlight === job.id}
                      className="flex items-center gap-1.5 text-[11px] px-2 py-1 rounded border border-border hover:bg-secondary/60 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Trigger this sync now"
                    >
                      {actionInFlight === job.id ? (
                        <>
                          <span className="inline-block w-3 h-3 rounded-full border-2 border-t-transparent border-muted-foreground animate-spin" />
                          <span>Firing…</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3" />
                          <span>Fire now</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </button>

              {expanded && (
                <div className="px-4 pb-4 border-t border-border/50 pt-3 space-y-3">
                  {/* B205 (v0.9.6): live progress for in-flight plugin syncs.
                      Returns null when nothing is running, so non-plugin
                      jobs and idle plugin rows skip rendering it entirely. */}
                  {isPluginRow(job) && <JobLiveProgress pluginSlug={pluginSlug(job)} />}

                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs text-muted-foreground flex-1">{job.description}</p>
                    {/* P114 v0.8.4: cross-link from Jobs row → Logs page
                        filtered to this plugin's sync events, scoped to
                        last_run if we have one. */}
                    {job.id.endsWith("-sync") && (
                      <a
                        href={
                          job.last_run
                            ? `/system/logs?source=sync&since=${encodeURIComponent(job.last_run)}`
                            : `/system/logs?source=sync`
                        }
                        onClick={(e) => e.stopPropagation()}
                        className="text-[11px] text-primary hover:underline whitespace-nowrap shrink-0"
                      >
                        View logs →
                      </a>
                    )}
                  </div>

                  {/* Command */}
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs font-mono-deck bg-secondary/50 border border-border rounded px-3 py-2 text-foreground overflow-x-auto">
                      {job.command}
                    </code>
                    <button
                      onClick={() => copyCommand(job.id, job.command)}
                      className="p-2 rounded border border-border hover:bg-secondary shrink-0"
                      title="Copy command"
                    >
                      {copiedId === job.id ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
                    </button>
                  </div>

                  {/* Crontab line */}
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">Crontab entry</p>
                    <p className="text-[10px] text-muted-foreground mb-1.5">
                      Add to your server's crontab with <code className="font-mono-deck bg-secondary px-1 rounded">crontab -e</code>. Replace <code className="font-mono-deck bg-secondary px-1 rounded">~/nousviz</code> with your install path.
                    </p>
                    <code className="block text-xs font-mono-deck bg-secondary/50 border border-border rounded px-3 py-2 text-muted-foreground overflow-x-auto whitespace-pre">
{`${job.recommended_schedule} cd ~/nousviz && .venv/bin/python3 ${job.command} >> logs/${job.id}.log 2>&1`}
                    </code>
                  </div>

                  {/* Source breakdown for complaints */}
                  {job.sources && job.sources.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">Sources</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        {job.sources.map(s => (
                          <div key={s.slug} className="bg-secondary/30 rounded px-3 py-2">
                            <p className="text-xs font-medium text-foreground">{s.name}</p>
                            <p className="text-xs font-mono-deck text-muted-foreground">
                              {s.total.toLocaleString()} complaints
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Full crontab block — only for bare-metal deploys without PM2.
          On PM2 deploys this block would install duplicate jobs alongside
          the PM2-managed ones already running (see B193 ticket body). */}
      {jobs.length > 0 && cronSource === "none" && (
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-sm font-medium text-foreground">All jobs — crontab block</h4>
            <button
              onClick={() => copyCommand("full-crontab", fullCrontab)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              {copiedId === "full-crontab" ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
              Copy all
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            On the server running NousViz, open your crontab with{" "}
            <code className="font-mono-deck bg-secondary/50 px-1.5 py-0.5 rounded">crontab -e</code>{" "}
            and paste the block below. Update <code className="font-mono-deck bg-secondary/50 px-1.5 py-0.5 rounded">~/nousviz</code> to match your install path.
          </p>
          <pre className="text-xs font-mono-deck bg-secondary/50 border border-border rounded px-3 py-3 text-muted-foreground overflow-x-auto whitespace-pre">
{fullCrontab}
          </pre>
        </div>
      )}
    </div>
  );
}
