import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Database, Search, Clock, Package, ExternalLink } from "lucide-react";
import { formatNumber, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { classifyFreshness, FreshnessStatus } from "@/lib/freshness";
import { DataTable } from "@/components/ui/DataTable";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface Dataset {
  name: string;
  pluginSlug: string;       // B165: keep slug for drilldown URLs
  plugin: string;           // display label
  db: string;
  rows?: number;
  grain?: string;
  lastSync?: string;
  schedule?: string;        // cron expression for freshness classification
}

const FRESHNESS_PILL_STYLE: Record<FreshnessStatus, string> = {
  ok:        "bg-green-500/15 text-green-400",
  stale:     "bg-red-500/15 text-red-400",
  never:     "bg-secondary text-muted-foreground",
  untracked: "bg-secondary/50 text-muted-foreground/70",
  unknown:   "bg-secondary text-muted-foreground",
};

const FRESHNESS_PILL_LABEL: Record<FreshnessStatus, string> = {
  ok:        "Fresh",
  stale:     "Stale",
  never:     "Never synced",
  untracked: "—",
  unknown:   "—",
};

function FreshnessPill({ lastSync, schedule }: { lastSync?: string; schedule?: string }) {
  const status = classifyFreshness(lastSync, schedule);
  const tooltip = [
    lastSync ? `Last sync: ${lastSync}` : "No sync recorded",
    schedule ? `Schedule: ${schedule}` : "No schedule declared",
  ].join(" · ");
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded-full font-mono-deck ${FRESHNESS_PILL_STYLE[status]}`}
      title={tooltip}
    >
      {FRESHNESS_PILL_LABEL[status]}
    </span>
  );
}

export default function DatasetsPage() {
  useMarkBootReadyOnMount();
  const [searchParams, setSearchParams] = useSearchParams();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  // B165: filter state lives in URL params so back-button + deep-links work.
  const search = searchParams.get("search") ?? "";
  const dbFilter = searchParams.get("db") ?? "all";
  const grainFilter = searchParams.get("grain") ?? "all";
  const pluginFilter = searchParams.get("plugin") ?? null;

  const updateParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value === null || value === "" || value === "all") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    apiFetch("/api/plugins")
      .then((r) => r.json())
      .then((data) => {
        const plugins: {
          id: string;
          name?: string;
          display_name?: string;
          datasets?: Dataset[];
          databases?: { postgres?: { tables?: string[] } };
          sync?: { schedule?: string };
        }[] = Array.isArray(data) ? data : data.plugins ?? [];

        const all: Dataset[] = plugins.flatMap((p) => {
          const pluginLabel = p.display_name ?? p.name ?? p.id;
          const pluginSlug = p.id;
          const pluginSchedule = p.sync?.schedule;
          // Use datasets[] if declared; fall back to databases.postgres.tables
          if (p.datasets && p.datasets.length > 0) {
            return p.datasets.map((d: any) => {
              let sync = d.last_sync;
              if (sync && typeof sync === "object") sync = sync.timestamp || sync.value || JSON.stringify(sync);
              return {
                ...d,
                pluginSlug,
                plugin: pluginLabel,
                lastSync: sync,
                schedule: d.schedule ?? pluginSchedule,
              };
            });
          }
          // B169 (v0.9.5.1): defensive dedupe in case backend ships
          // duplicate table names. Backend was fixed in the same release
          // but this protects future regressions in the API contract.
          const pgTables = Array.from(new Set(p.databases?.postgres?.tables ?? []));
          return pgTables.map((tname: string) => ({
            name: tname,
            pluginSlug,
            plugin: pluginLabel,
            db: "postgres",
            schedule: pluginSchedule,
          }));
        });
        setDatasets(all);
      })
      .catch((err) => console.error("DatasetsPage: failed to load datasets", err))
      .finally(() => setLoading(false));
  }, []);

  const allDbs = Array.from(new Set(datasets.map(d => d.db).filter(Boolean)));
  const allGrains = Array.from(new Set(datasets.map(d => d.grain).filter(Boolean))) as string[];

  const filtered = datasets.filter((d) => {
    const matchesSearch = d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.plugin.toLowerCase().includes(search.toLowerCase());
    const matchesDb = dbFilter === "all" || d.db === dbFilter;
    const matchesGrain = grainFilter === "all" || d.grain === grainFilter;
    const matchesPlugin = !pluginFilter || d.pluginSlug === pluginFilter;
    return matchesSearch && matchesDb && matchesGrain && matchesPlugin;
  });

  return (
    <div className="max-w-[1400px] space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-muted-foreground font-body">
          Browse all datasets registered by installed plugins.
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          {pluginFilter && (
            <button
              onClick={() => updateParam("plugin", null)}
              className="px-2.5 py-1 rounded-full text-xs font-body bg-primary/15 text-primary hover:bg-primary/25 transition-colors flex items-center gap-1"
              title="Clear plugin filter"
            >
              Plugin: {pluginFilter} ✕
            </button>
          )}
          {allDbs.length > 1 && (
            <div className="flex items-center gap-1">
              {["all", ...allDbs].map(db => (
                <button
                  key={db}
                  onClick={() => updateParam("db", db)}
                  className={`px-2.5 py-1 rounded-full text-xs font-body transition-colors ${
                    dbFilter === db
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {db === "all" ? "All DBs" : db}
                </button>
              ))}
            </div>
          )}
          {allGrains.length > 0 && (
            <div className="flex items-center gap-1">
              {["all", ...allGrains].map(g => (
                <button
                  key={g}
                  onClick={() => updateParam("grain", g)}
                  className={`px-2.5 py-1 rounded-full text-xs font-mono-deck transition-colors ${
                    grainFilter === g
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {g === "all" ? "All grains" : g}
                </button>
              ))}
            </div>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter datasets..."
              value={search}
              onChange={(e) => updateParam("search", e.target.value)}
              className="h-9 pl-9 pr-4 rounded-md bg-secondary border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
            />
          </div>
        </div>
      </div>

      {loading && (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <DataTable minWidth="640px" className="text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider sticky left-0 bg-card z-10">Dataset</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Plugin</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Database</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rows</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Grain</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Last Sync</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 sticky left-0 bg-card z-10"><div className="h-4 bg-secondary/50 rounded animate-pulse w-32" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-secondary/50 rounded animate-pulse w-24" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-secondary/50 rounded animate-pulse w-16" /></td>
                  <td className="px-4 py-3 text-right"><div className="h-4 bg-secondary/50 rounded animate-pulse w-12 ml-auto" /></td>
                  <td className="px-4 py-3"><div className="h-4 bg-secondary/50 rounded animate-pulse w-14" /></td>
                  <td className="px-4 py-3 text-right"><div className="h-4 bg-secondary/50 rounded animate-pulse w-20 ml-auto" /></td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        </div>
      )}

      {!loading && datasets.length === 0 && (
        <div className="py-20 text-center border border-dashed border-border rounded-lg">
          <Package className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">No datasets available. Install a plugin to register datasets.</p>
        </div>
      )}

      {!loading && datasets.length > 0 && (() => {
        // Group filtered datasets by plugin display name (slug is on each row)
        const groups: Record<string, Dataset[]> = {};
        filtered.forEach((ds) => {
          (groups[ds.plugin] ??= []).push(ds);
        });
        const pluginNames = Object.keys(groups).sort();

        return pluginNames.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">No datasets match your filter.</p>
        ) : (
          <div className="space-y-6">
            {pluginNames.map((pluginName) => {
              const slug = groups[pluginName][0].pluginSlug;
              return (
                <div key={pluginName}>
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="w-4 h-4 text-primary" />
                    {/* B165 D5: plugin name → /plugin/<slug> */}
                    <Link to={`/plugin/${slug}`} className="font-display text-sm text-foreground hover:text-primary transition-colors">
                      {pluginName}
                    </Link>
                    <span className="text-xs text-muted-foreground">{groups[pluginName].length} table{groups[pluginName].length !== 1 ? "s" : ""}</span>
                  </div>
                  {/* Mobile (<sm): stacked cards. B288.1 (v0.9.11.26.1):
                      replaces the squeezed sticky-both table view with
                      full-width cards so operators can see all the data
                      and tap actions without horizontal scroll. */}
                  <div className="block sm:hidden space-y-2">
                    {groups[pluginName].map((ds) => (
                      <MobileCard
                        key={`${ds.pluginSlug}-${ds.name}-card`}
                        title={
                          <div className="flex items-center gap-2">
                            <Database className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                            <span className="font-mono-deck text-foreground truncate">{ds.name}</span>
                          </div>
                        }
                        actions={
                          <Link
                            to={`/datasets/${ds.pluginSlug}/${encodeURIComponent(ds.name)}`}
                            className="inline-flex items-center justify-center gap-1 text-xs text-primary hover:underline font-body w-full h-8 rounded border border-primary/30 bg-primary/5"
                          >
                            View rows <ExternalLink className="w-3 h-3" />
                          </Link>
                        }
                      >
                        <MobileCardRow label="Database" valueClassName="font-mono-deck text-muted-foreground truncate">
                          {ds.db ? (
                            <Link to={`/connections?plugin=${ds.pluginSlug}`} className="hover:text-primary transition-colors">
                              {ds.db}
                            </Link>
                          ) : "—"}
                        </MobileCardRow>
                        <MobileCardRow label="Rows" valueClassName="font-mono-deck text-foreground">
                          {ds.rows != null ? formatNumber(ds.rows) : "—"}
                        </MobileCardRow>
                        <MobileCardRow label="Grain">
                          {ds.grain ? (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground font-mono-deck">
                              {ds.grain}
                            </span>
                          ) : "—"}
                        </MobileCardRow>
                        <MobileCardRow label="Freshness">
                          <FreshnessPill lastSync={ds.lastSync} schedule={ds.schedule} />
                        </MobileCardRow>
                        <MobileCardRow label="Last sync" valueClassName="text-muted-foreground">
                          {ds.lastSync ? (
                            <span title={formatAbsoluteTime(ds.lastSync)} className="inline-flex items-center gap-1">
                              <Clock className="w-3 h-3" /> {formatRelativeTime(ds.lastSync)}
                            </span>
                          ) : "—"}
                        </MobileCardRow>
                      </MobileCard>
                    ))}
                  </div>

                  {/* Desktop (sm+): the wrapped table. */}
                  <div className="hidden sm:block bg-card rounded-lg border border-border overflow-hidden">
                    <DataTable minWidth="720px" className="text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider sticky left-0 bg-card z-10">Dataset</th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Database</th>
                          <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Rows</th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Grain</th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Freshness</th>
                          <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Last Sync</th>
                          <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider sticky right-0 bg-card z-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {groups[pluginName].map((ds) => (
                          <tr key={`${ds.pluginSlug}-${ds.name}`} className="hover:bg-secondary/30 transition-colors">
                            <td className="px-4 py-3 sticky left-0 bg-card z-10 shadow-[inset_-1px_0_0_var(--border)]">
                              <div className="flex items-center gap-2">
                                <Database className="w-3.5 h-3.5 text-blue-400" />
                                <span className="font-mono-deck text-foreground">{ds.name}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 font-mono-deck text-muted-foreground">
                              {/* B165 D4: db cell links to Connections filtered to this plugin */}
                              {ds.db ? (
                                <Link to={`/connections?plugin=${ds.pluginSlug}`} className="hover:text-primary transition-colors">
                                  {ds.db}
                                </Link>
                              ) : "—"}
                            </td>
                            <td className="px-4 py-3 text-right font-mono-deck text-foreground">
                              {ds.rows != null ? formatNumber(ds.rows) : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {ds.grain ? (
                                <span className="text-xs px-2 py-0.5 rounded-full bg-secondary text-muted-foreground font-mono-deck">
                                  {ds.grain}
                                </span>
                              ) : "—"}
                            </td>
                            <td className="px-4 py-3">
                              <FreshnessPill lastSync={ds.lastSync} schedule={ds.schedule} />
                            </td>
                            <td className="px-4 py-3 text-right text-muted-foreground">
                              <span className="inline-flex items-center justify-end gap-1">
                                {ds.lastSync ? (
                                  <span title={formatAbsoluteTime(ds.lastSync)} className="inline-flex items-center gap-1">
                                    <Clock className="w-3 h-3" /> {formatRelativeTime(ds.lastSync)}
                                  </span>
                                ) : "—"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right sticky right-0 bg-card z-10 shadow-[inset_1px_0_0_var(--border)]">
                              {/* B170 (v0.9.5.2): drilldown to /datasets/:plugin/:table
                                  detail page. Replaces the old B165 D1 affordance
                                  that pointed at /data-port?plugin=&table= — Data
                                  Port is gone as a destination; row browsing is
                                  a drilldown leaf, not a peer page. */}
                              <Link
                                to={`/datasets/${ds.pluginSlug}/${encodeURIComponent(ds.name)}`}
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-body"
                                title="View rows"
                              >
                                View rows <ExternalLink className="w-3 h-3" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </DataTable>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}
    </div>
  );
}
