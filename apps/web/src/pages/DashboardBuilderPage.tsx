import { useState, useEffect, useCallback, useReducer, useRef, useSyncExternalStore, Suspense } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch, query } from "@/lib/api";
import {
  getRegisteredComponents,
  getPluginComponentsSnapshot,
  subscribePluginComponents,
} from "@/widgets/plugin-components";
import ErrorBoundary from "@/components/ErrorBoundary";
import KpiWidget from "@/widgets/KpiWidget";
import TableWidget from "@/widgets/TableWidget";
import ChartWidget from "@/widgets/ChartWidget";
import {
  Plus, GripVertical, Trash2, Copy,
  BarChart3, Table2, TrendingUp, Hash, Component, Database,
  Save, ArrowLeft, AlertCircle, ChevronDown, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FusionBuilder, emptyGraph } from "@/widgets/FusionBuilder";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import GridLayoutImport from "react-grid-layout";

// react-grid-layout uses `export = ReactGridLayout` (CJS) and the @types
// surface props via a different name than what TypeScript resolves against
// our `tsconfig.json`'s default-import interpretation. Cast the component
// to a permissive type so JSX usage stays clean; the runtime is unaffected.
const GridLayout = GridLayoutImport as unknown as React.ComponentType<any>;

type RGLayoutItem = { i: string; x: number; y: number; w: number; h: number; static?: boolean };
import { ChartTypePicker, CHART_TYPE_OPTIONS } from "@/widgets/ChartTypePicker";
import { DividerWidget } from "@/widgets/TextWidget";
import { compileFusionGraph } from "@/lib/fusion-compiler";
import { sharedFusionSchemaCache } from "@/lib/fusion-schema-cache";
import type { FusionGraph } from "@/lib/fusion-graph-types";

// ── Types ────────────────────────────────────────────────────────────

interface WidgetSpec {
  id: string;
  type: string;
  /** Legacy flow position. Kept for backwards compat with pre-v0.10.1.0 dashboards. */
  position: { row: number; col: number; width: number };
  /** v0.10.1.0: explicit free-form grid position (12-col grid, rowHeight 60px).
   *  When present, takes precedence over `position` in both builder + renderer. */
  layout?: { x: number; y: number; w: number; h: number };
  config: Record<string, unknown>;
}

// 12-column grid with 60px row height — react-grid-layout defaults that
// give us KPI=2 rows tall (~120px), chart=5 rows (~300px), table=6 rows.
const GRID_COLS = 12;
const GRID_ROW_HEIGHT = 60;

function defaultLayoutForType(type: string): { w: number; h: number } {
  // Heights in rowHeight (60px) units. The builder card adds a 20px
  // drag-header strip on top, so each unit contributes 60px minus the
  // strip share. Chart needs ~310px content → h:6 = 360-20=340px gives
  // headroom. KPI bumped to h:3 so the value isn't cramped under the
  // header. Heading h:2 so single-line titles never feel squashed.
  switch (type) {
    case "kpi": return { w: 3, h: 3 };
    case "table": return { w: 12, h: 7 };
    case "line_chart":
    case "bar_chart":
    case "stacked_bar_chart": return { w: 6, h: 6 };
    case "heading": return { w: 12, h: 2 };
    case "text": return { w: 12, h: 3 };
    case "divider": return { w: 12, h: 1 };
    case "custom": return { w: 6, h: 5 };
    default: return { w: 6, h: 5 };
  }
}

/** Convert legacy {row,col,width} to {x,y,w,h}. 4-col grid → 12-col grid by ×3. */
function legacyPositionToLayout(
  position: { row: number; col: number; width: number },
  type: string,
): { x: number; y: number; w: number; h: number } {
  const { h } = defaultLayoutForType(type);
  return {
    x: Math.max(0, Math.min(GRID_COLS - 1, position.col * 3)),
    y: position.row * h,
    w: Math.max(1, Math.min(GRID_COLS, position.width * 3)),
    h,
  };
}

interface BuilderState {
  name: string;
  description: string;
  widgets: WidgetSpec[];
  selectedId: string | null;
  previewMode: boolean;
}

type Action =
  | { type: "SET_NAME"; name: string }
  | { type: "SET_DESCRIPTION"; description: string }
  | { type: "ADD_WIDGET"; widgetType: string; config?: Record<string, unknown> }
  | { type: "REMOVE_WIDGET"; id: string }
  | { type: "DUPLICATE_WIDGET"; id: string }
  | { type: "UPDATE_WIDGET"; id: string; changes: Partial<WidgetSpec> }
  | { type: "UPDATE_LAYOUTS"; layouts: RGLayoutItem[] }
  | { type: "SELECT_WIDGET"; id: string | null }
  | { type: "MOVE_WIDGET"; fromIndex: number; toIndex: number }
  | { type: "TOGGLE_PREVIEW" }
  | { type: "LOAD"; state: Partial<BuilderState> };

