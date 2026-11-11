import { useCallback, useEffect, useState } from "react";
import { apiFetch, fetchLicence, type Licence } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";
import { BadgeCheck, Check, RefreshCw, X } from "lucide-react";

/** MC-608: the complete plan picture — tier, licence health, every
 * limit with live usage, every feature flag, email relay — in one
 * place. Renders nothing on community installs (no licence endpoint)
 * or for non-admin viewers (endpoint is admin-gated). Feature flags
 * render generically, so new gated features appear here the day the
 * contract grows them — no UI change needed. */

const FEATURE_LABELS: Record<string, string> = {
  mcp: "AI assistant access (MCP)",
  embedding: "Dashboard embedding",
  sso: "Single sign-on (SSO)",
  audit_log: "Audit log",
  data_export: "Data export",
};

function prettyFlag(key: string): string {
  return FEATURE_LABELS[key] || key.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
}

function UsageRow({ label, used, limit }: { label: string; used: number | null; limit: number | null }) {
  const pct = limit && used !== null ? Math.min(100, (used / limit) * 100) : null;
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground">
          {used === null ? "—" : used}
          {limit === null ? " · unlimited" : ` of ${limit}`}
        </span>
      </div>
      {pct !== null && (
        <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
          <div
            className={`h-full rounded-full ${pct >= 100 ? "bg-amber-500" : "bg-primary"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default function PlanSection() {
  const [licence, setLicence] = useState<Licence | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(() => { fetchLicence().then(setLicence); }, []);
  useEffect(() => { load(); }, [load]);

  async function refresh() {
    setRefreshing(true);
    try {
      await apiFetch("/api/enterprise/licence/refresh", { method: "POST" });
    } catch { /* fail-open: the read below still shows cached state */ }
    load();
    setRefreshing(false);
  }

  if (!licence) return null;

  const healthy = licence.status === "live";
  const cached = licence.status === "cached";
  const statusText = healthy
    ? "Licence up to date"
    : cached
      ? "Running on cached licence"
      : "Licence unavailable — free-tier limits apply";

  return (
    <div className="bg-card rounded-lg border border-border p-4 space-y-4">
      {/* Header: tier + health + refresh */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <BadgeCheck className="w-4 h-4 text-primary" />
          <h3 className="font-display text-sm text-foreground">
            <span className="capitalize">{licence.tier}</span> plan
          </h3>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                healthy ? "bg-emerald-500" : cached ? "bg-amber-500" : "bg-red-500"
              }`}
            />
            {statusText}
            {licence.fetched_at && (
              <span className="text-muted-foreground/60">
                · checked {formatRelativeTime(new Date(licence.fetched_at * 1000).toISOString())}
              </span>
            )}
          </span>
          <button
            onClick={refresh}
            disabled={refreshing}
            className="h-7 px-2.5 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-1.5 text-xs text-muted-foreground transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Limits with live usage */}
      <div className="grid sm:grid-cols-2 gap-4">
        <UsageRow label="Users (active seats)" used={licence.usage.users} limit={licence.limits.max_users} />
        <UsageRow label="Installed plugins" used={licence.usage.plugins} limit={licence.limits.max_plugins} />
      </div>

      {/* Everything the plan includes */}
      <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5 pt-1">
        {Object.entries(licence.features).map(([key, on]) => (
          <div key={key} className="flex items-center gap-2 text-xs">
            {on
              ? <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              : <X className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />}
            <span className={on ? "text-foreground" : "text-muted-foreground/60"}>
              {prettyFlag(key)}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-2 text-xs">
          {licence.email_relay
            ? <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
            : <X className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />}
          <span className={licence.email_relay ? "text-foreground" : "text-muted-foreground/60"}>
            Managed email sending
          </span>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground/70 pt-1 border-t border-border">
        Plan changes never remove anything: existing users and installed plugins
        are always kept, whatever your limits become.
      </p>
    </div>
  );
}
