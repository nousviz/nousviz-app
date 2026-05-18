/**
 * Unified Data Explorer — one surface for every data source the
 * instance can read from, regardless of whether it's an operator-defined
 * connection (Postgres/MySQL/ClickHouse) or a plugin-managed source.
 *
 * v1.0 simplification: replaces the separate Connections + Datasets nav
 * entries. Browse here, configure credentials under /connections (admin).
 *
 * Each source routes into its existing detail page:
 *   - operator connection → /connections/:id (table list)
 *   - plugin source       → /datasets?plugin=:slug (dataset list)
 *
 * Both eventually land on the same row-level browser
 * ([ConnectionTableRowsPage] or [DatasetDetailPage]).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Database,
  Package,
  Plus,
  RefreshCw,
  Search,
  Settings,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn, formatNumber, formatRelativeTime } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

type SourceKind = "operator" | "plugin";

interface UnifiedSource {
  kind: SourceKind;
  id: string;            // connection id, or plugin slug
  name: string;          // user-visible name
  type: string;          // postgres / mysql / clickhouse / plugin
  detail: string;        // host:port/db, or plugin id, or table count
  href: string;          // where clicking goes
  tableCount?: number;
  rowCount?: number;
  lastSync?: string;
  isDefault?: boolean;
}

const TYPE_CHIP: Record<string, string> = {
  postgres: "bg-blue-500/10 text-blue-400",
  mysql: "bg-orange-500/10 text-orange-400",
  clickhouse: "bg-yellow-500/10 text-yellow-400",
  plugin: "bg-purple-500/10 text-purple-400",
};

const TYPE_LABEL: Record<string, string> = {
  postgres: "PostgreSQL",
  mysql: "MySQL",
  clickhouse: "ClickHouse",
  plugin: "Plugin",
};

export default function DataPage() {
  useMarkBootReadyOnMount();
  const [sources, setSources] = useState<UnifiedSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const load = useCallback(() => {
    setLoading(true);

    const connectionsPromise = apiFetch("/api/connections")
      .then((r) => (r.ok ? r.json() : { connections: [] }))
      .catch(() => ({ connections: [] }));

    const pluginsPromise = apiFetch("/api/plugins")
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => []);

    Promise.all([connectionsPromise, pluginsPromise]).then(
      ([connData, pluginData]) => {
        // Operator-defined connections, excluding plugin-managed synthetic ones
        // (those surface as Plugin sources via /api/plugins instead).
        const opConns: UnifiedSource[] = (connData.connections ?? [])
          .filter((c: any) => !String(c.name ?? "").startsWith("plugin:"))
          .map((c: any) => {
            const cfg = c.config ?? {};
            const host = cfg.host || "localhost";
            const port =
              cfg.port ||
              (c.type === "mysql"
                ? "3306"
                : c.type === "clickhouse"
                  ? "8123"
                  : "5432");
            const detail = `${host}:${port}${cfg.database ? ` / ${cfg.database}` : ""}`;
            return {
              kind: "operator" as SourceKind,
              id: c.id,
              name: c.name,
              type: c.type,
              detail,
              href: `/connections/${c.id}`,
              isDefault: !!c.is_default,
            };
          });

        // Plugin sources with at least one dataset or table
        const pluginList: any[] = Array.isArray(pluginData)
          ? pluginData
          : (pluginData.plugins ?? []);
        const pluginSources: UnifiedSource[] = pluginList
          .map((p: any) => {
            const datasets = Array.isArray(p.datasets) ? p.datasets : [];
            const pgTables = Array.from(
              new Set<string>(p.databases?.postgres?.tables ?? []),
            );
            const tableCount = datasets.length || pgTables.length;
            if (tableCount === 0) return null;

            const lastSync =
              datasets
                .map((d: any) => {
                  const s = d.last_sync;
                  if (!s) return null;
                  if (typeof s === "object") return s.timestamp ?? s.value ?? null;
                  return s;
                })
                .filter(Boolean)
                .sort()
                .pop() ?? undefined;

            const totalRows = datasets.reduce(
              (acc: number, d: any) =>
                acc + (typeof d.rows === "number" ? d.rows : 0),
              0,
            );

            return {
              kind: "plugin" as SourceKind,
              id: p.id,
              name: p.display_name ?? p.name ?? p.id,
              type: "plugin",
              detail: `${tableCount} dataset${tableCount !== 1 ? "s" : ""}${totalRows > 0 ? ` · ${formatNumber(totalRows)} rows` : ""}`,
              href: `/datasets?plugin=${encodeURIComponent(p.id)}`,
              tableCount,
              rowCount: totalRows || undefined,
              lastSync,
            } as UnifiedSource;
          })
          .filter((s: UnifiedSource | null): s is UnifiedSource => s !== null);

        setSources([...opConns, ...pluginSources]);
        setLoading(false);
      },
    );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const allTypes = useMemo(
    () => Array.from(new Set(sources.map((s) => s.type))).sort(),
    [sources],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return sources.filter((s) => {
      if (typeFilter !== "all" && s.type !== typeFilter) return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.type.toLowerCase().includes(q) ||
        s.detail.toLowerCase().includes(q)
      );
    });
  }, [sources, search, typeFilter]);

  return (
    <div className="max-w-[1200px] space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-muted-foreground font-body">
          Every data source this instance can read from — databases and plugins.
        </p>
        <div className="flex items-center gap-2">
          <Link
            to="/connections"
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors"
            title="Manage connection credentials"
          >
            <Settings className="w-3 h-3" /> Manage connections
          </Link>
          <button
            onClick={load}
            disabled={loading}
            className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Type filter + search */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setTypeFilter("all")}
            className={cn(
              "px-2.5 py-1 rounded-full text-xs font-body transition-colors",
              typeFilter === "all"
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground",
            )}
          >
            All sources ({sources.length})
          </button>
          {allTypes.map((t) => {
            const count = sources.filter((s) => s.type === t).length;
            return (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={cn(
                  "px-2.5 py-1 rounded-full text-xs font-body transition-colors flex items-center gap-1.5",
                  typeFilter === t
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground",
                )}
              >
                <span
                  className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    TYPE_CHIP[t]?.split(" ")[0] ?? "bg-secondary",
                  )}
                />
                {TYPE_LABEL[t] ?? t} ({count})
              </button>
            );
          })}
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter sources…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-8 pr-3 w-56 rounded-md bg-secondary border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Sources */}
      {loading && sources.length === 0 ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-16 bg-secondary/40 rounded-md animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-border rounded-lg">
          <Database className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
          {sources.length === 0 ? (
            <>
              <p className="text-sm text-muted-foreground mb-3">
                No data sources yet.
              </p>
              <Link
                to="/connections"
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs"
              >
                <Plus className="w-3 h-3" /> Add a connection
              </Link>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No sources match your filter.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-1.5">
          {filtered.map((s) => (
            <Link
              key={`${s.kind}:${s.id}`}
              to={s.href}
              className="flex items-center gap-3 px-4 py-3 rounded-md bg-card border border-border text-xs hover:border-primary/40 transition-colors group"
            >
              <div
                className={cn(
                  "h-9 w-9 rounded-lg flex items-center justify-center shrink-0",
                  TYPE_CHIP[s.type] ?? "bg-secondary text-muted-foreground",
                )}
              >
                {s.kind === "plugin" ? (
                  <Package className="w-4 h-4" />
                ) : (
                  <Database className="w-4 h-4" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-foreground font-medium group-hover:text-primary transition-colors">
                    {s.name}
                  </span>
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-mono-deck uppercase tracking-wider",
                      TYPE_CHIP[s.type] ?? "bg-secondary text-muted-foreground",
                    )}
                  >
                    {TYPE_LABEL[s.type] ?? s.type}
                  </span>
                  {s.isDefault && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400">
                      default
                    </span>
                  )}
                </div>
                <p className="text-muted-foreground font-mono-deck truncate mt-0.5">
                  {s.detail}
                  {s.lastSync && (
                    <span className="ml-1.5 opacity-60">
                      · last sync {formatRelativeTime(s.lastSync)}
                    </span>
                  )}
                </p>
              </div>
              <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wider shrink-0">
                Browse →
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