function reducer(state: BuilderState, action: Action): BuilderState {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_DESCRIPTION":
      return { ...state, description: action.description };
    case "ADD_WIDGET": {
      const widget = makeWidget(action.widgetType, action.config || {}, state.widgets);
      return { ...state, widgets: [...state.widgets, widget], selectedId: widget.id };
    }
    case "REMOVE_WIDGET":
      return {
        ...state,
        widgets: state.widgets.filter((w) => w.id !== action.id),
        selectedId: state.selectedId === action.id ? null : state.selectedId,
      };
    case "DUPLICATE_WIDGET": {
      const src = state.widgets.find((w) => w.id === action.id);
      if (!src) return state;
      const dup: WidgetSpec = { ...src, id: makeId(), config: { ...src.config }, position: { ...src.position } };
      const idx = state.widgets.indexOf(src);
      const widgets = [...state.widgets];
      widgets.splice(idx + 1, 0, dup);
      return { ...state, widgets, selectedId: dup.id };
    }
    case "UPDATE_WIDGET":
      return {
        ...state,
        widgets: state.widgets.map((w) =>
          w.id === action.id ? { ...w, ...action.changes, config: { ...w.config, ...(action.changes.config || {}) } } : w
        ),
      };
    case "UPDATE_LAYOUTS": {
      // v0.10.1.0: react-grid-layout fires onLayoutChange with new {i,x,y,w,h}
      // for every widget after a drag/resize. Sync those back into widget.layout.
      const byId = new Map(action.layouts.map((l) => [l.i, l]));
      return {
        ...state,
        widgets: state.widgets.map((w) => {
          const l = byId.get(w.id);
          if (!l) return w;
          return { ...w, layout: { x: l.x, y: l.y, w: l.w, h: l.h } };
        }),
      };
    }
    case "SELECT_WIDGET":
      return { ...state, selectedId: action.id };
    case "MOVE_WIDGET": {
      const widgets = [...state.widgets];
      const [moved] = widgets.splice(action.fromIndex, 1);
      widgets.splice(action.toIndex, 0, moved);
      return { ...state, widgets };
    }
    case "TOGGLE_PREVIEW":
      return { ...state, previewMode: !state.previewMode, selectedId: null };
    case "LOAD":
      return { ...state, ...action.state };
    default:
      return state;
  }
}

