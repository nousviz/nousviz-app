import { apiFetch } from "@/lib/api";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, X, RefreshCw } from "lucide-react";

interface ConnectionIssue {
  plugin_id: string;
  plugin_name: string;
  type: "sync_failed" | "stale_data" | "connection_error";
  message: string;
  last_success: string | null;
  hours_since: number;
}

export default function ConnectionHealthBanner({ onVisibleChange }: { onVisibleChange?: (visible: boolean) => void }) {
  const [issues, setIssues] = useState<ConnectionIssue[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    checkHealth();
    // Re-check every 10 minutes
    const interval = setInterval(checkHealth, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  async function checkHealth() {
    try {
      setChecking(true);
      const res = await apiFetch("/api/health/connections");
      if (res.ok) {
        const data = await res.json();
        setIssues(data.issues || []);
      }
    } catch {
      // If API is down, that's a bigger problem — the online indicator handles it
    } finally {
      setChecking(false);
    }
  }

  const visibleIssues = issues.filter((i) => !dismissed.has(i.plugin_id + i.type));

  useEffect(() => {
    onVisibleChange?.(visibleIssues.length > 0);
  }, [visibleIssues.length, onVisibleChange]);

  if (visibleIssues.length === 0) return null;

  const isError = visibleIssues.some((i) => i.type === "sync_failed" || i.type === "connection_error");

  return (
    <div
      className={`fixed top-[calc(var(--topbar-h)+var(--banner-h,0px))] right-0 left-0 md:left-[var(--sidebar-w)] z-20 px-4 py-2.5 flex items-center gap-3 text-sm border-b ${
        isError
          ? "bg-red-500/10 border-red-500/20 text-red-400"
          : "bg-orange-500/10 border-orange-500/20 text-orange-400"
      }`}
    >
      <AlertTriangle className="w-4 h-4 flex-shrink-0" />

      <div className="flex-1 flex items-center gap-4 overflow-x-auto">
        {visibleIssues.map((issue) => (
          <span key={issue.plugin_id + issue.type} className="flex items-center gap-2 whitespace-nowrap">
            <span className="font-display text-xs font-semibold">{issue.plugin_name}:</span>
            <span className="text-xs font-body">{issue.message}</span>
            {issue.hours_since > 0 && (
              <span className="text-[10px] opacity-60">({issue.hours_since}h ago)</span>
            )}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <Link
          to="/connections"
          className="text-xs font-body px-2.5 py-1 rounded-md bg-white/10 hover:bg-white/20 transition-colors"
        >
          Fix now
        </Link>
        <button
          onClick={() => checkHealth()}
          className="p-1 rounded hover:bg-white/10 transition-colors"
          title="Re-check connections"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? "animate-spin" : ""}`} />
        </button>
        <button
          onClick={() => {
            const newDismissed = new Set(dismissed);
            visibleIssues.forEach((i) => newDismissed.add(i.plugin_id + i.type));
            setDismissed(newDismissed);
          }}
          className="p-1 rounded hover:bg-white/10 transition-colors"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
