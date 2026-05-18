/**
 * LogsPanel — operator-facing /system/logs view.
 *
 * B208 (v0.9.6.1): full filter overhaul. The previous panel exposed only
 * source + level dropdowns; rich context (plugin_id, run_id, actor) was
 * buried in the detail JSONB. This rewrite surfaces the promoted columns
 * as first-class filters, adds keyset pagination, free-text search,
 * date range, and renders the detail field as labeled chips.
 *
 * B209: chips on known keys (plugin_id, run_id, actor_user_id) become
 * navigation links to the relevant detail page.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { DataTable } from "@/components/ui/DataTable";
import {
  RefreshCw,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Info,
  AlertTriangle,
  X,
  Search,
} from "lucide-react";

interface LogEntry {
  id: number;
  level: string;
  source: string;
  message: string;
  detail: Record<string, unknown>;
  /**
   * B313 (v0.10.4): clean headline parsed from detail.stderr_tail when
   * the entry is a sync/hook failure. Rendered prominently above the
   * raw detail rows so operators see the actionable exception message
   * instead of a head-chopped traceback dump.
   */
  error_summary?: string | null;
  created_at: string;
  plugin_id: string | null;
  actor_user_id: string | null;
  run_id: number | null;
  actor_email: string | null;
  run_status: string | null;
}

interface FilterOptions {
  plugins: string[];
  users: { id: string; email: string | null }[];
}

const SOURCES = [
  "all",
  "plugin",            // B238 (v0.9.10.1): plugin authors' log_event calls
  "plugin_install",
  "plugin_update",
  "plugin_uninstall",
  "plugin_lifecycle",
  "plugin_loader",
  "plugin_config",
  "plugin_route",
  "sync",
  "scheduler",
  "credentials",
  "connections",
  "dashboards",
  "deploy_keys",
  "api",
  "startup",
];
const LEVELS = ["all", "info", "warning", "error"];

// B209: detect whether the /admin/users/:id route exists in the app.
// Per B209 ticket, we don't add a stub user route — chips degrade to
// display-only when the route is absent. App.tsx is the source of truth.
const USERS_DETAIL_ROUTE_EXISTS = false;

const PAGE_SIZE = 100;

