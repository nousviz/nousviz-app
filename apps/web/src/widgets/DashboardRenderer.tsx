import { useState, useEffect, useRef, useSyncExternalStore, Suspense } from "react";
import GridLayoutImport from "react-grid-layout";
const GridLayoutLib = GridLayoutImport as unknown as React.ComponentType<any>;
import { useQuery } from "@tanstack/react-query";
import { apiFetch, query, getDashboardSpec, NotFoundError } from "@/lib/api";
import KpiWidget from "./KpiWidget";
import TableWidget from "./TableWidget";
import ChartWidget from "./ChartWidget";
import ProgressBar, { type ProgressStatus } from "./ProgressBar";
import { HeadingWidget, TextWidget, DividerWidget } from "./TextWidget";
import {
  subscribePluginComponents,
  getPluginComponentsSnapshot,
  getPluginLoaderCompletedSnapshot,
} from "./plugin-components";
import PluginActions, { type PluginAction } from "@/components/plugins/PluginActions";
import ErrorBoundary from "@/components/ErrorBoundary";
import { AlertCircle } from "lucide-react";

// P119: small wrapper that fetches a plugin's manifest to read `actions:`
// for the dashboard_header slot. Keeps DashboardRenderer's main state
// shape untouched — this is an additive visual band above the charts.
function DashboardHeaderActions({ pluginId }: { pluginId: string }) {
  const [actions, setActions] = useState<PluginAction[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    apiFetch(`/api/plugins/${pluginId}`)
      .then((r) => r.json())
      .then((manifest) => {
        if (cancelled) return;
        setActions(Array.isArray(manifest.actions) ? manifest.actions : []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [pluginId, tick]);

  const headerActions = actions.filter((a) => a.slot === "dashboard_header");
  if (headerActions.length === 0) return null;

  return (
    <div className="flex justify-end">
      <PluginActions
        pluginId={pluginId}
        actions={actions}
        slot="dashboard_header"
        onAfterAction={() => setTick((t) => t + 1)}
      />
    </div>
  );
}

// P109: refresh_seconds bounds for live panels. Below 2s hammers the DB;
// above 3600s isn't "live" in any meaningful sense.
const MIN_REFRESH_SEC = 2;
const MAX_REFRESH_SEC = 3600;
const DEFAULT_REFRESH_SEC = 30;

function clampRefreshSeconds(s: number | undefined, fallback: number): number {
  const v = typeof s === "number" && !Number.isNaN(s) ? s : fallback;
  return Math.max(MIN_REFRESH_SEC, Math.min(MAX_REFRESH_SEC, v));
}

interface WidgetSpec {
  type: string;
  position: { row: number; col: number; width: number };
  config: Record<string, unknown>;
}

interface PanelSpec {
  id?: string;
  type: string;           // stat | table | line_chart | bar_chart | progress_bar | custom
  label?: string;
  title?: string;
  query?: string;         // raw SQL — panels format
  columns?: { key: string; label: string; type?: string }[];
  fallback_empty?: boolean;
  component?: string;     // for type: custom — name in plugin-components registry
  config?: Record<string, unknown>; // extra config passed to custom components
  position?: { row: number; col: number; width: number };
  // P109: live polling — any panel type can opt in
  live?: boolean;
  refresh_seconds?: number;
}

export interface DashboardSpec {
  name: string;
  label: string;
  description: string;
  db_engine?: string;  // "postgres" (default) — plugins may declare other engines
  widgets: WidgetSpec[];
  panels: PanelSpec[];  // alternate simpler format — normalised to widgets below
  filters: Record<string, unknown>[];
  // P109: dashboard-level default for panels that set live:true without
  // their own refresh_seconds
  refresh_seconds?: number;
}

interface DashboardRendererProps {
  pluginId: string;
  dashboardName: string;
  /** Optional pre-loaded spec — skips the API fetch when provided. */
  preloadedSpec?: DashboardSpec;
}

/**
 * Normalise the simple `panels` format to the richer `widgets` format.
 *
 * panels format (used by plugin dashboards with raw SQL):
 *   - type: stat | table | line_chart | bar_chart
 *   - query: "SELECT count(*) AS value FROM …"
 *   - columns: [{key, label, type}]
 *
 * Normalised to widgets with:
 *   - type: kpi (for stat), table, line_chart, bar_chart
 *   - config.custom_sql — DashboardRenderer executes this verbatim
 *   - position auto-assigned: stats fill row 0 (width 1 each), tables/charts get row 1+ (width 4)
 */
function normalisePanels(panels: PanelSpec[]): WidgetSpec[] {
  const stats   = panels.filter(p => p.type === "stat");
  const customs = panels.filter(p => p.type === "custom");
  const progressBars = panels.filter(p => p.type === "progress_bar");
  const others  = panels.filter(p =>
    p.type !== "stat"
    && p.type !== "custom"
    && p.type !== "progress_bar"
  );
  const result: WidgetSpec[] = [];

  // P109 helper: carry live / refresh_seconds through to the widget config.
  const liveConfig = (p: PanelSpec) => ({
    ...(p.live ? { live: true } : {}),
    ...(p.refresh_seconds != null ? { refresh_seconds: p.refresh_seconds } : {}),
  });

  // Stats → row 0, equal width
  stats.forEach((p, i) => {
    result.push({
      type: "kpi",
      position: { row: 0, col: i, width: 1 },
      config: {
        label: p.label || p.title || p.id || "",
        custom_sql: p.query?.trim(),
        fallback_empty: p.fallback_empty ?? true,
        ...liveConfig(p),
      },
    });
  });

  let nextRow = 1;

  // Custom widgets — preserve type + component, full width unless position declared
  customs.forEach((p) => {
    result.push({
      type: "custom",
      position: p.position || { row: nextRow++, col: 0, width: 4 },
      config: { component: p.component, ...p.config, ...liveConfig(p) },
    });
  });

  // P109: progress_bar panels — keep on their own rows, half-width by default
  progressBars.forEach((p) => {
    result.push({
      type: "progress_bar",
      position: p.position || { row: nextRow++, col: 0, width: 2 },
      config: {
        label: p.label || p.title || p.id || "",
        custom_sql: p.query?.trim(),
        fallback_empty: p.fallback_empty ?? true,
        ...liveConfig(p),
      },
    });
  });

  // Tables / charts → rows after customs, full width
  others.forEach((p: PanelSpec & { x_key?: string; y_key?: string; x_label?: string; y_label?: string }) => {
    const type = p.type === "table" ? "table" : p.type;
    // Convert panel columns [{key, label}] → widget columns [{field, label}]
    const widgetCols = (p.columns || []).map(c => ({
      field: c.key,
      label: c.label,
      ...(c.type === "datetime" ? { format: "datetime" as const } : {}),
    }));
    result.push({
      type,
      position: { row: nextRow++, col: 0, width: 4 },
      config: {
        title: p.label || p.title || "",
        custom_sql: p.query?.trim(),
        columns: widgetCols,
        // Chart-specific: map x_key/y_key → x/y for the chart renderer.
        // B158 (v0.9.4.8): also pass y_label → labels so ChartWidget's
        // legend/tooltip show "Programs" / "Brands" / etc. instead of
        // the raw column alias from `SELECT ... AS y`. ChartWidget
        // doesn't currently render an x-axis title, so x_label is
        // ignored for now (not silently — the YAML field is documented
        // and a future ChartWidget update can plumb it through).
        ...(p.x_key ? { x: p.x_key, y: [p.y_key || "y"] } : {}),
        ...(p.y_label ? { labels: [p.y_label] } : {}),
        fallback_empty: p.fallback_empty ?? true,
        ...liveConfig(p),
      },
    });
  });

  return result;
}

// Build SQL from widget config. The YAML-declared `period` is the only source
// of the date window — there is no UI override (B222: removed v0.9.7.5).
function buildQuery(widget: WidgetSpec, dbEngine?: string): string | null {
  const c = widget.config;

  // Custom SQL (from panels format) takes priority — no dataset needed
  if (c.custom_sql) return (c.custom_sql as string).trim();

  const dataset = c.dataset as string;
  if (!dataset) return null;

  const isPg = dbEngine === "postgres";

  // Resolve days from widget config (YAML default)
  const resolveDays = () => {
    const period = (c.period as string) || "30d";
    return parseInt(period) || 30;
  };

  // DB-specific syntax helpers
  const final = isPg ? "" : " FINAL";
  const dateFilter = (days: number, dateCol: string = "date") =>
    days >= 9999
      ? "1=1"
      : isPg
        ? `${dateCol} >= CURRENT_DATE - INTERVAL '${days} days'`
        : `${dateCol} >= today() - ${days}`;

  switch (widget.type) {
    case "kpi": {
      const metric = c.metric as string;
      const expression = c.expression as string;
      const days = resolveDays();
      const dateCol = (c.date_column as string) || "date";
      const select = expression || `sum(${metric})`;
      const whereClause = c.no_date_filter ? "1=1" : dateFilter(days, dateCol);
      return `SELECT ${select} as value FROM ${dataset}${final} WHERE ${whereClause}`;
    }
    case "line_chart":
    case "bar_chart":
    case "stacked_bar_chart": {
      const x = c.x as string;
      const yRaw = c.y;
      const y: string[] = Array.isArray(yRaw) ? yRaw : [yRaw as string];
      const aggRaw = c.aggregations as Record<string, string> | undefined;
      const days = resolveDays();
      const limit = (c.limit as number) || 100;
      const sort = c.sort as string;
      const dateCol = (c.date_column as string) || "date";

      const agg = (col: string) => {
        const fn = aggRaw?.[col] || "sum";
        return `${fn}(${col}) as ${col}`;
      };

      const whereClause = c.no_date_filter ? "1=1" : dateFilter(days, dateCol);

      if (x === "date" || x === dateCol) {
        const selects = y.map(agg).join(", ");
        return `SELECT ${x}, ${selects} FROM ${dataset}${final} WHERE ${whereClause} GROUP BY ${x} ORDER BY ${x}`;
      } else {
        const yCol = y[0];
        const aggFn = aggRaw?.[yCol] || "sum";
        return `SELECT ${x}, ${aggFn}(${yCol}) as ${yCol} FROM ${dataset}${final} WHERE ${whereClause} GROUP BY ${x} ORDER BY ${yCol} ${sort === "desc" ? "DESC" : "ASC"} LIMIT ${limit}`;
      }
    }
    case "table": {
      const columns = c.columns as { field: string; expression?: string }[];
      const groupBy = c.group_by as string | string[];
      const sortBy = c.sort_by as string;
      const sortDir = (c.sort_dir as string) || "desc";
      const limit = (c.limit as number) || 20;
      const days = resolveDays();
      const dateCol = (c.date_column as string) || "date";

      const groups = Array.isArray(groupBy) ? groupBy : groupBy ? [groupBy] : [];

      const plainCols: string[] = [];
      const exprCols: string[] = [];

      for (const col of columns) {
        if (col.expression) {
          exprCols.push(`${col.expression} as ${col.field}`);
        } else if (groups.includes(col.field)) {
          plainCols.push(col.field);
        } else {
          plainCols.push(`sum(${col.field}) as ${col.field}`);
        }
      }

      const selects = [...plainCols, ...exprCols];
      const whereClause = c.no_date_filter ? "1=1" : dateFilter(days, dateCol);
      let sql = `SELECT ${selects.join(", ")} FROM ${dataset}${final} WHERE ${whereClause}`;
      if (groups.length > 0) sql += ` GROUP BY ${groups.join(", ")}`;

      const customHaving = c.custom_having as string | undefined;
      if (customHaving) sql += ` HAVING ${customHaving}`;

      if (sortBy) sql += ` ORDER BY ${sortBy} ${sortDir.toUpperCase()}`;
      sql += ` LIMIT ${limit}`;
      return sql;
    }
    default:
      return null;
  }
}

// Individual widget renderer with data fetching
function WidgetRenderer({ widget, dbEngine, pluginId, dashboardName, dashboardRefreshSeconds }: { widget: WidgetSpec; dbEngine?: string; pluginId: string; dashboardName: string; dashboardRefreshSeconds?: number }) {
  // B223 (v0.9.7.6): subscribe to the registry so a late `registerPluginComponent`
  // (race with navigation, runtime-trusted plugin) re-resolves without a manual reload.
  const components = useSyncExternalStore(
    subscribePluginComponents,
    getPluginComponentsSnapshot,
    getPluginComponentsSnapshot,
  );
  // v0.10.0.5.1: also subscribe to the loader-completion flag. While the
  // loader is still walking /api/plugins (which can take 5-10s with 17+
  // installed plugins), show a neutral "Loading widget…" placeholder
  // instead of the alarming "Unknown custom component" error. The error
  // is only correct AFTER the loader has demonstrably finished and the
  // widget still isn't registered.
  const pluginLoaderDone = useSyncExternalStore(
    subscribePluginComponents,
    getPluginLoaderCompletedSnapshot,
    getPluginLoaderCompletedSnapshot,
  );

  // Layout / text widgets — no data fetch, render inline (v0.10.1.0).
  if (widget.type === "heading") {
    return <HeadingWidget text={(widget.config.text as string) || (widget.config.label as string) || ""} level={widget.config.level as "h1" | "h2" | "h3" | undefined} />;
  }
  if (widget.type === "text") {
    return <TextWidget text={(widget.config.text as string) || ""} />;
  }
  if (widget.type === "divider") {
    return <DividerWidget />;
  }

  // Custom widgets don't fetch data — they manage their own state
  if (widget.type === "custom") {
    const componentName = widget.config.component as string;
    const Component = components[componentName];
    if (!Component) {
      if (!pluginLoaderDone) {
        // Skeleton matches the bare card a custom plugin component
        // typically renders inside: header strip + body block. Cleaner
        // visual handoff than literal "Loading widget…" text.
        return (
          <div className="bg-card rounded-lg border border-border p-4 animate-pulse space-y-3">
            <div className="h-3 w-24 bg-secondary rounded" />
            <div className="h-24 bg-secondary/40 rounded" />
          </div>
        );
      }
      return (
        <div className="bg-card rounded-lg border border-red-500/30 p-4 text-xs text-red-400">
          Unknown custom component: {componentName}
        </div>
      );
    }
    // B154 (v0.9.4.6): wrap each custom plugin component in its own
    // ErrorBoundary. Without this, a single broken plugin widget
    // (e.g. one whose bundle externalises React and fails to import)
    // bubbles up to the route-level ErrorBoundary in AppLayout and
    // takes out the whole page — sidebar, tabs, every other panel.
    // The fallback renders an inline card so the rest of the dashboard
    // continues to function.
    return (
      <ErrorBoundary
        context={`plugin-widget:${pluginId}/${componentName}`}
        fallback={(error, reset) => (
          <div className="bg-card rounded-lg border border-amber-500/30 p-4 text-xs space-y-2">
            <div className="text-amber-400 font-medium">
              Widget failed to render: {componentName}
            </div>
            <div className="text-muted-foreground">
              {error.message}
            </div>
            <button
              type="button"
              onClick={reset}
              className="text-[11px] text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        )}
      >
        <Suspense fallback={
          <div className="bg-card rounded-lg border border-border p-4 animate-pulse space-y-3">
            <div className="h-3 w-24 bg-secondary rounded" />
            <div className="h-24 bg-secondary/40 rounded" />
          </div>
        }>
          <Component pluginId={pluginId} dashboardName={dashboardName} config={widget.config} />
        </Suspense>
      </ErrorBoundary>
    );
  }

  return <DataWidgetRenderer widget={widget} dbEngine={dbEngine} dashboardRefreshSeconds={dashboardRefreshSeconds} />;
}

// Built-in widget renderer with data fetching.
//
// v0.10.0.7.2 (Phase 14 / P14.1): per-widget data fetch moved to TanStack
// Query. Two widgets that resolve to the same SQL string now share one
// cache entry — relevant when an operator has multiple dashboards binding
// the same metric, or when a dashboard re-mounts after navigation. The
// per-widget "Loading widget…" flash on revisit disappears (cache hit).
// P109 live polling is now declarative via TanStack's refetchInterval;
// backgrounded tabs stop polling automatically (TanStack v5 default).
function DataWidgetRenderer({
  widget,
  dbEngine,
  dashboardRefreshSeconds,
}: {
  widget: WidgetSpec;
  dbEngine?: string;
  // P109: dashboard-level default for live polling
  dashboardRefreshSeconds?: number;
}) {
  // Pre-compute SQL + polling config so they can drive the query key + opts.
  const sql = buildQuery(widget, dbEngine);
  const live = widget.config?.live as boolean | undefined;
  const refreshSec = clampRefreshSeconds(
    widget.config?.refresh_seconds as number | undefined,
    dashboardRefreshSeconds ?? DEFAULT_REFRESH_SEC,
  );

  const {
    data: queryResult,
    isLoading,
    error: queryError,
  } = useQuery({
    // Cache key is the SQL itself — widgets with identical SQL share data.
    queryKey: ["widget-query", dbEngine || "postgres", sql || "__empty__"],
    queryFn: () => query(sql!, undefined, dbEngine),
    enabled: !!sql,                             // skip when buildQuery returned null
    refetchInterval: live ? refreshSec * 1000 : false,
    // TanStack v5 default: refetchIntervalInBackground = false → no
    // polling when document.hidden. Closes Phase 12 §I6 for widget polls.
  });

  const data = queryResult?.rows ?? null;
  const loading = !sql ? false : isLoading;

  // B291 (v0.10.0.4): when a fusion-bound widget hits a missing-view
  // error (operator unpublished or deleted the bound fusion), surface
  // an actionable message instead of the raw `relation does not exist`
  // Postgres error. Non-fusion widgets and non-matching errors pass
  // through unchanged.
  const error = queryError
    ? queryError instanceof Error ? queryError.message : "Query failed"
    : null;

  // Show empty state only when query succeeded but returned no data
  if (!loading && !error && data && data.length === 0 && widget.config?.fallback_empty) {
    if (widget.type === "kpi") {
      return (
        <KpiWidget
          label={(widget.config.label as string) || ""}
          value={0}
          format={widget.config.format as "currency" | "number" | "percent"}
          loading={false}
        />
      );
    }
    if (widget.type === "table") {
      return (
        <TableWidget
          title={(widget.config.title as string) || ""}
          columns={(widget.config.columns as { field: string; label: string }[]) || []}
          rows={[]}
          loading={false}
        />
      );
    }
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border border-red-500/20 p-4">
        <div className="flex items-center gap-2 text-red-400 text-xs">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
        <p className="text-[10px] font-mono-deck text-muted-foreground mt-2 break-all">
          {buildQuery(widget)}
        </p>
      </div>
    );
  }

  const c = widget.config;

  switch (widget.type) {
    case "kpi": {
      const value = data?.[0]?.value;
      return (
        <KpiWidget
          label={(c.label as string) || ""}
          value={value != null ? Number(value) : 0}
          format={c.format as "currency" | "number" | "percent"}
          loading={loading}
        />
      );
    }
    case "line_chart":
    case "bar_chart":
    case "stacked_bar_chart": {
      const x = c.x as string;
      const y = Array.isArray(c.y) ? (c.y as string[]) : [c.y as string];
      const labels = c.labels as string[] | undefined;
      const chartType = widget.type === "line_chart" ? "line" : widget.type === "stacked_bar_chart" ? "stacked_bar" : "bar";

      // Format dates for display
      const chartData = (data || []).map((row) => ({
        ...row,
        [x]: x === "date" && typeof row[x] === "string"
          ? (row[x] as string).slice(5) // MM-DD
          : row[x],
      }));

      return (
        <ChartWidget
          title={c.title as string}
          type={chartType}
          data={chartData}
          xKey={x}
          yKeys={y}
          yLabels={labels}
          loading={loading}
        />
      );
    }
    case "table": {
      let columns = (c.columns as { field: string; label: string; format?: "currency" | "number" | "percent" }[]) || [];
      // Auto-derive columns from data when using custom_sql with no column definitions
      if (columns.length === 0 && data && data.length > 0) {
        columns = Object.keys(data[0]).map((key) => ({
          field: key,
          label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        }));
      }
      return (
        <TableWidget
          title={c.title as string}
          columns={columns}
          rows={data || []}
          loading={loading}
        />
      );
    }
    case "progress_bar": {
      // P109: first row of the query result drives value / max / status.
      const row = data?.[0];
      const value = row?.value != null ? Number(row.value) : NaN;
      const max = row?.max != null ? Number(row.max) : NaN;
      const rawStatus = row?.status;
      const status = typeof rawStatus === "string"
        ? (rawStatus as ProgressStatus)
        : "running";
      return (
        <ProgressBar
          label={(c.label as string) || ""}
          value={value}
          max={max}
          status={status}
          loading={loading}
        />
      );
    }
    default:
      return (
        <div className="bg-card rounded-lg border border-border p-4 text-xs text-muted-foreground">
          Unknown widget type: {widget.type}
        </div>
      );
  }
}

// ── Main Dashboard Renderer ──────────────────────────────────────────

export default function DashboardRenderer({ pluginId, dashboardName, preloadedSpec }: DashboardRendererProps) {
  const [spec, setSpec] = useState<DashboardSpec | null>(null);
  const [loading, setLoading] = useState(!preloadedSpec);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  // If a preloaded spec is provided, normalise and use it directly
  useEffect(() => {
    if (!preloadedSpec) return;
    const data = { ...preloadedSpec };
    if (Array.isArray(data.panels) && data.panels.length > 0 && (!data.widgets || data.widgets.length === 0)) {
      data.widgets = normalisePanels(data.panels);
    }
    setSpec(data);
    setLoading(false);
  }, [preloadedSpec]);

  useEffect(() => {
    if (preloadedSpec) return; // skip fetch when spec is provided
    async function load() {
      try {
        setLoading(true);
        setNotFound(false);
        const data = await getDashboardSpec(pluginId, dashboardName) as unknown as DashboardSpec;
        // Normalise panels-format dashboards to widgets-format
        if (Array.isArray(data.panels) && data.panels.length > 0 && (!data.widgets || data.widgets.length === 0)) {
          data.widgets = normalisePanels(data.panels);
        }
        setSpec(data);
      } catch (e) {
        if (e instanceof NotFoundError) {
          setNotFound(true);
        } else {
          setError(e instanceof Error ? e.message : "Failed to load dashboard");
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [pluginId, dashboardName]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse">
              <div className="h-3 w-20 bg-secondary rounded mb-3" />
              <div className="h-7 w-24 bg-secondary rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="py-20 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-secondary mb-4">
          <AlertCircle className="w-6 h-6 text-muted-foreground" />
        </div>
        <h3 className="font-display text-base text-foreground mb-2">No dashboard spec yet</h3>
        <p className="text-sm text-muted-foreground max-w-sm mx-auto">
          This plugin is installed but hasn't shipped a dashboard spec for <span className="font-mono-deck">{dashboardName}</span> yet.
          Data will appear here once the plugin is fully configured.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border border-orange-500/20 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-orange-400 mx-auto mb-3" />
        <h3 className="font-display text-lg text-foreground mb-2">Dashboard unavailable</h3>
        <p className="text-sm text-muted-foreground font-body mb-1">{error}</p>
        <p className="text-xs text-muted-foreground font-mono-deck">
          Make sure the API server is running: cd apps/api && python3 -m uvicorn src.main:app
        </p>
      </div>
    );
  }

  if (!spec) return null;

  // v0.10.1.0: if any widget has an explicit `layout` field, render the
  // whole dashboard with react-grid-layout in read-only mode (no drag/
  // resize for view). Legacy dashboards without layout fall back to the
  // row-based gridTemplateColumns rendering below.
  const hasLayout = spec.widgets.some((w: any) => w.layout);
  if (hasLayout) {
    const layouts = spec.widgets.map((w: any, i: number) => ({
      i: w.id ?? String(i),
      x: w.layout?.x ?? 0,
      y: w.layout?.y ?? i * 5,
      w: w.layout?.w ?? 6,
      h: w.layout?.h ?? 4,
      static: true,
    }));
    return (
      <div>
        <DashboardHeaderActions pluginId={pluginId} />
        <ReadOnlyGridLayout
          layouts={layouts}
          widgets={spec.widgets}
          pluginId={pluginId}
          dashboardName={dashboardName}
          dbEngine={spec.db_engine}
          refreshSeconds={spec.refresh_seconds}
        />
      </div>
    );
  }

  // Group widgets by row — handle missing position gracefully (legacy path)
  const rows = new Map<number, WidgetSpec[]>();
  for (let i = 0; i < spec.widgets.length; i++) {
    const widget = spec.widgets[i];
    const row = widget.position?.row ?? i;
    if (!widget.position) {
      widget.position = { row, col: 0, width: 2 };
    }
    if (!rows.has(row)) rows.set(row, []);
    rows.get(row)!.push(widget);
  }

  return (
    <div className="space-y-4">
      {/* P119: plugin dashboard_header actions */}
      <DashboardHeaderActions pluginId={pluginId} />

      {[...rows.entries()]
        .sort(([a], [b]) => a - b)
        .map(([rowNum, widgets]) => {
          return (
            <div
              key={rowNum}
              className="grid gap-4"
              style={{
                gridTemplateColumns: widgets
                  .map((w) => `${w.position?.width ?? 1}fr`)
                  .join(" "),
              }}
            >
              {widgets.map((widget, i) => (
                <WidgetRenderer key={`${rowNum}-${i}`} widget={widget} dbEngine={spec.db_engine} pluginId={pluginId} dashboardName={dashboardName} dashboardRefreshSeconds={spec.refresh_seconds} />
              ))}
            </div>
          );
        })}
    </div>
  );
}

// v0.10.1.0: read-only grid renderer for layout-based dashboards.
// `static: true` on every layout entry disables drag + resize.
// Sized to the container by ResizeObserver so the grid is responsive.
function ReadOnlyGridLayout({
  layouts,
  widgets,
  pluginId,
  dashboardName,
  dbEngine,
  refreshSeconds,
}: {
  layouts: any[];
  widgets: WidgetSpec[];
  pluginId: string;
  dashboardName: string;
  dbEngine?: string;
  refreshSeconds?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1200);
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver(([entry]) => {
      setWidth(Math.max(320, entry.contentRect.width));
    });
    ro.observe(el);
    setWidth(Math.max(320, el.clientWidth));
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={containerRef} className="w-full">
      <GridLayoutLib
        className="layout"
        layout={layouts as any}
        cols={12 as any}
        rowHeight={60}
        width={width}
        margin={[16, 16]}
        containerPadding={[0, 0]}
        isDraggable={false}
        isResizable={false}
      >
        {widgets.map((widget: any, i: number) => (
          <div key={widget.id ?? String(i)}>
            <WidgetRenderer
              widget={widget}
              dbEngine={dbEngine}
              pluginId={pluginId}
              dashboardName={dashboardName}
              dashboardRefreshSeconds={refreshSeconds}
            />
          </div>
        ))}
      </GridLayoutLib>
    </div>
  );
}
