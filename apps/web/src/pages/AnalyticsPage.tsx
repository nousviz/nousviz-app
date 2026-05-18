import { useState, useEffect } from "react";
import {
  Clock,
  Eye,
  BarChart3,
  Monitor,
  Globe,
  Activity,
  TrendingUp,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const API_BASE = "/api";

interface Analytics {
  period_days: number;
  total_events: number;
  total_page_views: number;
  estimated_time_minutes: number;
  estimated_time_display: string;
  sessions: number;
  avg_session_minutes: number;
  devices: Record<string, number>;
  browsers: Record<string, number>;
  unique_ips: string[];
  ip_activity: Record<string, number>;
  peak_hour: string;
  hourly_distribution: Record<string, number>;
  time_per_page: { path: string; minutes: number }[];
}

interface DashboardUsage {
  period_days: number;
  total_events: number;
  page_views: { path: string; label: string; views: number }[];
  plugin_activity: { plugin: string; events: number }[];
  action_breakdown: Record<string, number>;
  daily_activity: { date: string; events: number }[];
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color = "blue",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color?: "blue" | "green" | "purple" | "orange";
}) {
  const colorMap = {
    blue: "bg-blue-500/10 text-blue-400",
    green: "bg-green-500/10 text-green-400",
    purple: "bg-purple-500/10 text-purple-400",
    orange: "bg-orange-500/10 text-orange-400",
  };
  return (
    <div className="bg-card rounded-lg border border-border p-4 flex items-start gap-3">
      <div className={cn("h-9 w-9 rounded-md flex items-center justify-center shrink-0", colorMap[color])}>
        {icon}
      </div>
      <div>
        <p className="text-xs text-muted-foreground font-body">{label}</p>
        <p className="text-xl font-display text-foreground mt-0.5">{value}</p>
        {sub && <p className="text-xs text-muted-foreground font-mono-deck mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

const KNOWN_PATHS: Record<string, string> = {
  "/": "Home",
  "/marketplace": "Marketplace",
  "/connections": "Connections",
  "/datasets": "Datasets",
  "/alerts": "Alerts",
  "/annotations": "Annotations",
  "/plugins": "Installed Plugins",
  "/settings": "Settings",
  "/analytics": "Usage Analytics",
  "/fusions": "Fusions",
};

function cleanPath(path: string): string {
  if (KNOWN_PATHS[path]) return KNOWN_PATHS[path];
  // Plugin pages
  const pluginMatch = path.match(/^\/plugin\/([^/]+)(?:\/dashboards\/(.+))?/);
  if (pluginMatch) {
    const pluginId = pluginMatch[1];
    const dashboard = pluginMatch[2];
    return dashboard ? `${pluginId} / ${dashboard}` : pluginId;
  }
  return path.replace(/^\//, "") || "Home";
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [usage, setUsage] = useState<DashboardUsage | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [aRes, uRes] = await Promise.all([
        apiFetch(`${API_BASE}/activity/analytics?days=${days}`),
        apiFetch(`${API_BASE}/activity/dashboard-usage?days=${days}`),
      ]);
      if (!aRes.ok || !uRes.ok) throw new Error("Failed to load analytics");
      setAnalytics(await aRes.json());
      setUsage(await uRes.json());
    } catch (e: any) {
      setError(e.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [days]);

  if (loading) {
    return (
      <div className="max-w-[1400px] space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse h-24" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !analytics || !usage) {
    return (
      <div className="max-w-[1400px] py-20 text-center">
        <AlertCircle className="w-8 h-8 mx-auto mb-3 text-red-400" />
        <p className="text-sm text-muted-foreground mb-4">{error || "Could not load analytics data."}</p>
        <button
          onClick={loadData}
          className="h-9 px-4 rounded-md bg-secondary text-sm text-foreground hover:bg-secondary/80 flex items-center gap-2 mx-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    );
  }

  // Prepare hourly chart data
  const hourlyData = Object.entries(analytics.hourly_distribution).map(([hour, count]) => ({
    hour,
    events: count,
  }));

  // Prepare daily chart data
  const dailyData = usage.daily_activity;

  return (
    <div className="max-w-[1400px] space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground font-body">
            How your dashboards and data are being used.
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="h-9 px-3 rounded-md bg-secondary border border-border text-sm text-foreground shrink-0"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Clock className="w-4 h-4" />}
          label="Total Time Spent"
          value={analytics.estimated_time_display}
          sub={`${analytics.sessions} session${analytics.sessions !== 1 ? "s" : ""}`}
          color="blue"
        />
        <StatCard
          icon={<Eye className="w-4 h-4" />}
          label="Page Views"
          value={analytics.total_page_views.toString()}
          sub={`${analytics.total_events} total events`}
          color="green"
        />
        <StatCard
          icon={<Activity className="w-4 h-4" />}
          label="Avg Session"
          value={`${analytics.avg_session_minutes.toFixed(0)}m`}
          sub={`Peak hour: ${analytics.peak_hour}`}
          color="purple"
        />
        <StatCard
          icon={<Monitor className="w-4 h-4" />}
          label="Devices"
          value={Object.keys(analytics.devices).join(", ") || "—"}
          sub={`${analytics.unique_ips.length} unique IP${analytics.unique_ips.length !== 1 ? "s" : ""}`}
          color="orange"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Page activity — time + views combined */}
        <div className="lg:col-span-2 bg-card rounded-lg border border-border">
          <div className="p-4 border-b border-border">
            <h3 className="font-display text-sm text-foreground flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Page Activity
            </h3>
          </div>
          <div className="divide-y divide-border">
            {analytics.time_per_page.map((page, i) => {
              const maxMinutes = analytics.time_per_page[0]?.minutes || 1;
              const pct = (page.minutes / maxMinutes) * 100;
              const views = usage.page_views.find(p => p.path === page.path)?.views;
              return (
                <div key={i} className="px-4 py-2.5 flex items-center gap-3">
                  <span className="text-xs text-foreground font-body w-[200px] truncate" title={page.path}>
                    {cleanPath(page.path)}
                  </span>
                  <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono-deck text-muted-foreground w-16 text-right">
                    {page.minutes < 1 ? "<1m" : `${page.minutes.toFixed(0)}m`}
                  </span>
                  {views !== undefined && (
                    <span className="text-xs font-mono-deck text-muted-foreground/60 w-12 text-right" title="Page views">
                      {views} {views === 1 ? "view" : "views"}
                    </span>
                  )}
                </div>
              );
            })}
            {analytics.time_per_page.length === 0 && (
              <div className="p-8 text-center text-sm text-muted-foreground">No activity yet</div>
            )}
          </div>
        </div>

        {/* Action breakdown + unused dashboards */}
        <div className="space-y-4">
          {/* Actions */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="font-display text-sm text-foreground mb-3 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-green-400" />
              Actions
            </h3>
            <div className="space-y-2">
              {Object.entries(usage.action_breakdown)
                .sort(([, a], [, b]) => b - a)
                .map(([action, count]) => (
                  <div key={action} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{action.replace(/_/g, " ")}</span>
                    <span className="font-mono-deck text-foreground">{count}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Browsers */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="font-display text-sm text-foreground mb-3 flex items-center gap-2">
              <Globe className="w-4 h-4 text-purple-400" />
              Browsers
            </h3>
            <div className="space-y-2">
              {Object.entries(analytics.browsers)
                .sort(([, a], [, b]) => b - a)
                .map(([browser, count]) => (
                  <div key={browser} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{browser}</span>
                    <span className="font-mono-deck text-foreground">{count}</span>
                  </div>
                ))}
            </div>
          </div>

        </div>
      </div>

      {/* Daily activity chart */}
      {dailyData.length > 1 && (
        <div className="bg-card rounded-lg border border-border p-5">
          <h3 className="font-display text-sm text-foreground mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            Daily Activity
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6b7280" }} tickFormatter={(v) => v.slice(5)} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
              <Tooltip
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12, color: "hsl(var(--foreground))" }}
                labelStyle={{ color: "hsl(var(--muted-foreground))" }}
              />
              <Bar dataKey="events" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Hourly distribution */}
      {hourlyData.length > 1 && (
        <div className="bg-card rounded-lg border border-border p-5">
          <h3 className="font-display text-sm text-foreground mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" />
            Activity by Hour
          </h3>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
              <Tooltip
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12, color: "hsl(var(--foreground))" }}
                labelStyle={{ color: "hsl(var(--muted-foreground))" }}
              />
              <Bar dataKey="events" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