function makeId() {
  return `w-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function makeWidget(type: string, config: Record<string, unknown> = {}, existingWidgets: WidgetSpec[] = []): WidgetSpec {
  const wt = WIDGET_TYPES.find((w) => w.type === type);
  const width = wt?.defaultWidth ?? (type === "custom" ? 4 : 2);
  const { w, h } = defaultLayoutForType(type);

  // Find the lowest empty y where the new widget can fit (left-aligned x=0).
  // Simple packer: place below the current max y + h of last widget.
  const maxY = existingWidgets.reduce((acc, ew) => {
    const ey = (ew.layout?.y ?? 0) + (ew.layout?.h ?? defaultLayoutForType(ew.type).h);
    return Math.max(acc, ey);
  }, 0);

  return {
    id: makeId(),
    type,
    position: { row: 99, col: 0, width },
    layout: { x: 0, y: maxY, w, h },
    config,
  };
}

// ── Widget type metadata ─────────────────────────────────────────────

const WIDGET_TYPES = [
  { type: "kpi", label: "Stat / KPI", icon: Hash, defaultSql: "SELECT count(*) AS value FROM ", defaultWidth: 1, needsQuery: true },
  { type: "table", label: "Table", icon: Table2, defaultSql: "SELECT * FROM ", defaultWidth: 4, needsQuery: true },
  { type: "line_chart", label: "Line Chart", icon: TrendingUp, defaultSql: "SELECT date, count(*) AS value FROM ", defaultWidth: 4, needsQuery: true },
  { type: "bar_chart", label: "Bar Chart", icon: BarChart3, defaultSql: "SELECT category, count(*) AS value FROM ", defaultWidth: 2, needsQuery: true },
  { type: "stacked_bar_chart", label: "Stacked Bar", icon: BarChart3, defaultSql: "SELECT category, a, b FROM ", defaultWidth: 2, needsQuery: true },
  // v0.10.1.0: layout/text widgets — no SQL needed.
  { type: "heading", label: "Heading", icon: Hash, defaultSql: "", defaultWidth: 4, needsQuery: false },
  { type: "text", label: "Text", icon: Hash, defaultSql: "", defaultWidth: 4, needsQuery: false },
  { type: "divider", label: "Divider", icon: Hash, defaultSql: "", defaultWidth: 4, needsQuery: false },
];

const LAYOUT_WIDGET_TYPES = new Set(["heading", "text", "divider"]);
const NEEDS_QUERY = (type: string) =>
  !LAYOUT_WIDGET_TYPES.has(type) && type !== "custom";

// ── Main Builder Page ────────────────────────────────────────────────

export default function DashboardBuilderPage() {
  useMarkBootReadyOnMount();
  const { slug } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(slug);

  const [state, dispatch] = useReducer(reducer, {
    name: "",
    description: "",
    widgets: [],
    selectedId: null,
    previewMode: false,
  });

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [plugins, setPlugins] = useState<{ slug: string; display_name: string; tables: string[] }[]>([]);

  // Load plugin metadata for the widget picker
  useEffect(() => {
    apiFetch("/api/plugins")
      .then((r) => r.json())
      .then((d) => {
        const list = (d.plugins || [])
          .filter((p: any) => p.databases?.postgres?.tables?.length)
          .map((p: any) => ({
            slug: p.name || p.slug,
            display_name: p.display_name || p.name || p.slug,
            tables: p.databases?.postgres?.tables || [],
          }));
        setPlugins(list);
      })
      .catch((e) => console.error("Failed to load plugins:", e));
  }, []);

  // Load existing dashboard for edit mode
  useEffect(() => {
    if (!slug) return;
    apiFetch(`/api/dashboards/${slug}`)
      .then((r) => r.json())
      .then((d) => {
        dispatch({
          type: "LOAD",
          state: {
            name: d.name,
            description: d.description || "",
            widgets: (d.widgets || []).map((w: any, i: number) => {
              const position = w.position || { row: i, col: 0, width: w.type === "kpi" ? 1 : 4 };
              // v0.10.1.0: backfill explicit layout for legacy widgets so the
              // grid canvas has stable {x,y,w,h} to work with.
              const layout = w.layout ?? legacyPositionToLayout(position, w.type);
              return {
                ...w,
                id: w.id || makeId(),
                position,
                layout,
              };
            }),
          },
        });
      })
      .catch((e) => console.error("Failed to load dashboard:", e));
  }, [slug]);

  async function handleSave() {
    if (!state.name.trim()) { setSaveError("Name is required"); return; }
    if (state.widgets.length === 0) { setSaveError("Add at least one widget"); return; }

    setSaving(true);
    setSaveError(null);

    // v0.10.1.0: widgets carry an explicit `layout` (authoritative for the new
    // grid renderer). Derive a legacy `{row,col,width}` from layout so older
    // renderers / YAML consumers still see a reasonable position fallback.
    const widgets = state.widgets.map((w) => {
      const layout = w.layout ?? legacyPositionToLayout(w.position, w.type);
      const position = {
        row: Math.floor(layout.y / Math.max(1, layout.h)),
        col: Math.floor(layout.x / 3),
        width: Math.max(1, Math.min(4, Math.round(layout.w / 3))),
      };
      return { ...w, layout, position };
    });
    const sources = extractSources(widgets, plugins);

    const body = {
      name: state.name.trim(),
      description: state.description.trim() || null,
      widgets,
      sources,
    };

    try {
      const url = isEdit ? `/api/dashboards/${slug}` : "/api/dashboards";
      const method = isEdit ? "PUT" : "POST";
      const res = await apiFetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to save");
      }
      const saved = await res.json();
      navigate(`/dashboards/${saved.slug}`);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const selectedWidget = state.widgets.find((w) => w.id === state.selectedId) || null;

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      if ((e.key === "Delete" || e.key === "Backspace") && state.selectedId) {
        e.preventDefault();
        dispatch({ type: "REMOVE_WIDGET", id: state.selectedId });
      }
      if (e.key === "d" && (e.metaKey || e.ctrlKey) && state.selectedId) {
        e.preventDefault();
        dispatch({ type: "DUPLICATE_WIDGET", id: state.selectedId });
      }
      if (e.key === "Escape") {
        dispatch({ type: "SELECT_WIDGET", id: null });
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [state.selectedId, dispatch]);

  return (
    <div className="fixed inset-0 z-40 bg-background flex flex-col">
      {/* Top bar */}
      <div className="border-b border-border px-4 py-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/dashboards")}
              className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <input
                type="text"
                value={state.name}
                onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
                placeholder="Dashboard name…"
                className="bg-transparent text-foreground font-display text-sm border-none outline-none w-64 placeholder:text-muted-foreground"
              />
              <input
                type="text"
                value={state.description}
                onChange={(e) => dispatch({ type: "SET_DESCRIPTION", description: e.target.value })}
                placeholder="Description (optional)"
                className="block bg-transparent text-muted-foreground text-[11px] border-none outline-none w-64 placeholder:text-muted-foreground/50 mt-0.5"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* v0.10.1.1: Preview-mode toggle removed — the canvas already
                renders real widget data via LiveWidgetCard, so there's no
                separate "preview" state to flip into. The builder IS the
                preview. */}
            <button
              onClick={handleSave}
              disabled={saving}
              className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? "Saving…" : isEdit ? "Update" : "Save"}
            </button>
          </div>
        </div>
      </div>

      {saveError && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-400 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5" />
          {saveError}
        </div>
      )}

      {/* Main content — single layout, the canvas IS the preview (v0.10.1.1) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar — Widget Picker */}
        <div className="w-[260px] border-r border-border overflow-y-auto p-3 shrink-0">
          <WidgetPicker plugins={plugins} dispatch={dispatch} />
        </div>

        {/* Center — Canvas */}
        <div className="flex-1 min-w-0 overflow-y-auto p-6 bg-secondary/20">
          <BuilderCanvas widgets={state.widgets} selectedId={state.selectedId} dispatch={dispatch} />
        </div>

        {/* Right sidebar — Config Panel */}
        <div className="w-[320px] border-l border-border overflow-y-auto p-4 shrink-0">
            {selectedWidget ? (
              <WidgetConfigPanel widget={selectedWidget} dispatch={dispatch} />
            ) : (
              <div className="py-12 text-center text-xs text-muted-foreground">
                Select a widget to edit its properties
              </div>
            )}
          </div>
        </div>
    </div>
  );
}

// ── Widget Picker ────────────────────────────────────────────────────

function WidgetPicker({
  plugins,
  dispatch,
}: {
  plugins: { slug: string; display_name: string; tables: string[] }[];
  dispatch: React.Dispatch<Action>;
}) {
  const [expandedPlugins, setExpandedPlugins] = useState<Set<string>>(new Set());
  const customComponents = getRegisteredComponents();

  function togglePlugin(slug: string) {
    setExpandedPlugins((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug); else next.add(slug);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <p className="text-[10px] font-mono-deck text-muted-foreground uppercase tracking-wider">Widget Picker</p>

      {/* Widget types */}
      <div>
        <p className="text-xs font-display text-muted-foreground mb-2">By Type</p>
        <div className="grid grid-cols-2 gap-1.5">
          {CHART_TYPE_OPTIONS.filter((opt) => opt.type !== "custom").map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.type}
                onClick={() => dispatch({
                  type: "ADD_WIDGET",
                  widgetType: opt.type,
                  // v0.10.1.1: data widgets open in the visual Builder with
                  // an empty graph — no SQL stub. The compiler will write
                  // `custom_sql` once the operator picks a source.
                  config: opt.needsQuery
                    ? { label: "" }
                    : opt.type === "heading"
                      ? { text: "New Heading", level: "h2" }
                      : opt.type === "text"
                        ? { text: "Add your text here. Use **bold** and `code`." }
                        : {},
                })}
                className="flex flex-col items-center gap-1 p-2.5 rounded-md border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-muted-foreground hover:text-foreground"
              >
                <Icon className="w-4 h-4" />
                <span className="text-[10px] font-body">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom components */}
      {customComponents.length > 0 && (
        <div>
          <p className="text-xs font-display text-muted-foreground mb-2">Custom Components</p>
          <div className="space-y-1">
            {customComponents.map((name) => (
              <button
                key={name}
                onClick={() => dispatch({ type: "ADD_WIDGET", widgetType: "custom", config: { component: name } })}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-xs text-muted-foreground hover:text-foreground"
              >
                <Component className="w-3.5 h-3.5" />
                {name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Plugin tables */}
      {plugins.length > 0 && (
        <div>
          <p className="text-xs font-display text-muted-foreground mb-2">Plugin Tables</p>
          <div className="space-y-0.5">
            {plugins.map((p) => (
              <div key={p.slug}>
                <button
                  onClick={() => togglePlugin(p.slug)}
                  className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-md hover:bg-secondary/50 text-xs text-foreground transition-colors"
                >
                  {expandedPlugins.has(p.slug) ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  {p.display_name}
                  <span className="text-muted-foreground ml-auto text-[10px]">{p.tables.length}</span>
                </button>
                {expandedPlugins.has(p.slug) && (
                  <div className="ml-4 space-y-0.5 mt-0.5">
                    {p.tables.map((table) => (
                      <button
                        key={table}
                        onClick={() =>
                          dispatch({
                            type: "ADD_WIDGET",
                            widgetType: "kpi",
                            config: {
                              label: table.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                              custom_sql: `SELECT count(*) AS value FROM ${table}`,
                            },
                          })
                        }
                        className="w-full flex items-center gap-1.5 px-2 py-1 rounded text-[11px] text-muted-foreground hover:text-foreground hover:bg-secondary/30 transition-colors font-mono-deck"
                      >
                        <Database className="w-3 h-3 shrink-0" />
                        {table}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

// ── Builder Canvas ───────────────────────────────────────────────────

function BuilderCanvas({
  widgets,
  selectedId,
  dispatch,
}: {
  widgets: WidgetSpec[];
  selectedId: string | null;
  dispatch: React.Dispatch<Action>;
}) {
  // v0.10.1.1: measure the canvas container width so the grid never flows
  // under the right-side config sidebar. Hard-coding width={1320} broke at
  // any viewport narrower than ~1900px.
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver(([entry]) => {
      setContainerWidth(Math.max(320, entry.contentRect.width));
    });
    ro.observe(el);
    setContainerWidth(Math.max(320, el.clientWidth));
    return () => ro.disconnect();
  }, []);

  if (widgets.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center py-16 px-8 border-2 border-dashed border-border rounded-lg max-w-sm">
          <Plus className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground font-body">
            Add widgets from the picker on the left
          </p>
          <p className="text-[10px] text-muted-foreground/50 mt-2 font-mono-deck">
            Drag to move · resize from edges · Del to remove · Cmd+D to duplicate · Esc to deselect
          </p>
        </div>
      </div>
    );
  }

  const layouts: RGLayoutItem[] = widgets.map((w) => {
    const l = w.layout ?? legacyPositionToLayout(w.position, w.type);
    return { i: w.id, x: l.x, y: l.y, w: l.w, h: l.h };
  });

  return (
    <div ref={containerRef} className="w-full">
      <GridLayout
        className="layout"
        layout={layouts as any}
        cols={GRID_COLS}
        rowHeight={GRID_ROW_HEIGHT}
        width={containerWidth}
        margin={[16, 16]}
        containerPadding={[0, 0]}
        compactType="vertical"
        preventCollision={false}
        draggableHandle=".widget-drag-handle"
        onLayoutChange={(newLayout: any) => {
          dispatch({ type: "UPDATE_LAYOUTS", layouts: newLayout as RGLayoutItem[] });
        }}
      >
        {widgets.map((widget) => (
          <div key={widget.id}>
            <LiveWidgetCard
              widget={widget}
              isSelected={selectedId === widget.id}
              dispatch={dispatch}
            />
          </div>
        ))}
      </GridLayout>
    </div>
  );
}

// ── Live Widget Card — renders actual widget with edit overlay ────────

function LiveWidgetCard({
  widget,
  isSelected,
  dispatch,
}: {
  widget: WidgetSpec;
  isSelected: boolean;
  dispatch: React.Dispatch<Action>;
}) {
  const c = widget.config;
  const sql = (c.custom_sql || "") as string;
  const sqlComplete = sql.trim().length > 0
    && !sql.trim().endsWith("FROM")
    && !sql.trim().endsWith("FROM ")
    && sql.trim().split(/\s+/).length >= 4;
  const hasQuery = NEEDS_QUERY(widget.type) && sqlComplete;
  const label = (c.label || c.title || c.text || c.component || widget.type) as string;
  const isLayout = LAYOUT_WIDGET_TYPES.has(widget.type);

  // v0.10.1.4: header bar is now part of the flex flow (always visible,
  // subtle background) rather than an absolute overlay. The absolute
  // version clipped content underneath itself — most painfully on the
  // inline text/heading editors where the top of the input was hidden.
  return (
    <div
      className={cn(
        "relative group rounded-lg h-full flex flex-col transition-all overflow-hidden",
        isSelected
          ? "ring-2 ring-primary/70 ring-offset-2 ring-offset-secondary/20"
          : "ring-1 ring-transparent hover:ring-primary/30",
      )}
      onClick={(e) => { e.stopPropagation(); dispatch({ type: "SELECT_WIDGET", id: widget.id }); }}
    >
      {/* Full-width drag header — always visible, fades subtly when not
          selected. Part of the flex flow so it doesn't overlay content. */}
      <div
        className={cn(
          "widget-drag-handle shrink-0 flex items-center justify-between gap-2 px-2 h-5",
          "cursor-grab active:cursor-grabbing select-none transition-colors",
          "border-b border-border bg-secondary/60 backdrop-blur-sm",
          isSelected
            ? "opacity-100"
            : "opacity-60 group-hover:opacity-100",
        )}
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <GripVertical className="w-3 h-3 text-muted-foreground shrink-0" />
          <span className="text-[10px] font-mono-deck text-muted-foreground truncate">
            {label || widget.type}
          </span>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); dispatch({ type: "DUPLICATE_WIDGET", id: widget.id }); }}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors rounded hover:bg-background/60"
            title="Duplicate (Cmd+D)"
          >
            <Copy className="w-3 h-3" />
          </button>
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); dispatch({ type: "REMOVE_WIDGET", id: widget.id }); }}
            className="p-1 text-muted-foreground hover:text-red-400 transition-colors rounded hover:bg-background/60"
            title="Delete (Del)"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Widget content — fills remaining height below the header */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {widget.type === "heading" ? (
          <InlineHeadingEdit widget={widget} dispatch={dispatch} />
        ) : widget.type === "text" ? (
          <InlineTextEdit widget={widget} dispatch={dispatch} />
        ) : widget.type === "divider" ? (
          <div className="h-full flex items-center px-2">
            <DividerWidget />
          </div>
        ) : hasQuery ? (
          <div className="h-full overflow-hidden">
            <LiveWidgetPreview widget={widget} />
          </div>
        ) : widget.type === "custom" ? (
          <CustomWidgetPreview component={(c.component as string) || ""} config={c} />
        ) : (
          <div className="h-full flex items-center justify-center p-4 text-center bg-card border-2 border-dashed border-border/60 rounded-lg">
            <p className="text-xs text-muted-foreground">
              {isLayout
                ? `${label || "Untitled"} — edit in the right panel`
                : `${label || "Untitled"} — author a query in the right panel`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Live Widget Preview — fetches and renders real data ──────────────

// ── Inline editors for heading / text ─────────────────────────────────
//
// v0.10.1.3: click the rendered text in the card to edit it in place.
// The sidebar text inputs are removed for these types so there's one
// obvious way to change the content. Level selector for headings stays
// in the sidebar (h1/h2/h3 is not a click-and-type concern).

function InlineHeadingEdit({
  widget,
  dispatch,
}: {
  widget: WidgetSpec;
  dispatch: React.Dispatch<Action>;
}) {
  const text = (widget.config.text as string) || "";
  const level = (widget.config.level as "h1" | "h2" | "h3") || "h2";
  const sizeClass = level === "h1" ? "text-2xl" : level === "h2" ? "text-lg" : "text-sm";
  return (
    <div className="h-full bg-card rounded-lg border border-border flex items-center px-3">
      <input
        type="text"
        value={text}
        onChange={(e) =>
          dispatch({
            type: "UPDATE_WIDGET",
            id: widget.id,
            changes: { config: { text: e.target.value } },
          })
        }
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        placeholder="Heading"
        className={cn(
          "w-full bg-transparent border-none outline-none font-display text-foreground placeholder:text-muted-foreground/40",
          sizeClass,
        )}
      />
    </div>
  );
}

function InlineTextEdit({
  widget,
  dispatch,
}: {
  widget: WidgetSpec;
  dispatch: React.Dispatch<Action>;
}) {
  const text = (widget.config.text as string) || "";
  return (
    <div className="h-full bg-card rounded-lg border border-border p-3">
      <textarea
        value={text}
        onChange={(e) =>
          dispatch({
            type: "UPDATE_WIDGET",
            id: widget.id,
            changes: { config: { text: e.target.value } },
          })
        }
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        placeholder="Add your text here. Use **bold** and `code`."
        className="w-full h-full bg-transparent border-none outline-none resize-none text-sm text-muted-foreground font-body placeholder:text-muted-foreground/40 leading-relaxed"
      />
    </div>
  );
}

// ── Live render of a custom plugin component on the canvas ────────────
//
// v0.10.1.3: was "Live preview rendering pending" placeholder; now
// resolves the component from the same registry view mode uses and
// renders it. ErrorBoundary + Suspense match WidgetRenderer's behaviour
// in DashboardRenderer.

function CustomWidgetPreview({
  component: name,
  config,
}: {
  component: string;
  config: Record<string, unknown>;
}) {
  const components = useSyncExternalStore(
    subscribePluginComponents,
    getPluginComponentsSnapshot,
    getPluginComponentsSnapshot,
  );
  if (!name) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-card rounded-lg border border-dashed border-border/60">
        <Component className="w-6 h-6 text-muted-foreground/40 mb-2" />
        <p className="text-xs text-muted-foreground">
          Pick a component in the right panel
        </p>
      </div>
    );
  }
  const Comp = components[name];
  if (!Comp) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-4 bg-card rounded-lg border border-red-500/30 text-red-400 text-xs">
        Unknown component: {name}
      </div>
    );
  }
  return (
    <ErrorBoundary
      context={`builder-preview:${name}`}
      fallback={(error, reset) => (
        <div className="h-full p-4 bg-card rounded-lg border border-amber-500/30 text-xs space-y-2">
          <div className="text-amber-400 font-medium">
            {name} failed to render
          </div>
          <div className="text-muted-foreground">{error.message}</div>
          <button
            type="button"
            onClick={reset}
            onMouseDown={(e) => e.stopPropagation()}
            className="text-[11px] text-primary hover:underline"
          >
            Retry
          </button>
        </div>
      )}
    >
      <Suspense
        fallback={
          <div className="h-full bg-card rounded-lg border border-border animate-pulse" />
        }
      >
        <Comp pluginId="" dashboardName="" config={config} />
      </Suspense>
    </ErrorBoundary>
  );
}

function LiveWidgetPreview({ widget }: { widget: WidgetSpec }) {
  const c = widget.config;
  const sql = (c.custom_sql || "") as string;
  const [data, setData] = useState<Record<string, unknown>[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Don't auto-run incomplete SQL (stubs from the picker end with "FROM ")
  const sqlReady = sql.trim().length > 0
    && !sql.trim().endsWith("FROM")
    && !sql.trim().endsWith("FROM ")
    && sql.trim().split(/\s+/).length >= 4;

  const fetchData = useCallback(async () => {
    if (!sqlReady) { setLoading(false); setData(null); return; }
    try {
      setLoading(true);
      setError(null);
      const result = await query(sql);
      setData(result.rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }, [sql, sqlReady]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (error) {
    return (
      <div className="bg-card rounded-lg border border-red-500/20 p-3">
        <div className="flex items-center gap-2 text-red-400 text-xs">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      </div>
    );
  }

  switch (widget.type) {
    case "kpi":
      return <KpiWidget label={(c.label as string) || ""} value={data?.[0]?.value != null ? Number(data[0].value) : 0} loading={loading} />;
    case "table": {
      let cols = (c.columns as { field: string; label: string }[]) || [];
      if (cols.length === 0 && data?.length) {
        cols = Object.keys(data[0]).map((k) => ({
          field: k,
          label: k.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase()),
        }));
      }
      return <TableWidget title={(c.title as string) || ""} columns={cols} rows={data || []} loading={loading} />;
    }
    case "line_chart":
    case "bar_chart":
    case "stacked_bar_chart": {
      const x = (c.x as string) || (data?.[0] ? Object.keys(data[0])[0] : "x");
      const y = Array.isArray(c.y) ? c.y as string[] : data?.[0] ? Object.keys(data[0]).filter((k) => k !== x) : ["value"];
      const chartType = widget.type === "line_chart" ? "line" : widget.type === "stacked_bar_chart" ? "stacked_bar" : "bar";
      return <ChartWidget title={(c.title as string) || ""} type={chartType} data={data || []} xKey={x} yKeys={y} loading={loading} />;
    }
    default:
      return <div className="bg-card rounded-lg border border-border p-4 text-xs text-muted-foreground">Unknown: {widget.type}</div>;
  }
}

// ── Widget Config Panel ──────────────────────────────────────────────

function WidgetConfigPanel({
  widget,
  dispatch,
}: {
  widget: WidgetSpec;
  dispatch: React.Dispatch<Action>;
}) {
  const [previewData, setPreviewData] = useState<Record<string, unknown>[] | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Visual query builder state. v0.10.0.9: widgets can author their
  // query via the visual builder (the same UX previously locked inside
  // /fusions) instead of raw SQL. The graph compiles to SQL on every
  // change and writes back into widget.config.custom_sql so the rest
  // of the dashboard pipeline (DashboardRenderer, preview, save) is
  // unchanged. Raw SQL mode is preserved as a fallback for widgets
  // that already only have custom_sql, and as an advanced affordance.
  const initialGraph = (widget.config.query_graph as FusionGraph | undefined) ?? emptyGraph();
  // v0.10.1.1: Builder is always the default mode. SQL is opt-in only.
  // Loading a legacy dashboard with only custom_sql still opens in Builder
  // (with an empty graph); operator can click the SQL tab to see the
  // existing SQL. Removes the "every new widget opens in SQL because it
  // was seeded with a placeholder" bug.
  const [graph, setGraph] = useState<FusionGraph>(initialGraph);
  const [editorMode, setEditorMode] = useState<"builder" | "sql">("builder");

  // Reset state when switching widgets
  useEffect(() => {
    setPreviewData(null);
    setPreviewError(null);
    const g = (widget.config.query_graph as FusionGraph | undefined) ?? emptyGraph();
    setGraph(g);
    setEditorMode("builder");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [widget.id]);

  function update(changes: Partial<WidgetSpec>) {
    dispatch({ type: "UPDATE_WIDGET", id: widget.id, changes });
  }

  function updateConfig(key: string, value: unknown) {
    update({ config: { [key]: value } });
  }

  // When the graph changes in builder mode, compile to SQL and persist
  // both graph + sql on the widget config so it's re-editable next time
  // and so the dashboard renderer (which reads custom_sql) keeps working.
  useEffect(() => {
    if (editorMode !== "builder") return;
    const result = compileFusionGraph(graph, sharedFusionSchemaCache);
    const patch: Record<string, unknown> = { query_graph: graph };
    if (result.ok) patch.custom_sql = result.sql;
    update({ config: patch });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, editorMode]);

  async function runPreview() {
    const sql = widget.config.custom_sql as string;
    if (!sql) return;
    setPreviewError(null);
    try {
      const result = await query(sql);
      setPreviewData(result.rows);
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : "Query failed");
    }
  }

  // v0.10.1.0: auto-fire preview whenever the SQL changes to a valid-looking
  // value. Debounced 400ms so rapid graph edits don't hammer the query API.
  // Populates previewData so the visual axis pickers + preview pane render
  // without the operator clicking "Run Preview" every time.
  const currentSql = (widget.config.custom_sql as string) || "";
  useEffect(() => {
    if (!NEEDS_QUERY(widget.type)) return;
    const trimmed = currentSql.trim();
    if (!trimmed) return;
    if (trimmed.endsWith("FROM") || trimmed.endsWith("FROM ")) return;
    if (trimmed.split(/\s+/).length < 4) return;
    const t = window.setTimeout(() => {
      runPreview();
    }, 400);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSql, widget.type]);

  const customComponents = getRegisteredComponents();
  const isLayoutWidget = LAYOUT_WIDGET_TYPES.has(widget.type);
  const isHeading = widget.type === "heading";
  const isText = widget.type === "text";

  return (
    <div className="space-y-4">
      <p className="text-[10px] font-mono-deck text-muted-foreground uppercase tracking-wider">Widget Config</p>

      {/* Type — visual picker */}
      <div className="space-y-1.5">
        <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Type</label>
        <ChartTypePicker
          value={widget.type}
          onChange={(newType) => {
            // Resize to type default when switching between layout vs data widgets
            const wasLayout = LAYOUT_WIDGET_TYPES.has(widget.type);
            const isNowLayout = LAYOUT_WIDGET_TYPES.has(newType);
            const changes: Partial<WidgetSpec> = { type: newType };
            if (wasLayout !== isNowLayout && widget.layout) {
              const def = defaultLayoutForType(newType);
              changes.layout = { ...widget.layout, w: def.w, h: def.h };
            }
            dispatch({ type: "UPDATE_WIDGET", id: widget.id, changes });
          }}
        />
      </div>

      {/* Heading-specific config — text is edited inline on the card now (v0.10.1.3);
          sidebar keeps only the level selector. */}
      {isHeading && (
        <div className="space-y-1">
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Level</label>
          <div className="flex gap-1">
            {(["h1", "h2", "h3"] as const).map((lv) => (
              <button
                key={lv}
                onClick={() => updateConfig("level", lv)}
                className={cn(
                  "flex-1 h-8 rounded-md text-xs font-body transition-colors",
                  ((widget.config.level as string) || "h2") === lv
                    ? "bg-primary text-white"
                    : "bg-secondary text-muted-foreground hover:text-foreground",
                )}
              >
                {lv.toUpperCase()}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground/60 mt-1">
            Click the heading on the card to edit the text.
          </p>
        </div>
      )}

      {/* Text-specific config — fully inline now; sidebar just guides. */}
      {isText && (
        <p className="text-[10px] text-muted-foreground/60">
          Click the text on the card to edit. Supports <code className="text-foreground">**bold**</code> and <code className="text-foreground">`code`</code> in view mode.
        </p>
      )}

      {/* Label — for data widgets */}
      {!isLayoutWidget && (
        <div className="space-y-1">
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Label</label>
          <input
            type="text"
            value={(widget.config.label || widget.config.title || "") as string}
            onChange={(e) => {
              updateConfig("label", e.target.value);
              updateConfig("title", e.target.value);
            }}
            className="w-full h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      )}

      {/* Custom component selector */}
      {widget.type === "custom" && (
        <div className="space-y-1">
          <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Component</label>
          <select
            value={(widget.config.component || "") as string}
            onChange={(e) => updateConfig("component", e.target.value)}
            className="w-full h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Select component…</option>
            {customComponents.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Query — visual builder OR raw SQL. Builder is the default.
          Hidden for layout widgets (heading/text/divider) — they
          don't need a query. */}
      {!isLayoutWidget && widget.type !== "custom" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Query</label>
            <div className="flex bg-secondary rounded-md p-0.5">
              <button
                type="button"
                onClick={() => setEditorMode("builder")}
                className={cn(
                  "h-6 px-2 rounded text-[10px] font-semibold uppercase tracking-wider transition-colors",
                  editorMode === "builder"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Builder
              </button>
              <button
                type="button"
                onClick={() => setEditorMode("sql")}
                className={cn(
                  "h-6 px-2 rounded text-[10px] font-semibold uppercase tracking-wider transition-colors",
                  editorMode === "sql"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                SQL
              </button>
            </div>
          </div>

          {editorMode === "builder" ? (
            <FusionBuilder graph={graph} onChange={setGraph} showPreview={true} />
          ) : (
            <textarea
              value={(widget.config.custom_sql || "") as string}
              onChange={(e) => updateConfig("custom_sql", e.target.value)}
              rows={5}
              className="w-full px-3 py-2 rounded-md bg-background border border-border text-xs text-foreground font-mono-deck focus:outline-none focus:ring-1 focus:ring-primary resize-y"
              placeholder="SELECT count(*) AS value FROM table_name"
            />
          )}

          {/* Chart axis config — visual column pickers (v0.10.1.0).
              Populated from the live preview's columns; falls back to a
              text input if no preview data has resolved yet. */}
          {(widget.type === "line_chart" || widget.type === "bar_chart" || widget.type === "stacked_bar_chart") && (() => {
            const columns: string[] = previewData && previewData.length > 0
              ? Object.keys(previewData[0])
              : [];
            const xValue = (widget.config.x as string) || "";
            const yValues: string[] = Array.isArray(widget.config.y)
              ? (widget.config.y as string[])
              : widget.config.y
                ? [widget.config.y as string]
                : [];
            return (
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div>
                  <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">X Axis</label>
                  {columns.length > 0 ? (
                    <select
                      value={xValue}
                      onChange={(e) => updateConfig("x", e.target.value)}
                      className="w-full h-7 px-2 rounded bg-background border border-border text-xs text-foreground font-mono-deck focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="">Pick column…</option>
                      {columns.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={xValue}
                      onChange={(e) => updateConfig("x", e.target.value)}
                      placeholder="date"
                      className="w-full h-7 px-2 rounded bg-background border border-border text-xs text-foreground font-mono-deck focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  )}
                </div>
                <div>
                  <label className="text-[10px] font-mono-deck text-muted-foreground uppercase">Y Axis</label>
                  {columns.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {columns.filter((c) => c !== xValue).map((col) => {
                        const selected = yValues.includes(col);
                        return (
                          <button
                            key={col}
                            type="button"
                            onClick={() => {
                              const next = selected ? yValues.filter((c) => c !== col) : [...yValues, col];
                              updateConfig("y", next);
                            }}
                            className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded font-mono-deck border transition-colors",
                              selected
                                ? "bg-primary/20 border-primary/50 text-primary"
                                : "bg-background border-border text-muted-foreground hover:text-foreground",
                            )}
                          >
                            {col}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <input
                      type="text"
                      value={yValues.join(", ")}
                      onChange={(e) => updateConfig("y", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
                      placeholder="value"
                      className="w-full h-7 px-2 rounded bg-background border border-border text-xs text-foreground font-mono-deck focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  )}
                </div>
              </div>
            );
          })()}

          {/* v0.10.1.6: Run-Preview button removed — the query auto-runs
              on a 400ms debounce when SQL becomes complete, AND the
              canvas widget itself renders the live result. The button
              was redundant on both fronts. */}
        </div>
      )}

      {/* Preview result */}
      {previewError && (
        <div className="p-2 rounded bg-red-500/10 text-xs text-red-400 flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          {previewError}
        </div>
      )}
      {previewData && !previewError && (
        <div className="border border-border rounded-md overflow-hidden">
          {widget.type === "kpi" ? (
            <div className="p-3">
              <KpiWidget
                label={(widget.config.label as string) || "Preview"}
                value={previewData[0]?.value != null ? Number(previewData[0].value) : 0}
                loading={false}
              />
            </div>
          ) : widget.type === "table" ? (
            <div className="p-3 max-h-48 overflow-auto">
              <TableWidget
                title=""
                columns={
                  previewData.length > 0
                    ? Object.keys(previewData[0]).map((k) => ({ field: k, label: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) }))
                    : []
                }
                rows={previewData}
                loading={false}
              />
            </div>
          ) : (
            <div className="p-3 text-xs text-muted-foreground">
              {previewData.length} row{previewData.length !== 1 ? "s" : ""} returned
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────

function extractSources(widgets: WidgetSpec[], plugins: { slug: string; tables: string[] }[]): string[] {
  const sources = new Set<string>();
  for (const w of widgets) {
    const sql = (w.config.custom_sql || "") as string;
    for (const p of plugins) {
      for (const table of p.tables) {
        if (sql.toLowerCase().includes(table.toLowerCase())) {
          sources.add(p.slug);
        }
      }
    }
  }
  return [...sources];
}
