import { apiFetch } from "@/lib/api";
import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { useBootCoordinator } from "@/components/layout/BootCoordinator";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Database, Plug, Bell, RefreshCw,
  CheckCircle2, AlertTriangle, XCircle,
  ArrowRight, Activity, Clock, Shield,
} from "lucide-react";
import { cn, formatRelativeTime, formatAbsoluteTime, formatStatus } from "@/lib/utils";
import {
  evaluateChecks,
  summarize,
  labelForLevel,
  countByStatus,
  type HealthData,
  type ConfigData,
} from "@/lib/health-checks";

// ── Types ────────────────────────────────────────────────────────────

interface LaunchpadData {
  recent_activity: ActivityEvent[];
  recent_data_changes: DataChange[];
  alerts_summary: AlertsSummary;
  health_snapshot: { level: string; checks: { id: string; status: string; label: string; detail: string }[]; version: string; created_at: string } | null;
  needs_attention: AttentionItem[];
  stats: { annotations?: number; fusions?: number; active_shares?: number };
}

interface ActivityEvent {
  action: string;
  page_path: string | null;
  plugin_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
  user_name: string | null;
}

interface DataChange {
  plugin_id: string;
  display_name?: string;
  last_sync: string | null;
  total_rows?: number;
  tables?: number;
}

interface AlertsSummary {
  total: number;
  enabled: number;
  triggered_24h: number;
  recent_triggers: { alert_name: string; plugin_id: string; triggered_at: string }[];
}

interface AttentionItem {
  type: string;
  severity: string;
  message: string;
  plugin_id?: string;
  share_id?: string;
  last_sync?: string;
  expires_at?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: string }) {
  if (status === "pass") return <CheckCircle2 className="w-3.5 h-3.5 text-green-400 shrink-0" />;
  if (status === "warn") return <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" />;
  return <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />;
}

