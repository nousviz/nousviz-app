import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import {
  evaluateChecks,
  summarize,
  labelForLevel,
  countByStatus,
  type HealthData,
  type ConfigData,
  type HealthCheck,
} from "@/lib/health-checks";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Info, ChevronRight } from "lucide-react";
import LogsPanel from "@/components/settings/LogsPanel";
import CheckAction from "@/components/health/CheckAction";
import SslSetupModal from "@/components/SslSetupModal";
import SetupWizard from "@/components/SetupWizard";
import ResourcesPanel from "@/components/system/ResourcesPanel";
import JobsDashboard from "@/components/system/JobsDashboard";
import SystemTabBar, { type SystemTabId } from "@/components/system/SystemTabBar";

// Local subset — only the tabs HealthOverviewPage actually renders inline.
// Permissions and Users live in their own pages but appear in the SystemTabBar.
const HANDLED_TABS = ["health", "resources", "jobs", "logs"] as const;
type HealthTab = typeof HANDLED_TABS[number];

interface HealthLogEntry {
  id: number;
  level: string;
  checks: { id: string; status: string; label: string; detail: string }[];
  postgres_ok: boolean;
  tables: number;
  version: string;
  created_at: string;
}

const AUTO_REFRESH_MS = 30_000;

function StatusIcon({ status, className }: { status: string; className?: string }) {
  if (status === "pass" || status === "info") return <CheckCircle2 className={cn("w-4 h-4 text-green-400 shrink-0", className)} />;
  if (status === "warn") return <AlertTriangle className={cn("w-4 h-4 text-yellow-400 shrink-0", className)} />;
  return <XCircle className={cn("w-4 h-4 text-red-400 shrink-0", className)} />;
}

function LevelBadge({ level, label }: { level: string; label?: string }) {
  const styles: Record<string, string> = {
    healthy: "bg-green-500/10 text-green-400",
    warning: "bg-yellow-500/10 text-yellow-400",
    critical: "bg-red-500/10 text-red-400",
    loading: "bg-secondary text-muted-foreground",
  };
  const displayLabel = label || labelForLevel(level);
  return (
    <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-mono-deck", styles[level] || styles.warning)}>
      {displayLabel}
    </span>
  );
}

// Legacy row — used for per-snapshot history display (the "expanded
// history entry" list). Keeps the flat, non-expandable shape because
// historical snapshots are a different UX from current state.
function CheckRow({ check }: { check: { id: string; status: string; label: string; detail: string } }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-secondary/30">
      <StatusIcon status={check.status} />
      <span className="text-sm text-foreground font-body flex-1">{check.label}</span>
      <span className="text-xs text-muted-foreground font-mono-deck">{check.detail}</span>
    </div>
  );
}

// Order inside a group: failing first, then warn, then pass/info.
function sortBySeverity(a: HealthCheck, b: HealthCheck): number {
  const rank = (s: string) =>
    s === "fail" ? 0 : s === "warn" ? 1 : s === "info" ? 2 : 3;
  return rank(a.status) - rank(b.status);
}

