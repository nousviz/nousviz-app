/**
 * Resources tab on /system/health (B271 / v0.9.11.13).
 *
 * Wraps GET /api/system/resources. Auto-refreshes every 60s.
 * Sections (top to bottom):
 *   1. Refresh + collected_at
 *   2. Server stat cards (disk, memory, swap, load, uptime)
 *   3. Postgres summary row
 *   4. Plugins panel (sortable)
 *   5. Tables panel (sortable)
 *   6. Syncs panel (sortable; default desc on cpu_load_pct_estimate)
 *   7. Largest indexes panel
 *
 * No diagnostic rules / findings list yet — that's B272 in v0.9.11.14.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { RefreshCw, HardDrive, Cpu, Database, AlertTriangle, ChevronDown, ChevronRight, Info } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import FindingsPanel from "./FindingsPanel";

// ── Response shape (matches the backend ResourcesResponse model) ─────

interface ServerCpu { cpu_count: number; cpu_model: string | null; }
interface ServerMemory { total_mb: number; used_mb: number; free_mb: number; available_mb: number; buff_cache_mb: number; }
interface ServerSwap { total_mb: number; used_mb: number; free_mb: number; }
interface ServerDisk { path: string; total_gb: number; used_gb: number; free_gb: number; used_pct: number; }
interface ServerLoad { load_1m: number; load_5m: number; load_15m: number; }
interface ServerResources {
  cpu: ServerCpu | null;
  memory: ServerMemory | null;
  swap: ServerSwap | null;
  disk_root: ServerDisk | null;
  load: ServerLoad | null;
  uptime_seconds: number | null;
}
interface PostgresSummary {
  db_size_mb: number;
  cache_hit_pct: number;
  active_connections: number;
  idle_connections: number;
  max_connections: number;
  pg_stat_statements_installed: boolean;
}
interface TableStat {
  schema: string;
  name: string;
  plugin: string | null;
  total_size_mb: number;
  data_mb: number;
  index_mb: number;
  rows: number;
  dead_rows: number;
  dead_pct: number;
  last_vacuum: string | null;
  last_analyze: string | null;
  seq_scan_count: number;
  idx_scan_count: number;
  seq_scan_pct: number;
}
interface PluginStat {
  id: string;
  table_count: number;
  total_size_mb: number;
  total_rows: number;
  last_sync_at: string | null;
  sync_schedule_cron: string | null;
}
interface SyncStat {
  plugin_id: string;
  schedule_cron: string;
  schedule_interval_seconds: number;
  runs_24h: number;
  errors_24h: number;
  avg_duration_ms: number | null;
  max_duration_ms: number | null;
  cpu_load_pct_estimate: number;
}
interface IndexStat {
  schema: string;
  table: string;
  name: string;
  size_mb: number;
  scans_lifetime: number;
  tuples_read: number;
}
interface ResourcesResponse {
  collected_at: string;
  server: ServerResources;
  postgres: PostgresSummary;
  tables: TableStat[];
  plugins: PluginStat[];
  syncs: SyncStat[];
  indexes_largest: IndexStat[];
}

// ── Color thresholds ────────────────────────────────────────────────

function diskColor(pct: number): string {
  if (pct > 85) return "text-red-400";
  if (pct > 70) return "text-yellow-400";
  return "text-green-400";
}
function memoryColor(free_mb: number, swap_mb: number): string {
  if (free_mb < 200) return "text-red-400";
  if (free_mb < 500) return swap_mb === 0 ? "text-red-400" : "text-yellow-400";
  return "text-green-400";
}
function swapColor(total_mb: number, mem_free_mb: number): string {
  if (total_mb === 0 && mem_free_mb < 500) return "text-red-400";
  if (total_mb === 0) return "text-yellow-400";
  return "text-green-400";
}
function syncCpuColor(pct: number): string {
  if (pct > 60) return "text-red-400";
  if (pct > 30) return "text-yellow-400";
  return "text-green-400";
}
function deadPctColor(pct: number): string {
  if (pct > 30) return "text-red-400";
  if (pct > 10) return "text-yellow-400";
  return "text-muted-foreground";
}
function seqScanColor(pct: number): string {
  if (pct > 50) return "text-red-400";
  if (pct > 25) return "text-yellow-400";
  return "text-muted-foreground";
}
function cacheHitColor(pct: number): string {
  if (pct < 95) return "text-red-400";
  if (pct < 99) return "text-yellow-400";
  return "text-green-400";
}

function fmtMb(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
}

function fmtUptime(seconds: number | null): string {
  if (!seconds) return "—";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  if (d > 0) return `${d}d ${h}h`;
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function fmtMs(ms: number | null): string {
  if (ms === null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`;
  return `${ms} ms`;
}

// ── StatCard ────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, color, icon: Icon,
}: { label: string; value: string; sub?: string; color?: string; icon?: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="bg-card border border-border rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-meta uppercase tracking-wider text-muted-foreground">
        {Icon && <Icon className="w-3 h-3" />}
        {label}
      </div>
      <p className={cn("text-section-header mt-1", color ?? "text-foreground")}>{value}</p>
      {sub && <p className="text-meta text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Sortable table primitive ─────────────────────────────────────────

interface ColumnDef<T> {
  key: keyof T | string;
  label: string;
  className?: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number;
}

function SortableTable<T>({ columns, rows, defaultSort, defaultDir = "desc" }: {
  columns: ColumnDef<T>[];
  rows: T[];
  defaultSort: keyof T | string;
  defaultDir?: "asc" | "desc";
}) {
  const [sortKey, setSortKey] = useState<keyof T | string>(defaultSort);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultDir);

  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return rows;
    const sortFn = col.sortValue ?? ((r: T) => (r as Record<string, unknown>)[col.key as string] as string | number);
    return [...rows].sort((a, b) => {
      const va = sortFn(a);
      const vb = sortFn(b);
      if (va === vb) return 0;
      const cmp = va < vb ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir, columns]);

  function toggleSort(k: keyof T | string) {
    if (k === sortKey) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border">
            {columns.map((c) => (
              <th
                key={String(c.key)}
                onClick={() => toggleSort(c.key)}
                className={cn(
                  "px-2 py-1.5 text-left text-meta uppercase tracking-wider text-muted-foreground cursor-pointer hover:text-foreground transition-colors",
                  c.className,
                )}
              >
                {c.label} {sortKey === c.key && (sortDir === "asc" ? "↑" : "↓")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={i} className="border-b border-border/50 hover:bg-secondary/20 transition-colors">
              {columns.map((c) => (
                <td key={String(c.key)} className={cn("px-2 py-1.5", c.className)}>
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Section wrapper ─────────────────────────────────────────────────

function Section({ title, count, children, defaultOpen = true }: { title: string; count?: number; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-3 py-2 flex items-center gap-2 text-meta uppercase tracking-wider text-muted-foreground hover:bg-secondary/40 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <span className="font-semibold">{title}</span>
        {count !== undefined && <span className="opacity-70">{count}</span>}
      </button>
      {open && <div className="p-3 border-t border-border">{children}</div>}
    </div>
  );
}

// ── Main panel ──────────────────────────────────────────────────────

export default function ResourcesPanel() {
  const [data, setData] = useState<ResourcesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (fresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const url = fresh ? "/api/system/resources?fresh=true" : "/api/system/resources";
      const res = await apiFetch(url);
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load resources");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setInterval(() => load(), 60_000);
    return () => clearInterval(t);
  }, [load]);

  if (loading && !data) {
    return <div className="py-12 text-center text-muted-foreground">Loading resources…</div>;
  }
  if (error && !data) {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
        {error}
      </div>
    );
  }
  if (!data) return null;

  const s = data.server;
  const collected = new Date(data.collected_at);

  // ── Lead-summary derivation (B271 v0.9.11.13.1 UX restructure) ─────
  // The single most-meaningful stats, computed once and shown at the top
  // so the operator sees the state of the platform in 3 seconds.
  const totalSyncCpuPct = data.syncs.reduce((acc, sy) => acc + sy.cpu_load_pct_estimate, 0);
  const slowestSync = [...data.syncs].sort((a, b) => b.cpu_load_pct_estimate - a.cpu_load_pct_estimate)[0];
  const failingSyncs = data.syncs.filter(sy => sy.errors_24h > 0);
  const dominantPlugin = data.plugins[0]; // sorted by size desc
  const dominantPluginPct = dominantPlugin && data.postgres.db_size_mb > 0
    ? Math.round(dominantPlugin.total_size_mb / data.postgres.db_size_mb * 100)
    : 0;
  const oldestVacuum = [...data.tables]
    .filter(t => t.last_vacuum && t.total_size_mb > 50)
    .sort((a, b) => new Date(a.last_vacuum!).getTime() - new Date(b.last_vacuum!).getTime())[0];
  const unusedIndexCount = data.indexes_largest.filter(idx => idx.scans_lifetime === 0).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-meta text-muted-foreground">
          Collected {formatRelativeTime(data.collected_at)} ({collected.toLocaleTimeString()})
        </p>
        <button
          onClick={() => load(true)}
          disabled={loading}
          className="h-8 px-3 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          title="Force fresh collection (bypass 30s cache)"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* B272 v0.9.11.18: diagnostic findings panel — turns raw metrics
          below into named, actionable issues with severity + recommendation. */}
      <FindingsPanel />

      {/* B271 v0.9.11.13.1: lead summary block — operator sees the state
          in 3 seconds. The full diagnostic engine ships in B272 (v0.9.11.14)
          and replaces this with a real findings list. */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">At a glance</h2>
          <span className="text-meta text-muted-foreground italic">
            Auto-detected issues + recommendations land in v0.9.11.17 (B272 — diagnostic engine).
          </span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-secondary/40 rounded-md p-3">
            <p className="text-meta uppercase tracking-wider text-muted-foreground">Total sync CPU load</p>
            <p className={cn("text-section-header mt-1", syncCpuColor(totalSyncCpuPct))}>
              {totalSyncCpuPct.toFixed(0)}%
            </p>
            <p className="text-meta text-muted-foreground mt-1">
              {slowestSync ? `Worst: ${slowestSync.plugin_id} (${slowestSync.cpu_load_pct_estimate.toFixed(0)}%)` : "No active syncs"}
            </p>
          </div>
          <div className="bg-secondary/40 rounded-md p-3">
            <p className="text-meta uppercase tracking-wider text-muted-foreground">Failing syncs (24h)</p>
            <p className={cn("text-section-header mt-1", failingSyncs.length > 0 ? "text-red-400" : "text-green-400")}>
              {failingSyncs.length}
            </p>
            <p className="text-meta text-muted-foreground mt-1">
              {failingSyncs.length > 0
                ? failingSyncs.slice(0, 2).map(sy => sy.plugin_id).join(", ") + (failingSyncs.length > 2 ? "…" : "")
                : "All healthy"}
            </p>
          </div>
          <div className="bg-secondary/40 rounded-md p-3">
            <p className="text-meta uppercase tracking-wider text-muted-foreground">Dominant plugin</p>
            <p className="text-section-header mt-1 text-foreground">
              {dominantPlugin ? <>{fmtMb(dominantPlugin.total_size_mb)}</> : "—"}
            </p>
            <p className="text-meta text-muted-foreground mt-1">
              {dominantPlugin ? `${dominantPlugin.id} — ${dominantPluginPct}% of database` : "No plugins"}
            </p>
          </div>
          <div className="bg-secondary/40 rounded-md p-3">
            <p className="text-meta uppercase tracking-wider text-muted-foreground">Database health</p>
            <p className={cn("text-section-header mt-1", cacheHitColor(data.postgres.cache_hit_pct))}>
              {data.postgres.cache_hit_pct.toFixed(1)}%
            </p>
            <p className="text-meta text-muted-foreground mt-1">
              cache hit · {fmtMb(data.postgres.db_size_mb)} total
            </p>
          </div>
        </div>
        {(s.swap?.total_mb === 0 && (s.memory?.available_mb ?? 0) < 500) && (
          <div className="rounded-md border border-yellow-500/20 bg-yellow-500/5 p-2 flex items-center gap-2 text-xs text-yellow-300">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            No swap configured and memory free is low — OOM-kill risk if usage spikes.
          </div>
        )}
        {oldestVacuum && new Date(oldestVacuum.last_vacuum!).getTime() < Date.now() - 7 * 86400 * 1000 && (
          <div className="rounded-md border border-yellow-500/20 bg-yellow-500/5 p-2 flex items-center gap-2 text-xs text-yellow-300">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>
              <span className="font-mono-deck">{oldestVacuum.name}</span> hasn't been vacuumed in {Math.round((Date.now() - new Date(oldestVacuum.last_vacuum!).getTime()) / (86400 * 1000))} days.
              Stale planner stats may slow queries on this table.
            </span>
          </div>
        )}
        {unusedIndexCount > 0 && (
          <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-2 flex items-center gap-2 text-xs text-blue-300">
            <Info className="w-3.5 h-3.5 shrink-0" />
            <span>{unusedIndexCount} index{unusedIndexCount > 1 ? "es" : ""} in the top-20 list have never been used. They occupy disk + slow writes; safe to drop.</span>
          </div>
        )}
      </div>

      {/* Server */}
      <Section title="Server" defaultOpen>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <StatCard
            label="Disk"
            icon={HardDrive}
            value={s.disk_root ? `${s.disk_root.used_pct}%` : "—"}
            sub={s.disk_root ? `${s.disk_root.used_gb} / ${s.disk_root.total_gb} GB` : undefined}
            color={s.disk_root ? diskColor(s.disk_root.used_pct) : undefined}
          />
          <StatCard
            label="Memory free"
            value={s.memory ? fmtMb(s.memory.available_mb) : "—"}
            sub={s.memory ? `of ${fmtMb(s.memory.total_mb)}` : undefined}
            color={s.memory && s.swap ? memoryColor(s.memory.available_mb, s.swap.total_mb) : undefined}
          />
          <StatCard
            label="Swap"
            value={s.swap ? `${fmtMb(s.swap.used_mb)} / ${fmtMb(s.swap.total_mb)}` : "—"}
            sub={s.swap?.total_mb === 0 ? "no swap configured" : undefined}
            color={s.swap && s.memory ? swapColor(s.swap.total_mb, s.memory.available_mb) : undefined}
          />
          <StatCard
            label="Load"
            value={s.load ? `${s.load.load_1m}` : "—"}
            sub={s.load ? `${s.load.load_5m} / ${s.load.load_15m}` : undefined}
          />
          <StatCard
            label="Uptime"
            value={fmtUptime(s.uptime_seconds)}
          />
          <StatCard
            label="CPU"
            icon={Cpu}
            value={s.cpu ? String(s.cpu.cpu_count) : "—"}
            sub={s.cpu?.cpu_model ?? undefined}
          />
        </div>
        {/* Note: the "no swap + low memory" warning lives in the lead-summary
            block above; not duplicated here. */}
      </Section>

      {/* Postgres */}
      <Section title="Postgres" defaultOpen>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatCard
            label="DB size"
            icon={Database}
            value={fmtMb(data.postgres.db_size_mb)}
          />
          <StatCard
            label="Cache hit"
            value={`${data.postgres.cache_hit_pct.toFixed(2)}%`}
            color={cacheHitColor(data.postgres.cache_hit_pct)}
          />
          <StatCard
            label="Connections"
            value={`${data.postgres.active_connections + data.postgres.idle_connections}`}
            sub={`${data.postgres.active_connections} active / ${data.postgres.idle_connections} idle / ${data.postgres.max_connections} max`}
          />
          <StatCard
            label="pg_stat_statements"
            value={data.postgres.pg_stat_statements_installed ? "installed" : "missing"}
            color={data.postgres.pg_stat_statements_installed ? "text-green-400" : "text-yellow-400"}
            sub={data.postgres.pg_stat_statements_installed ? undefined : "slow-query visibility unavailable"}
          />
        </div>
      </Section>

      {/* Detail tables — collapsed by default to reduce noise.
          Operator opens what they need to investigate. The lead-summary
          block above surfaces the headlines. */}
      <Section title="Plugins" count={data.plugins.length} defaultOpen={false}>
        <SortableTable
          columns={[
            { key: "id", label: "Plugin", render: (r) => <span className="font-mono-deck">{r.id}</span> },
            { key: "table_count", label: "Tables", render: (r) => r.table_count },
            { key: "total_size_mb", label: "Size", render: (r) => fmtMb(r.total_size_mb), sortValue: (r) => r.total_size_mb },
            { key: "total_rows", label: "Rows", render: (r) => r.total_rows.toLocaleString() },
            { key: "last_sync_at", label: "Last sync", render: (r) => r.last_sync_at ? formatRelativeTime(r.last_sync_at) : "—" },
            { key: "sync_schedule_cron", label: "Schedule", render: (r) => <span className="font-mono-deck text-muted-foreground">{r.sync_schedule_cron ?? "—"}</span> },
          ] as ColumnDef<PluginStat>[]}
          rows={data.plugins}
          defaultSort="total_size_mb"
        />
      </Section>

      {/* Tables */}
      <Section title="Tables (top 50)" count={data.tables.length} defaultOpen={false}>
        <SortableTable
          columns={[
            { key: "name", label: "Table", render: (r) => <span className="font-mono-deck">{r.schema === "public" ? r.name : `${r.schema}.${r.name}`}</span> },
            { key: "plugin", label: "Plugin", render: (r) => r.plugin ? <span className="text-meta px-1.5 py-0.5 rounded bg-secondary text-foreground">{r.plugin}</span> : <span className="text-muted-foreground">—</span> },
            { key: "total_size_mb", label: "Total", render: (r) => fmtMb(r.total_size_mb), sortValue: (r) => r.total_size_mb },
            { key: "data_mb", label: "Data", render: (r) => fmtMb(r.data_mb), sortValue: (r) => r.data_mb },
            { key: "index_mb", label: "Index", render: (r) => fmtMb(r.index_mb), sortValue: (r) => r.index_mb },
            { key: "rows", label: "Rows", render: (r) => r.rows.toLocaleString() },
            { key: "dead_pct", label: "Dead %", render: (r) => <span className={deadPctColor(r.dead_pct)}>{r.dead_pct}%</span> },
            { key: "seq_scan_pct", label: "Seq %", render: (r) => <span className={seqScanColor(r.seq_scan_pct)}>{r.seq_scan_pct}%</span> },
            { key: "last_vacuum", label: "Last vacuum", render: (r) => r.last_vacuum ? formatRelativeTime(r.last_vacuum) : "—" },
          ] as ColumnDef<TableStat>[]}
          rows={data.tables}
          defaultSort="total_size_mb"
        />
      </Section>

      {/* Syncs */}
      <Section title="Syncs (24h)" count={data.syncs.length} defaultOpen={false}>
        <SortableTable
          columns={[
            { key: "plugin_id", label: "Plugin", render: (r) => <span className="font-mono-deck">{r.plugin_id}</span> },
            { key: "schedule_cron", label: "Schedule", render: (r) => <span className="font-mono-deck text-muted-foreground">{r.schedule_cron || "—"}</span> },
            { key: "runs_24h", label: "Runs", render: (r) => r.runs_24h },
            { key: "errors_24h", label: "Errors", render: (r) => <span className={r.errors_24h > 0 ? "text-red-400" : "text-muted-foreground"}>{r.errors_24h}</span> },
            { key: "avg_duration_ms", label: "Avg duration", render: (r) => fmtMs(r.avg_duration_ms ?? null), sortValue: (r) => r.avg_duration_ms ?? 0 },
            { key: "max_duration_ms", label: "Max duration", render: (r) => fmtMs(r.max_duration_ms ?? null), sortValue: (r) => r.max_duration_ms ?? 0 },
            { key: "cpu_load_pct_estimate", label: "CPU est %", render: (r) => <span className={cn("font-semibold", syncCpuColor(r.cpu_load_pct_estimate))}>{r.cpu_load_pct_estimate.toFixed(1)}%</span> },
          ] as ColumnDef<SyncStat>[]}
          rows={data.syncs}
          defaultSort="cpu_load_pct_estimate"
        />
      </Section>

      {/* Largest indexes */}
      <Section title="Largest indexes" count={data.indexes_largest.length} defaultOpen={false}>
        <SortableTable
          columns={[
            { key: "name", label: "Index", render: (r) => <span className="font-mono-deck">{r.name}</span> },
            { key: "table", label: "Table", render: (r) => <span className="font-mono-deck text-muted-foreground">{r.table}</span> },
            { key: "size_mb", label: "Size", render: (r) => fmtMb(r.size_mb), sortValue: (r) => r.size_mb },
            { key: "scans_lifetime", label: "Scans", render: (r) => <span className={r.scans_lifetime === 0 ? "text-yellow-400" : ""}>{r.scans_lifetime.toLocaleString()}</span> },
            { key: "tuples_read", label: "Tuples read", render: (r) => r.tuples_read.toLocaleString() },
          ] as ColumnDef<IndexStat>[]}
          rows={data.indexes_largest}
          defaultSort="size_mb"
        />
      </Section>
    </div>
  );
}
