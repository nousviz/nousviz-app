/**
 * Diagnostic findings panel (B272 / v0.9.11.18).
 *
 * Wraps GET /api/system/diagnostics. Renders at the top of the
 * Resources tab on /system/health, above the existing stat cards.
 *
 * Each finding card shows severity icon + title (collapsed); click to
 * expand for evidence + recommendation + affected list + action button.
 * Severity counters at the top filter the list when clicked.
 *
 * Phase 1 actions: `external` (link to a route) and `manual` (open a
 * modal with SQL/shell command + copy-to-clipboard). The Phase 2
 * `sql_with_confirmation` apply path is deferred.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  RefreshCw,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  Copy,
  Check,
  X,
  Bell,
} from "lucide-react";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

type Severity = "critical" | "warn" | "info";

interface FindingAffected {
  type: string;
  name: string;
  detail?: string | null;
}

interface FindingAction {
  type: "external" | "manual";
  label: string;
  url?: string | null;
  sql?: string | null;
  shell?: string | null;
}

interface Finding {
  id: string;
  severity: Severity;
  title: string;
  evidence: string;
  recommendation: string;
  affected: FindingAffected[];
  action?: FindingAction | null;
  detected_at: string;
  // B274 (v0.9.11.20): set when the diagnostic-alert bridge has
  // dispatched a webhook for this (finding_id, affected_key). Drives
  // the "alert sent N min ago" badge below.
  last_alerted_at?: string | null;
}

interface DiagnosticsResponse {
  collected_at: string;
  summary: { critical: number; warn: number; info: number };
  findings: Finding[];
}

const SEVERITY_META: Record<
  Severity,
  { label: string; icon: typeof AlertOctagon; tone: string; bg: string; border: string }
> = {
  critical: {
    label: "Critical",
    icon: AlertOctagon,
    tone: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
  },
  warn: {
    label: "Warning",
    icon: AlertTriangle,
    tone: "text-yellow-400",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
  },
  info: {
    label: "Info",
    icon: Info,
    tone: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
  },
};

export default function FindingsPanel() {
  const [data, setData] = useState<DiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<Severity | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [manualAction, setManualAction] = useState<FindingAction | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");

  const load = useCallback(async (fresh: boolean = false) => {
    setRefreshing(true);
    setError(null);
    try {
      const url = fresh ? "/api/system/diagnostics?fresh=true" : "/api/system/diagnostics";
      const r = await apiFetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as DiagnosticsResponse;
      setData(body);
    } catch (e) {
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

  const visibleFindings = useMemo(() => {
    if (!data) return [];
    if (!activeFilter) return data.findings;
    return data.findings.filter((f) => f.severity === activeFilter);
  }, [data, activeFilter]);

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      // Browsers without clipboard permission — leave the modal open
      // so the operator can select the text manually.
    }
  };

  if (loading && !data) {
    return (
      <div className="bg-card border border-border rounded-lg px-4 py-3 text-xs text-muted-foreground">
        Loading findings…
      </div>
    );
  }

  const summary = data?.summary || { critical: 0, warn: 0, info: 0 };
  const totalFindings = summary.critical + summary.warn + summary.info;

  return (
    <div className="space-y-3">
      {/* Header strip — counters + collected_at + refresh */}
      <div className="bg-card border border-border rounded-lg px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-display text-foreground">Findings</h3>
            {totalFindings === 0 ? (
              <span className="text-[11px] text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                No issues detected
              </span>
            ) : (
              <>
                {(["critical", "warn", "info"] as const).map((sev) => {
                  const count = summary[sev];
                  if (count === 0) return null;
                  const meta = SEVERITY_META[sev];
                  const Icon = meta.icon;
                  const isActive = activeFilter === sev;
                  return (
                    <button
                      key={sev}
                      onClick={() => setActiveFilter(isActive ? null : sev)}
                      className={cn(
                        "text-[10px] font-mono-deck flex items-center gap-1 px-1.5 py-0.5 rounded border tabular-nums transition-colors",
                        isActive
                          ? `${meta.bg} ${meta.tone} ${meta.border}`
                          : "bg-secondary text-muted-foreground border-border hover:text-foreground",
                      )}
                      title={`Filter to ${meta.label.toLowerCase()} only`}
                    >
                      <Icon className="w-2.5 h-2.5" />
                      {count} {meta.label}
                    </button>
                  );
                })}
                {activeFilter && (
                  <button
                    onClick={() => setActiveFilter(null)}
                    className="text-[10px] text-muted-foreground hover:text-foreground"
                  >
                    Clear filter
                  </button>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {data?.collected_at && (
              <span
                className="text-[10px] text-muted-foreground"
                title={formatAbsoluteTime(data.collected_at)}
              >
                {formatRelativeTime(data.collected_at)}
              </span>
            )}
            <button
              onClick={() => load(true)}
              disabled={refreshing}
              className="h-7 px-2 rounded-md bg-secondary text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
            >
              <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin")} />
              Refresh
            </button>
          </div>
        </div>
        {error && (
          <p className="text-[11px] text-red-400 mt-2 flex items-center gap-1.5">
            <X className="w-3 h-3" />
            Failed to load: {error}
          </p>
        )}
      </div>

      {/* Findings list (or empty state) */}
      {totalFindings === 0 && !error ? (
        <div className="bg-card border border-border rounded-lg px-4 py-6 text-center">
          <CheckCircle2 className="w-5 h-5 mx-auto mb-2 text-green-400 opacity-60" />
          <p className="text-xs text-muted-foreground">
            No issues detected against the 12 diagnostic rules.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {visibleFindings.map((f) => (
            <FindingCard
              key={f.id + ":" + f.affected.map((a) => a.name).join(",")}
              finding={f}
              expanded={expandedId === f.id}
              onToggle={() =>
                setExpandedId((prev) => (prev === f.id ? null : f.id))
              }
              onManualAction={(action) => setManualAction(action)}
            />
          ))}
        </div>
      )}

      {/* Manual-action modal (SQL / shell + copy) */}
      {manualAction && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
              <h3 className="text-sm font-display text-foreground">{manualAction.label}</h3>
              <button
                onClick={() => setManualAction(null)}
                className="h-7 w-7 rounded hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-auto px-4 py-3">
              <p className="text-[11px] text-muted-foreground mb-2">
                {manualAction.sql ? "SQL — copy and run as a Postgres superuser:" : "Shell command — run on the host:"}
              </p>
              <pre className="bg-secondary/40 border border-border rounded p-3 text-[11px] font-mono-deck text-foreground whitespace-pre-wrap break-all overflow-x-auto">
                {manualAction.sql || manualAction.shell}
              </pre>
            </div>
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border/50">
              <button
                onClick={() => handleCopy((manualAction.sql || manualAction.shell || ""))}
                className="h-8 px-3 rounded-md bg-blue-500 text-white text-xs hover:bg-blue-600 flex items-center gap-1.5"
              >
                {copyState === "copied" ? (
                  <>
                    <Check className="w-3 h-3" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy to clipboard
                  </>
                )}
              </button>
              <button
                onClick={() => setManualAction(null)}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Per-finding timeline strip (B273 v0.9.11.19) ────────────────────

interface FindingHistoryPoint {
  snapshot_at: string;
  present: boolean;
  severity?: string | null;
}

interface FindingHistoryResponse {
  finding_id: string;
  days: number;
  points: FindingHistoryPoint[];
  first_detected_at?: string | null;
}

function FindingTimeline({ findingId }: { findingId: string }) {
  const [history, setHistory] = useState<FindingHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch(
      `/api/system/diagnostics/history?id=${encodeURIComponent(findingId)}&days=30`,
    )
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as FindingHistoryResponse;
      })
      .then((body) => {
        if (cancelled) return;
        setHistory(body);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [findingId]);

  if (loading) {
    return (
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
          History (last 30 days)
        </p>
        <p className="text-[11px] text-muted-foreground">Loading timeline…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
          History (last 30 days)
        </p>
        <p className="text-[11px] text-red-400">Failed to load: {error}</p>
      </div>
    );
  }

  if (!history || history.points.length === 0) {
    return (
      <div>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
          History (last 30 days)
        </p>
        <p className="text-[11px] text-muted-foreground">
          No history yet. The first daily snapshot lands at 03:30 UTC.
        </p>
      </div>
    );
  }

  // Auto-text: "first detected: N days ago" or "today"
  let firstDetectedLabel = "Not detected in this window.";
  if (history.first_detected_at) {
    const ageMs = Date.now() - Date.parse(history.first_detected_at);
    const ageDays = Math.floor(ageMs / (24 * 60 * 60 * 1000));
    if (ageDays <= 0) {
      firstDetectedLabel = "First detected: today";
    } else {
      firstDetectedLabel = `First detected: ${ageDays} day${ageDays === 1 ? "" : "s"} ago`;
    }
  }

  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
        History (last {history.days} days)
      </p>
      <div className="flex items-center gap-px">
        {history.points.map((p) => (
          <FindingTimelineCell key={p.snapshot_at} point={p} />
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground mt-1.5">{firstDetectedLabel}</p>
    </div>
  );
}

function FindingTimelineCell({ point }: { point: FindingHistoryPoint }) {
  if (!point.present) {
    return (
      <span
        className="w-2 h-4 bg-secondary/40 rounded-sm"
        title={`${formatAbsoluteTime(point.snapshot_at)} — not detected`}
      />
    );
  }
  const sev = (point.severity ?? "info") as Severity;
  const meta = SEVERITY_META[sev] ?? SEVERITY_META.info;
  const cellTone =
    sev === "critical"
      ? "bg-red-500/80"
      : sev === "warn"
      ? "bg-yellow-500/80"
      : "bg-blue-500/80";
  return (
    <span
      className={cn("w-2 h-4 rounded-sm", cellTone)}
      title={`${formatAbsoluteTime(point.snapshot_at)} — ${meta.label}`}
    />
  );
}


// ── Finding card ────────────────────────────────────────────────────

function FindingCard({
  finding,
  expanded,
  onToggle,
  onManualAction,
}: {
  finding: Finding;
  expanded: boolean;
  onToggle: () => void;
  onManualAction: (action: FindingAction) => void;
}) {
  const meta = SEVERITY_META[finding.severity];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "bg-card border rounded-lg overflow-hidden",
        meta.border,
      )}
    >
      <button
        onClick={onToggle}
        className="w-full px-4 py-2.5 flex items-start gap-3 text-left hover:bg-secondary/20 transition-colors"
      >
        <div className={cn("h-7 w-7 rounded-md flex items-center justify-center shrink-0", meta.bg)}>
          <Icon className={cn("w-3.5 h-3.5", meta.tone)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("text-[10px] font-mono-deck font-semibold uppercase", meta.tone)}>
              {meta.label}
            </span>
            <span className="text-sm text-foreground">{finding.title}</span>
            {/* B274 (v0.9.11.20): alert-sent badge — surfaces when the
                bridge has dispatched a webhook for this finding. */}
            {finding.last_alerted_at && (
              <span
                className="text-[10px] font-mono-deck flex items-center gap-1 px-1.5 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400"
                title={`Webhook alert sent at ${formatAbsoluteTime(finding.last_alerted_at)}`}
              >
                <Bell className="w-2.5 h-2.5" />
                alert sent {formatRelativeTime(finding.last_alerted_at)}
              </span>
            )}
          </div>
          {!expanded && finding.affected.length > 0 && (
            <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
              {finding.affected.slice(0, 3).map((a) => a.name).join(" · ")}
              {finding.affected.length > 3 && ` · +${finding.affected.length - 3} more`}
            </p>
          )}
        </div>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-2" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-2" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border/50 px-4 py-3 space-y-3 bg-secondary/20">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
              Evidence
            </p>
            <p className="text-[11px] text-foreground whitespace-pre-wrap leading-relaxed">
              {finding.evidence}
            </p>
          </div>

          {finding.affected.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
                Affected ({finding.affected.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {finding.affected.map((a, i) => (
                  <span
                    key={`${a.type}-${a.name}-${i}`}
                    className="text-[10px] font-mono-deck bg-secondary/40 border border-border rounded px-1.5 py-0.5"
                    title={a.detail ?? undefined}
                  >
                    <span className="text-muted-foreground">{a.type}:</span>{" "}
                    <span className="text-foreground">{a.name}</span>
                    {a.detail && <span className="text-muted-foreground"> · {a.detail}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
              Recommendation
            </p>
            <p className="text-[11px] text-foreground whitespace-pre-wrap leading-relaxed">
              {finding.recommendation}
            </p>
          </div>

          {finding.action && (
            <div className="pt-1">
              {finding.action.type === "external" && finding.action.url ? (
                <a
                  href={finding.action.url}
                  className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                >
                  {finding.action.label}
                  <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <button
                  onClick={() => onManualAction(finding.action!)}
                  className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded border border-border bg-secondary/40 hover:bg-secondary text-foreground"
                >
                  {finding.action.label}
                  <Copy className="w-3 h-3" />
                </button>
              )}
            </div>
          )}

          {/* B273 v0.9.11.19: 30-day presence timeline. Lazy-loads when
              this card is expanded so we don't fan out N parallel
              history requests for every finding on initial render. */}
          <FindingTimeline findingId={finding.id} />

          <p className="text-[10px] text-muted-foreground">
            Rule: <code className="font-mono-deck">{finding.id}</code>
          </p>
        </div>
      )}
    </div>
  );
}