// Expandable current-state row used in the System Status > Health tab
// (P115 v0.8.4). Clicking toggles an inline panel that shows `expanded`
// key/value details (version, table count, SSL issuer, etc.).
function ExpandableCheckRow({
  check,
  expanded,
  onToggle,
  onSslSetup,
  onSetupWizard,
}: {
  check: HealthCheck;
  expanded: boolean;
  onToggle: () => void;
  onSslSetup: () => void;
  onSetupWizard: () => void;
}) {
  const hasExpanded = !!check.expanded && check.expanded.length > 0;
  return (
    <div className="rounded-lg bg-secondary/30 overflow-hidden">
      <button
        type="button"
        onClick={hasExpanded ? onToggle : undefined}
        disabled={!hasExpanded}
        className={cn(
          "w-full flex items-center gap-3 px-3 py-2 text-left",
          hasExpanded ? "hover:bg-secondary/60 transition-colors cursor-pointer" : "cursor-default",
        )}
      >
        {hasExpanded ? (
          <ChevronRight
            className={cn(
              "w-3.5 h-3.5 text-muted-foreground shrink-0 transition-transform",
              expanded && "rotate-90",
            )}
          />
        ) : (
          <span className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
        )}
        <StatusIcon status={check.status} />
        <span className="text-sm text-foreground font-body flex-1">{check.label}</span>
        <span className="text-xs text-muted-foreground font-mono-deck mr-2">{check.detail}</span>
        {check.action && (
          <CheckAction
            action={check.action}
            onSslSetup={onSslSetup}
            onSetupWizard={onSetupWizard}
          />
        )}
      </button>
      {expanded && hasExpanded && (
        <div className="px-5 pb-3 pt-1 border-t border-border/50 space-y-1">
          {check.expanded!.map(e => (
            <div key={e.label} className="flex items-baseline justify-between gap-3">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground w-24 shrink-0">
                {e.label}
              </span>
              <span className="text-xs font-mono-deck text-foreground break-all text-right">
                {e.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const GROUP_META: Record<"services" | "security" | "configuration", { label: string; description: string }> = {
  services:      { label: "Services",      description: "Databases and utilities the platform talks to." },
  security:      { label: "Security",      description: "Authentication, encryption, and transport." },
  configuration: { label: "Configuration", description: "Platform settings that aren't security-critical." },
};

function GroupSection({
  group,
  checks,
  expandedId,
  onToggle,
  onSslSetup,
  onSetupWizard,
}: {
  group: "services" | "security" | "configuration";
  checks: HealthCheck[];
  expandedId: string | null;
  onToggle: (id: string) => void;
  onSslSetup: () => void;
  onSetupWizard: () => void;
}) {
  if (checks.length === 0) return null;
  const meta = GROUP_META[group];
  const sorted = [...checks].sort(sortBySeverity);
  return (
    <div className="bg-card rounded-lg border border-border p-5 space-y-3">
      <div>
        <h3 className="font-display text-sm text-foreground">{meta.label}</h3>
        <p className="text-[11px] text-muted-foreground mt-0.5">{meta.description}</p>
      </div>
      <div className="space-y-2">
        {sorted.map(c => (
          <ExpandableCheckRow
            key={c.id}
            check={c}
            expanded={expandedId === c.id}
            onToggle={() => onToggle(c.id)}
            onSslSetup={onSslSetup}
            onSetupWizard={onSetupWizard}
          />
        ))}
      </div>
    </div>
  );
}

export default function HealthOverviewPage() {
  // Tab state via path param — matches /settings/:tab convention.
  // Route is /system/:tab; App.tsx redirects bare /system and
  // /health-overview → /system/health.
  const { tab: urlTab } = useParams<{ tab?: string }>();
  const activeTab: HealthTab = HANDLED_TABS.some(t => t === urlTab)
    ? (urlTab as HealthTab)
    : "health";
  // Tab navigation handled by SystemTabBar; this page just renders the active section.

  const [liveChecks, setLiveChecks] = useState<HealthCheck[] | null>(null);
  const [liveLevel, setLiveLevel] = useState<"healthy" | "warning" | "critical" | "loading">("loading");
  const [liveVersion, setLiveVersion] = useState<string>("");
  const [liveTimestamp, setLiveTimestamp] = useState<string>("");
  const [liveError, setLiveError] = useState<string | null>(null);
  const [history, setHistory] = useState<HealthLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null);
  // P115: per-check inline expand (services, security, configuration rows)
  const [expandedCheckId, setExpandedCheckId] = useState<string | null>(null);
  // P115: timeline collapsed by default; reveals the 96-blob heatmap + per-check rows on demand
  const [showTimeline, setShowTimeline] = useState(false);
  // P115: CheckAction may trigger the SSL-setup modal or the setup wizard
  const [showSslModal, setShowSslModal] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const loadRef = useRef<(recordFresh?: boolean) => void>(() => {});

  const load = useCallback((recordFresh: boolean = false) => {
    setRefreshing(true);
    if (history.length === 0) setLoading(true);
    setLiveError(null);
    // `recordFresh` = true (manual Refresh button) triggers a fresh
    // /api/health/record server-side so the history gets a new row AND
    // live data picks up whatever just changed. Auto-refresh polls without
    // asking the server to write a new log row (the PM2 cron handles that).
    const recordPromise = recordFresh
      ? apiFetch("/api/health/record", { method: "POST" }).catch(() => null)
      : Promise.resolve(null);
    Promise.allSettled([
      recordPromise.then(() => apiFetch("/api/health").then(r => r.json() as Promise<HealthData>)),
      apiFetch("/api/health/config").then(r => r.json() as Promise<ConfigData>),
      apiFetch("/api/health/log?days=7&limit=100").then(r => r.json()).catch(() => ({ log: [] })),
    ]).then(results => {
      const [healthResult, configResult, logResult] = results;

      if (healthResult.status === "fulfilled" && configResult.status === "fulfilled") {
        const hData = healthResult.value;
        const cData = configResult.value;
        const checks = evaluateChecks(hData, cData);
        const { level } = summarize(checks);
        setLiveChecks(checks);
        setLiveLevel(level);
        setLiveVersion(hData?.version || "");
        setLiveTimestamp(hData?.timestamp || new Date().toISOString());
      } else {
        setLiveError("Live check failed — showing last logged snapshot");
        const log: HealthLogEntry[] = logResult.status === "fulfilled" ? (logResult.value.log || []) : [];
        if (log.length > 0) {
          const latest = log[0];
          setLiveChecks(
            latest.checks.map((c: HealthLogEntry["checks"][number]) => ({
              id: c.id,
              label: c.label,
              status: c.status as "pass" | "warn" | "fail",
              detail: c.detail,
            })),
          );
          setLiveLevel(latest.level as "healthy" | "warning" | "critical");
          setLiveVersion(latest.version || "");
          setLiveTimestamp(latest.created_at);
        } else {
          setLiveChecks([]);
          setLiveLevel("loading");
        }
      }

      const log = logResult.status === "fulfilled" ? (logResult.value.log || []) : [];
      setHistory(log);
      setLoading(false);
      setRefreshing(false);
    });
  }, [history.length]);

  loadRef.current = load;

  // Initial load + auto-refresh every 30s
  useEffect(() => {
    loadRef.current();
    const id = window.setInterval(() => loadRef.current(), AUTO_REFRESH_MS);
    return () => window.clearInterval(id);
  }, []);

  const liveCounts = liveChecks ? countByStatus(liveChecks) : { pass: 0, warn: 0, fail: 0 };

  return (
    <div className="max-w-[1000px] space-y-6">
      {/* B271 v0.9.11.13.1: shared SystemTabBar — same surface across
          all /system/* pages, matches the sidebar exactly. */}
      <SystemTabBar
        active={activeTab as SystemTabId}
        rightSlot={activeTab === "health" ? (
          <button
            onClick={() => loadRef.current(true)}
            disabled={refreshing}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 transition-colors disabled:opacity-50 mb-2"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            Refresh
          </button>
        ) : undefined}
      />

      {activeTab === "jobs" && <JobsDashboard />}
      {activeTab === "logs" && <LogsPanel />}
      {activeTab === "resources" && <ResourcesPanel />}

      {activeTab === "health" && (
        <>
      <div>
        <p className="text-sm text-muted-foreground font-body">System status and operator console.</p>
        <p className="text-[11px] text-muted-foreground mt-0.5">Refreshes automatically every 30 seconds.</p>
      </div>

      {/* Current status summary strip — live from /api/health + /api/health/config (B191) */}
      {liveChecks !== null && (
        <div className="bg-card rounded-lg border border-border px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="font-display text-sm text-foreground">Current Status</h3>
            {liveTimestamp && (
              <p className="text-[11px] text-muted-foreground mt-0.5" title={formatAbsoluteTime(liveTimestamp)}>
                Updated {formatRelativeTime(liveTimestamp)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <LevelBadge level={liveLevel} />
            {liveChecks.length > 0 && (
              <span className="text-[11px] text-muted-foreground font-mono-deck">
                <span className="text-green-400">{liveCounts.pass} Passing</span>
                {liveCounts.warn > 0 && <> · <span className="text-yellow-400">{liveCounts.warn} Warning{liveCounts.warn === 1 ? "" : "s"}</span></>}
                {liveCounts.fail > 0 && <> · <span className="text-red-400">{liveCounts.fail} Failing</span></>}
              </span>
            )}
            {liveVersion && (
              <span className="text-xs font-mono-deck text-muted-foreground">v{liveVersion}</span>
            )}
          </div>
        </div>
      )}

      {liveError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-yellow-500/10 text-yellow-400 text-xs">
          <Info className="w-3.5 h-3.5 shrink-0" />
          <span>{liveError}</span>
        </div>
      )}

      {/* Grouped check rendering — P115 v0.8.4 */}
      {liveChecks !== null && liveChecks.length > 0 && (
        <>
          {(["services", "security", "configuration"] as const).map(group => {
            const groupChecks = liveChecks.filter(c => (c.group ?? "configuration") === group);
            return (
              <GroupSection
                key={group}
                group={group}
                checks={groupChecks}
                expandedId={expandedCheckId}
                onToggle={(id) => setExpandedCheckId(prev => prev === id ? null : id)}
                onSslSetup={() => setShowSslModal(true)}
                onSetupWizard={() => setShowWizard(true)}
              />
            );
          })}
        </>
      )}

      {liveChecks !== null && liveChecks.length === 0 && !loading && (
        <div className="bg-card rounded-lg border border-border p-5">
          <p className="text-sm text-muted-foreground">No health data available yet.</p>
        </div>
      )}

      {liveChecks === null && !loading && (
        <div className="bg-card rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="w-8 h-8 mx-auto mb-3 text-muted-foreground opacity-30" />
          <p className="text-sm text-muted-foreground mb-2">No health data yet.</p>
          <p className="text-xs text-muted-foreground">Health checks run every 5 minutes via PM2 cron. Data will appear here after the first check.</p>
        </div>
      )}

      {/* Timeline heatmap — collapsed by default in v0.8.4 (P115).
          Click "Show timeline" to reveal both the overall heatmap and
          the per-check timeline. Keeps the page clean by default. */}
      {history.length > 0 && !showTimeline && (
        <div className="bg-card rounded-lg border border-border px-5 py-3 flex items-center justify-between">
          <div>
            <p className="text-xs text-foreground font-body">History</p>
            <p className="text-[11px] text-muted-foreground">
              {history.length} snapshots in the last 7 days
            </p>
          </div>
          <button
            onClick={() => setShowTimeline(true)}
            className="text-[11px] text-primary hover:underline"
          >
            Show timeline
          </button>
        </div>
      )}

      {history.length > 0 && showTimeline && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm text-foreground">Timeline</h3>
            <button
              onClick={() => setShowTimeline(false)}
              className="text-[11px] text-muted-foreground hover:text-foreground"
            >
              Hide
            </button>
          </div>
          <div className="flex items-end gap-px h-8">
            {history.slice(0, 96).reverse().map((h) => {
              const color = h.level === "healthy" ? "bg-green-400" : h.level === "warning" ? "bg-yellow-400" : "bg-red-400";
              return (
                <div key={h.id} className={cn("flex-1 min-w-[2px] rounded-sm cursor-pointer hover:opacity-70", color)}
                  style={{ height: "100%" }}
                  title={`${formatAbsoluteTime(h.created_at)} — ${labelForLevel(h.level)}`}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>{history.length > 0 ? formatRelativeTime(history[Math.min(history.length - 1, 95)].created_at) : ""}</span>
            <span>Now</span>
          </div>

          {/* Per-check timelines */}
          {(() => {
            const checkIds = [...new Set(history.flatMap(h => (h.checks || []).map(c => c.id)))];
            if (checkIds.length === 0) return null;
            return (
              <div className="space-y-2 mt-4">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Per-check timeline</p>
                {checkIds.map(cid => {
                  const label = history.find(h => h.checks?.find(c => c.id === cid))?.checks?.find(c => c.id === cid)?.label || cid;
                  return (
                    <div key={cid} className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground w-24 truncate shrink-0">{label}</span>
                      <div className="flex items-center gap-px flex-1 h-3">
                        {history.slice(0, 96).reverse().map((h) => {
                          const check = (h.checks || []).find(c => c.id === cid);
                          const status = check?.status || "pass";
                          const detail = check?.detail || "";
                          const color = (status === "pass" || status === "info") ? "bg-green-400/60" : status === "warn" ? "bg-yellow-400" : "bg-red-400";
                          return <div key={h.id} className={cn("flex-1 min-w-[2px] rounded-sm cursor-pointer hover:opacity-70", color)} style={{ height: "100%" }}
                            title={`${formatAbsoluteTime(h.created_at)} — ${status}${detail ? `: ${detail}` : ""}`} />;
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      )}

      {/* History list */}
      {history.length > 0 && (
        <div className="bg-card rounded-lg border border-border">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <h3 className="font-display text-sm text-foreground">History (last 7 days)</h3>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-muted-foreground">{history.length} entries</span>
            </div>
          </div>
          <div className="divide-y divide-border max-h-[32rem] overflow-y-auto">
            {history.map(h => {
              const expanded = expandedHistoryId === h.id;
              const counts = countByStatus(h.checks || []);
              return (
                <div key={h.id}>
                  <button
                    type="button"
                    onClick={() => setExpandedHistoryId(expanded ? null : h.id)}
                    className="w-full px-5 py-2.5 flex items-center gap-4 text-left hover:bg-secondary/20 transition-colors"
                  >
                    <ChevronRight
                      className={cn(
                        "w-3.5 h-3.5 text-muted-foreground transition-transform shrink-0",
                        expanded && "rotate-90",
                      )}
                    />
                    <LevelBadge level={h.level} />
                    <span
                      className="text-xs font-mono-deck text-muted-foreground flex-1"
                      title={formatAbsoluteTime(h.created_at)}
                    >
                      {formatRelativeTime(h.created_at)}
                    </span>
                    {h.checks && h.checks.length > 0 && (
                      <span className="text-[11px] font-mono-deck">
                        <span className="text-green-400">{counts.pass} Passing</span>
                        {counts.warn > 0 && <span className="text-yellow-400"> · {counts.warn} Warning{counts.warn === 1 ? "" : "s"}</span>}
                        {counts.fail > 0 && <span className="text-red-400"> · {counts.fail} Failing</span>}
                      </span>
                    )}
                    <span className="text-xs font-mono-deck text-muted-foreground w-20 text-right">v{h.version}</span>
                  </button>

                  {expanded && (
                    <div className="px-5 pb-4 pt-1 space-y-2 bg-secondary/20">
                      {h.checks && h.checks.length > 0 ? (
                        h.checks.map(c => <CheckRow key={c.id} check={c} />)
                      ) : (
                        <p className="text-xs text-muted-foreground py-2">
                          No per-check data for this snapshot (written before the per-check schema landed).
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* P115 v0.8.4: modals for CheckAction button triggers.
          SSL setup and the setup wizard render only when a failing check
          exposes the corresponding action and the operator clicks it. */}
      {showSslModal && (
        <SslSetupModal onClose={() => setShowSslModal(false)} />
      )}
      {showWizard && (
        <SetupWizard onClose={() => setShowWizard(false)} />
      )}
        </>
      )}
    </div>
  );
}