export default function LogsPanel() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter state — initialized from URL so deep-links restore the view.
  const [source, setSource] = useState(searchParams.get("source") ?? "all");
  const [level, setLevel] = useState(searchParams.get("level") ?? "all");
  const [pluginId, setPluginId] = useState(searchParams.get("plugin_id") ?? "");
  const [actorUserId, setActorUserId] = useState(searchParams.get("actor_user_id") ?? "");
  const [runId, setRunId] = useState(searchParams.get("run_id") ?? "");
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [since, setSince] = useState(searchParams.get("since") ?? "");
  const [until, setUntil] = useState(searchParams.get("until") ?? "");

  // Debounced free-text search to avoid a request per keystroke.
  const [qDebounced, setQDebounced] = useState(q);
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [nextCursor, setNextCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    plugins: [],
    users: [],
  });

  const [expandedId, setExpandedId] = useState<number | null>(null);
  // B212 (v0.9.6.3): default ON. /system/logs is the canonical "what's
  // happening now" view; static-snapshot-by-default doesn't match the page's
  // purpose. Operators can still toggle off via the checkbox.
  const [autoRefresh, setAutoRefresh] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  // Build query params from current filter state. Used both for URL sync
  // and for the API request.
  const buildParams = useCallback(
    (opts: { cursor?: number | null } = {}) => {
      const p = new URLSearchParams();
      if (source !== "all") p.set("source", source);
      if (level !== "all") p.set("level", level);
      if (pluginId) p.set("plugin_id", pluginId);
      if (actorUserId) p.set("actor_user_id", actorUserId);
      if (runId) p.set("run_id", runId);
      if (qDebounced) p.set("q", qDebounced);
      if (since) p.set("since", since);
      if (until) p.set("until", until);
      if (opts.cursor != null) p.set("cursor", String(opts.cursor));
      p.set("limit", String(PAGE_SIZE));
      return p;
    },
    [source, level, pluginId, actorUserId, runId, qDebounced, since, until],
  );

  // Persist filter state to URL (replace, not push, so back stack stays clean).
  useEffect(() => {
    const next = buildParams();
    next.delete("limit"); // not user-facing
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
    // We intentionally only depend on buildParams's inputs, not searchParams,
    // so we don't loop on our own URL writes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, level, pluginId, actorUserId, runId, qDebounced, since, until]);

  const load = useCallback(() => {
    setLoading(true);
    apiFetch(`/api/admin/logs?${buildParams()}`)
      .then((r) => r.json())
      .then((d) => {
        setLogs(d.logs || []);
        setNextCursor(d.next_cursor ?? null);
      })
      .catch((e) => console.error("Logs load failed:", e))
      .finally(() => setLoading(false));
  }, [buildParams]);

  // Initial load + reload on filter change.
  useEffect(() => {
    load();
  }, [load]);

  // Load filter dropdown options once on mount. Refreshes every 5 minutes
  // in case new plugins / users have appeared.
  useEffect(() => {
    const fetchOptions = () =>
      apiFetch("/api/admin/logs/filters")
        .then((r) => r.json())
        .then((d: FilterOptions) => setFilterOptions(d))
        .catch(() => {});
    fetchOptions();
    const id = setInterval(fetchOptions, 5 * 60_000);
    return () => clearInterval(id);
  }, []);

  // Auto-refresh polls every 30s when enabled.
  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(load, 30_000);
      return () => clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [autoRefresh, load]);

  const loadMore = async () => {
    if (nextCursor == null) return;
    setLoadingMore(true);
    try {
      const r = await apiFetch(`/api/admin/logs?${buildParams({ cursor: nextCursor })}`);
      const d = await r.json();
      setLogs((prev) => [...prev, ...(d.logs || [])]);
      setNextCursor(d.next_cursor ?? null);
    } catch (e) {
      console.error("Logs load-more failed:", e);
    } finally {
      setLoadingMore(false);
    }
  };

  const clearAll = () => {
    setSource("all");
    setLevel("all");
    setPluginId("");
    setActorUserId("");
    setRunId("");
    setQ("");
    setSince("");
    setUntil("");
  };

  const anyFilterActive =
    source !== "all" ||
    level !== "all" ||
    !!pluginId ||
    !!actorUserId ||
    !!runId ||
    !!q ||
    !!since ||
    !!until;

  const levelIcon = (lvl: string) => {
    switch (lvl) {
      case "error":
        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
      case "warning":
        return <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />;
      default:
        return <Info className="w-3.5 h-3.5 text-blue-400" />;
    }
  };

  const levelColor = (lvl: string) => {
    switch (lvl) {
      case "error":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <div className="space-y-4">
      {/* Filter bar — row 1: dropdowns. B288 (v0.9.11.26): stacks vertically below sm so the refresh group doesn't strand on its own row via ml-auto. */}
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-end gap-3">
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Source
          </label>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground"
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {s === "all" ? "All Sources" : s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Level
          </label>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground"
          >
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l === "all" ? "All Levels" : l}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Plugin
          </label>
          <select
            value={pluginId}
            onChange={(e) => setPluginId(e.target.value)}
            className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground"
          >
            <option value="">All Plugins</option>
            {filterOptions.plugins.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            User
          </label>
          <select
            value={actorUserId}
            onChange={(e) => setActorUserId(e.target.value)}
            className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground w-full sm:w-auto sm:min-w-[180px]"
          >
            <option value="">All Users</option>
            {filterOptions.users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.email ?? u.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Run ID
          </label>
          <input
            type="text"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            placeholder="run_id"
            className="h-8 px-2 rounded-md bg-background border border-border text-sm text-foreground font-mono-deck w-24"
          />
        </div>

        <div className="flex items-center gap-2 sm:ml-auto">
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
          <button
            onClick={load}
            disabled={loading}
            className="h-8 px-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Filter bar — row 2: text search + date range + clear. B288 (v0.9.11.26): stacks vertically below sm. */}
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-end gap-3">
        <div className="w-full sm:flex-1 sm:min-w-[240px]">
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Search message
          </label>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="filter by message text…"
              className="w-full h-8 pl-8 pr-3 rounded-md bg-background border border-border text-sm text-foreground"
            />
          </div>
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Since
          </label>
          {/* B212 (v0.9.6.3): date-only precision. API normalizes to
              start-of-day UTC server-side. */}
          <input
            type="date"
            value={since}
            onChange={(e) => setSince(e.target.value)}
            className="h-8 px-2 rounded-md bg-background border border-border text-sm text-foreground"
          />
        </div>
        <div>
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase block mb-1">
            Until
          </label>
          {/* B212: API normalizes to end-of-day UTC so until=2026-04-29
              includes events at 23:59:59, not just at midnight. */}
          <input
            type="date"
            value={until}
            onChange={(e) => setUntil(e.target.value)}
            className="h-8 px-2 rounded-md bg-background border border-border text-sm text-foreground"
          />
        </div>
        {anyFilterActive && (
          <button
            onClick={clearAll}
            className="h-8 px-3 rounded-md bg-secondary/50 hover:bg-secondary text-xs text-foreground flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Clear all
          </button>
        )}
      </div>

      {/* Log entries */}
      {loading && logs.length === 0 ? (
        <div className="py-12 text-center text-xs text-muted-foreground animate-pulse">
          Loading logs…
        </div>
      ) : logs.length === 0 ? (
        <div className="py-12 text-center border border-dashed border-border rounded-lg">
          <p className="text-sm text-muted-foreground">No logs found</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            {anyFilterActive
              ? "Try adjusting filters or clearing all."
              : "Logs appear here when plugin operations occur."}
          </p>
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <DataTable minWidth="720px">
            <thead>
              <tr className="bg-secondary/30 text-muted-foreground">
                <th className="px-3 py-2 text-left font-semibold w-8"></th>
                <th className="px-3 py-2 text-left font-semibold w-40">Time</th>
                <th className="px-3 py-2 text-left font-semibold w-28">Source</th>
                <th className="px-3 py-2 text-left font-semibold w-16">Level</th>
                <th className="px-3 py-2 text-left font-semibold">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <LogRow
                  key={log.id}
                  log={log}
                  expanded={expandedId === log.id}
                  onToggle={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  levelIcon={levelIcon(log.level)}
                  levelColor={levelColor(log.level)}
                />
              ))}
            </tbody>
          </DataTable>

          {nextCursor != null && (
            <div className="p-3 border-t border-border bg-secondary/20 text-center">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="h-8 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-xs text-foreground transition-colors disabled:opacity-50"
              >
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </div>
      )}

      <p className="text-[10px] text-muted-foreground">
        Showing {logs.length} {logs.length === 1 ? "entry" : "entries"}
        {nextCursor != null ? " (more available)" : ""}.
      </p>
    </div>
  );
}

// ── Log row ───────────────────────────────────────────────────────────

function LogRow({
  log,
  expanded,
  onToggle,
  levelIcon,
  levelColor,
}: {
  log: LogEntry;
  expanded: boolean;
  onToggle: () => void;
  levelIcon: React.ReactNode;
  levelColor: string;
}) {
  // Detail keys we surface as labeled chips at the top of the expansion.
  // Anything else falls through to plain key:value lines below.
  const detailKeys = Object.keys(log.detail || {});
  const knownKeys = new Set([
    "plugin_id",
    "actor_user_id",
    "run_id",
    "action",
  ]);
  const otherDetails = detailKeys.filter((k) => !knownKeys.has(k));
  const hasExpandable =
    !!log.plugin_id ||
    !!log.actor_user_id ||
    !!log.run_id ||
    detailKeys.length > 0;

  return (
    <>
      <tr
        onClick={onToggle}
        className={cn(
          "border-t border-border cursor-pointer hover:bg-secondary/20 transition-colors",
          expanded && "bg-secondary/10",
        )}
      >
        <td className="px-3 py-2">
          {hasExpandable ? (
            expanded ? (
              <ChevronDown className="w-3 h-3 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-3 h-3 text-muted-foreground" />
            )
          ) : null}
        </td>
        <td
          className="px-3 py-2 font-mono-deck text-muted-foreground whitespace-nowrap"
          title={log.created_at}
        >
          {new Date(log.created_at).toLocaleString()}
        </td>
        <td className="px-3 py-2">
          <span className="font-mono-deck text-muted-foreground bg-secondary/50 px-1.5 py-0.5 rounded text-[10px]">
            {log.source.replace(/_/g, " ")}
          </span>
        </td>
        <td className="px-3 py-2">
          <span className="flex items-center gap-1">
            {levelIcon}
            <span className={levelColor}>{log.level}</span>
          </span>
        </td>
        <td className="px-3 py-2 text-foreground max-w-[600px]">
          <div className="truncate">{log.message}</div>
          {log.error_summary && (
            <div
              className="mt-0.5 text-[10px] text-red-300/90 truncate font-mono-deck"
              title={log.error_summary}
            >
              {log.error_summary}
            </div>
          )}
        </td>
      </tr>
      {expanded && hasExpandable && (
        <tr className="bg-secondary/5">
          <td colSpan={5} className="px-6 py-3">
            <DetailChips log={log} otherDetails={otherDetails} />
          </td>
        </tr>
      )}
    </>
  );
}

// ── Detail chips ──────────────────────────────────────────────────────

function DetailChips({
  log,
  otherDetails,
}: {
  log: LogEntry;
  otherDetails: string[];
}) {
  return (
    <div className="space-y-2">
      {log.error_summary && (
        <div className="rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-[11px] text-red-200 font-mono-deck">
          <span className="text-red-400/70 mr-1.5">error:</span>
          {log.error_summary}
        </div>
      )}
      <div className="flex flex-wrap gap-1.5">
        {log.plugin_id && (
          <Chip
            label="plugin"
            value={log.plugin_id}
            href={`/plugin/${log.plugin_id}/overview`}
            title={`Open ${log.plugin_id}`}
          />
        )}
        {log.run_id != null && (
          <Chip
            label="run"
            value={`#${log.run_id}`}
            href={`/system/jobs?run_id=${log.run_id}`}
            title={
              log.run_status
                ? `run #${log.run_id} · ${log.run_status}`
                : `run #${log.run_id}`
            }
          />
        )}
        {log.actor_user_id && (
          <Chip
            label="user"
            value={log.actor_email ?? log.actor_user_id.slice(0, 8)}
            href={
              USERS_DETAIL_ROUTE_EXISTS
                ? `/admin/users/${log.actor_user_id}`
                : undefined
            }
            title={
              USERS_DETAIL_ROUTE_EXISTS
                ? log.actor_email ?? log.actor_user_id
                : `${log.actor_email ?? log.actor_user_id} — user detail page TBD`
            }
          />
        )}
        {typeof log.detail?.action === "string" && (
          <Chip label="action" value={log.detail.action as string} />
        )}
      </div>

      {otherDetails.length > 0 && (
        <dl className="grid grid-cols-[max-content,1fr] gap-x-3 gap-y-1 text-[10px] font-mono-deck">
          {otherDetails.map((k) => {
            const v = log.detail?.[k];
            return (
              <div key={k} className="contents">
                <dt className="text-muted-foreground">{k}:</dt>
                <dd className="text-foreground break-all">
                  {typeof v === "string" || typeof v === "number" || typeof v === "boolean"
                    ? String(v)
                    : JSON.stringify(v)}
                </dd>
              </div>
            );
          })}
        </dl>
      )}
    </div>
  );
}

// ── Chip ──────────────────────────────────────────────────────────────

function Chip({
  label,
  value,
  href,
  title,
}: {
  label: string;
  value: string;
  href?: string;
  title?: string;
}) {
  const inner = (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-secondary/40 text-[10px] font-mono-deck">
      <span className="text-muted-foreground">{label}:</span>
      <span className="text-foreground">{value}</span>
    </span>
  );
  if (href) {
    return (
      <Link
        to={href}
        title={title}
        className="hover:opacity-80 transition-opacity"
        onClick={(e) => e.stopPropagation()}
      >
        {inner}
      </Link>
    );
  }
  return <span title={title}>{inner}</span>;
}