function SectionCard({ title, icon: Icon, to, badge, children }: {
  title: string;
  icon: React.ElementType;
  to?: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-display text-sm text-foreground">{title}</h3>
          {badge && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-mono-deck">
              {badge}
            </span>
          )}
        </div>
        {to && (
          <Link to={to} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="text-xs text-muted-foreground py-2">{message}</p>;
}

const SETTINGS_LABELS: Record<string, string> = {
  email: "Configured SMTP",
  database: "Updated database settings",
};

function actionLabel(action: string, details?: Record<string, unknown> | null): string {
  if (action === "settings_update" && details?.setting) {
    return SETTINGS_LABELS[details.setting as string] || `Updated ${details.setting} settings`;
  }
  const email = details?.email as string | undefined;
  if (action === "user_register") return `User registered${email ? ` · ${email}` : ""}`;
  if (action === "user_invite") return `Invited user${email ? ` · ${email}` : ""}`;
  if (action === "user_deactivate") return `Deactivated user${email ? ` · ${email}` : ""}`;
  if (action === "user_reactivate") return `Reactivated user${email ? ` · ${email}` : ""}`;
  const labels: Record<string, string> = {
    "plugin_install": "Installed plugin",
    "plugin_uninstall": "Uninstalled plugin",
    "plugin_sync": "Synced plugin",
    "share_create": "Created share",
    "share_revoke": "Revoked share",
    "share_access": "Share accessed",
    "alert_create": "Created alert",
    "alert_toggle": "Toggled alert",
    "settings_update": "Updated settings",
    "annotation_create": "Created annotation",
    "fusion_create": "Created fusion",
    "api_key_create": "Created API key",
    "api_key_revoke": "Revoked API key",
  };
  return labels[action] || formatStatus(action.replace(/_/g, " "));
}

// ── Main page ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [liveHealth, setLiveHealth] = useState<HealthData | null>(null);
  const [configData, setConfigData] = useState<ConfigData | null>(null);
  const [launchpad, setLaunchpad] = useState<LaunchpadData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const { markBootPageReady } = useBootCoordinator();
  const markedRef = useRef(false);

  const load = useCallback(() => {
    setRefreshing(true);
    Promise.allSettled([
      fetch("/api/health", { cache: "no-store" }).then(r => r.ok ? r.json() : null),
      fetch("/api/health/config", { cache: "no-store" }).then(r => r.ok ? r.json() : null),
      apiFetch("/api/launchpad").then(r => r.ok ? r.json() : null),
    ]).then(([hRes, cRes, lpRes]) => {
      if (hRes.status === "fulfilled") setLiveHealth(hRes.value);
      if (cRes.status === "fulfilled") setConfigData(cRes.value);
      if (lpRes.status === "fulfilled" && lpRes.value) setLaunchpad(lpRes.value);
      setLoading(false);
      setRefreshing(false);
      // B225: signal "first page ready" once initial fetch resolves so the
      // boot splash dismisses to reveal real content (not the "Loading..."
      // text below). Idempotent — only fires the first time.
      if (!markedRef.current) {
        markedRef.current = true;
        markBootPageReady();
      }
    });
  }, [markBootPageReady]);

  useEffect(() => { load(); }, [load]);
  // Auto-refresh every 60s
  useEffect(() => {
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  const checks = evaluateChecks(liveHealth, configData);
  const { level } = summarize(checks);
  const counts = countByStatus(checks);

  if (loading && !liveHealth) {
    // Skeleton matches the populated layout so the page doesn't snap
    // structurally when data resolves. Header + system-status card +
    // stats tile row + a few section cards.
    return (
      <div className="max-w-[1200px] space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-9 w-24 rounded-md" />
        </div>
        <div className="bg-card rounded-lg border border-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
          <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-9 rounded-md" />)}
          </div>
        </div>
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-[88px] rounded-lg" />)}
        </div>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    );
  }

  const lp = launchpad || {
    recent_activity: [],
    recent_data_changes: [],
    alerts_summary: { total: 0, enabled: 0, triggered_24h: 0, recent_triggers: [] },
    health_snapshot: null,
    needs_attention: [],
    stats: {},
  };

  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground font-body">Your NousViz instance at a glance.</p>
        </div>
        <button
          onClick={load}
          disabled={refreshing}
          className="h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* ── Needs Attention (top — most urgent) ──────────────────── */}
      {lp.needs_attention.length > 0 && (
        <div className="space-y-2">
          {lp.needs_attention.map((item, i) => (
            <div key={i} className={cn(
              "flex items-start gap-3 px-4 py-3 rounded-lg border",
              item.severity === "warning" ? "bg-yellow-500/5 border-yellow-500/20" : "bg-blue-500/5 border-blue-500/20"
            )}>
              {item.severity === "warning"
                ? <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
                : <Clock className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground">{item.message}</p>
                {item.last_sync && (
                  <p className="text-xs text-muted-foreground mt-0.5">Last sync: {formatRelativeTime(item.last_sync)}</p>
                )}
                {item.expires_at && (
                  <p className="text-xs text-muted-foreground mt-0.5">Expires: {formatRelativeTime(item.expires_at)}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── System Status (compact inline; links to /system) ────── */}
      <SectionCard title="System Status" icon={Shield} to="/system"
        badge={`${labelForLevel(level)} · ${counts.pass} Passing${counts.warn > 0 ? ` · ${counts.warn} Warning${counts.warn !== 1 ? "s" : ""}` : ""}`}
      >
        <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {checks.map(c => (
            <div key={c.id} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/30 text-xs">
              <StatusIcon status={c.status} />
              <span className="text-foreground font-body flex-1 truncate">{c.label}</span>
              <span className="text-muted-foreground font-mono-deck truncate max-w-[140px]">{c.detail}</span>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── Two-column grid: Alerts + Data Changes ─────────────── */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">

        {/* Recent Alerts */}
        <SectionCard title="Alerts" icon={Bell} to="/alerts"
          badge={lp.alerts_summary.enabled > 0 ? `${lp.alerts_summary.enabled} Enabled` : undefined}
        >
          {lp.alerts_summary.triggered_24h > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-yellow-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" />
                {lp.alerts_summary.triggered_24h} alert{lp.alerts_summary.triggered_24h !== 1 ? "s" : ""} fired in the last 24 hours
              </p>
              {lp.alerts_summary.recent_triggers.map((t, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/30 text-xs">
                  <Bell className="w-3 h-3 text-yellow-400 shrink-0" />
                  <span className="text-foreground flex-1 truncate">{t.alert_name}</span>
                  <span className="text-muted-foreground font-mono-deck" title={formatAbsoluteTime(t.triggered_at)}>
                    {formatRelativeTime(t.triggered_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : lp.alerts_summary.total > 0 ? (
            <p className="text-xs text-muted-foreground">
              {lp.alerts_summary.enabled} of {lp.alerts_summary.total} alerts enabled. No alerts fired in the last 24 hours.
            </p>
          ) : (
            <EmptyState message="No alerts configured yet. Create your first alert to monitor data anomalies." />
          )}
        </SectionCard>

        {/* Recent Data Changes — B170 (v0.9.5.2): card "more" link points
            at /datasets (was /data-port; that page was retired). */}
        <SectionCard title="Data Changes" icon={Database} to="/datasets">
          {lp.recent_data_changes.length > 0 ? (
            <div className="space-y-2">
              {lp.recent_data_changes.map((d, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/30 text-xs">
                  <Plug className="w-3 h-3 text-muted-foreground shrink-0" />
                  <span className="text-foreground flex-1 truncate">{d.display_name || d.plugin_id}</span>
                  {d.total_rows !== undefined && (
                    <span className="text-muted-foreground font-mono-deck">{d.total_rows.toLocaleString()} rows</span>
                  )}
                  {d.last_sync && (
                    <span className="text-muted-foreground font-mono-deck" title={formatAbsoluteTime(d.last_sync)}>
                      {formatRelativeTime(d.last_sync)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No plugin data syncs recorded yet." />
          )}
        </SectionCard>
      </div>

      {/* ── Recent Activity ───────────────────────────────────────── */}
      <SectionCard title="Recent Activity" icon={Activity}
        badge={lp.recent_activity.length > 0 ? `${lp.recent_activity.length} events` : undefined}
      >
        {lp.recent_activity.length > 0 ? (
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {lp.recent_activity.map((e, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/20 text-xs">
                <Activity className="w-3 h-3 text-muted-foreground shrink-0" />
                <span className="text-foreground flex-1 truncate">
                  {actionLabel(e.action, e.details)}
                  {e.plugin_id && <span className="text-muted-foreground"> · {e.plugin_id}</span>}
                  {e.user_name && <span className="text-muted-foreground"> · {e.user_name}</span>}
                </span>
                <span className="text-muted-foreground font-mono-deck shrink-0" title={formatAbsoluteTime(e.created_at)}>
                  {formatRelativeTime(e.created_at)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState message="No recent activity." />
        )}
      </SectionCard>

      {/* ── Quick stats row ───────────────────────────────────────── */}
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3">
        <Link to="/annotations" className="bg-card rounded-lg border border-border p-4 hover:bg-secondary/20 transition-colors">
          <p className="text-xs text-muted-foreground">Annotations</p>
          <p className="text-2xl font-display text-foreground mt-1">{lp.stats.annotations ?? 0}</p>
        </Link>
        <Link to="/shares" className="bg-card rounded-lg border border-border p-4 hover:bg-secondary/20 transition-colors">
          <p className="text-xs text-muted-foreground">Active Shares</p>
          <p className="text-2xl font-display text-foreground mt-1">{lp.stats.active_shares ?? 0}</p>
        </Link>
        <Link to="/marketplace" className="bg-card rounded-lg border border-border p-4 hover:bg-secondary/20 transition-colors">
          <p className="text-xs text-muted-foreground">Marketplace</p>
          <p className="text-sm font-display text-primary mt-2 flex items-center gap-1">Browse <ArrowRight className="w-3 h-3" /></p>
        </Link>
      </div>
    </div>
  );
}
