import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  LayoutDashboard,
  Plug,
  Database,
  MessageSquareText,
  Bell,
  HelpCircle,
  Store,
  Settings,
  Activity,
  BarChart3,
  ArrowRight,
  StickyNote,
  Hash,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

const API_BASE = "/api";

interface SearchResult {
  id: string;
  section: string;
  icon: typeof Search;
  title: string;
  subtitle?: string;
  path?: string;
  action?: () => void;
  /** Extra search keywords. Useful for renamed surfaces — e.g. "overview"
   * still finds "Home" after P110 so muscle-memory keyboard nav keeps working. */
  aliases?: string[];
}

// ── Static pages ─────────────────────────────────────────────────────

const PAGES: SearchResult[] = [
  { id: "p-home",         section: "Pages", icon: LayoutDashboard,   title: "Home",              path: "/",           aliases: ["overview", "launchpad", "dashboard"] },
  { id: "p-fusions",      section: "Pages", icon: BarChart3,          title: "Fusions",           path: "/fusions" },
  { id: "p-alerts",       section: "Pages", icon: Bell,               title: "Alerts",            path: "/alerts" },
  { id: "p-annotations",  section: "Pages", icon: MessageSquareText,  title: "Annotations",       path: "/annotations" },
  { id: "p-marketplace",  section: "Pages", icon: Store,              title: "Marketplace",       path: "/marketplace" },
  { id: "p-plugins",      section: "Pages", icon: Plug,               title: "Installed Plugins", path: "/plugins" },
  { id: "p-connections",  section: "Pages", icon: Plug,               title: "Connections",       path: "/connections" },
  { id: "p-datasets",     section: "Pages", icon: Database,           title: "Datasets",          path: "/datasets" },
  { id: "p-analytics",    section: "Pages", icon: Activity,           title: "Usage Analytics",   path: "/analytics" },
  { id: "p-settings",     section: "Pages", icon: Settings,           title: "Settings",          path: "/settings" },
];

const HELP: SearchResult[] = [
  { id: "h-install",     section: "Help", icon: HelpCircle, title: "How to install a plugin",    subtitle: "Browse the marketplace and click Install on any plugin", path: "/marketplace" },
  { id: "h-fusion",      section: "Help", icon: HelpCircle, title: "What is a Fusion?",           subtitle: "A Fusion combines KPIs from multiple data sources into one view — go to Fusions to create one", path: "/fusions" },
  { id: "h-alert",       section: "Help", icon: HelpCircle, title: "How do alerts work?",         subtitle: "Alerts watch a metric and fire when it crosses a threshold — set them up on the Alerts page", path: "/alerts" },
  { id: "h-annotation",  section: "Help", icon: HelpCircle, title: "What are annotations?",       subtitle: "Annotations mark events (deployments, incidents, campaigns) on your data timeline", path: "/annotations" },
  { id: "h-connections", section: "Help", icon: HelpCircle, title: "How do I connect a database?", subtitle: "Go to Connections to add a MySQL, Postgres, or API data source", path: "/connections" },
  { id: "h-datasets",    section: "Help", icon: HelpCircle, title: "Where is my data?",            subtitle: "Datasets shows all tables registered by installed plugins", path: "/datasets" },
];

// ── Section config ───────────────────────────────────────────────────

const SECTION_ORDER = ["Pages", "Plugins", "Datasets", "Annotations", "Notes", "Alerts", "Docs", "Help"];

const SECTION_ICONS: Record<string, typeof Search> = {
  Pages: LayoutDashboard,
  Plugins: Plug,
  Datasets: Database,
  Annotations: MessageSquareText,
  Notes: StickyNote,
  Alerts: Bell,
  Docs: BookOpen,
  Help: HelpCircle,
};

// ── Component ────────────────────────────────────────────────────────

export default function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [dynamicResults, setDynamicResults] = useState<SearchResult[]>([]);
  const [loadingDynamic, setLoadingDynamic] = useState(false);
  const [pluginPages, setPluginPages] = useState<SearchResult[]>([]);

  // Load installed plugin pages on mount
  useEffect(() => {
    fetch(`${API_BASE}/plugins`)
      .then(r => r.json())
      .then(data => {
        const pages: SearchResult[] = [];
        for (const p of data.plugins || []) {
          pages.push({
            id: `pl-${p.id}`,
            section: "Plugins",
            icon: Activity,
            title: p.display_name || p.id,
            subtitle: `Installed · v${p.version}`,
            path: `/plugin/${p.id}/dashboards`,
          });
          for (const d of p.dashboards || []) {
            pages.push({
              id: `pl-${p.id}-${d.name}`,
              section: "Pages",
              icon: BarChart3,
              title: d.label || d.name,
              subtitle: p.display_name || p.id,
              path: `/plugin/${p.id}/dashboards/${d.name}`,
            });
          }
        }
        setPluginPages(pages);
      })
      .catch(() => {});
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIdx(0);
      setDynamicResults([]);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Fetch dynamic results (annotations, notes, alerts, datasets) on query change
  useEffect(() => {
    if (!query || query.length < 2) {
      setDynamicResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoadingDynamic(true);
      const dynamic: SearchResult[] = [];

      try {
        // Annotations
        const annRes = await apiFetch(`${API_BASE}/annotations`);
        const annData = await annRes.json();
        for (const a of annData.annotations || []) {
          if (
            a.title?.toLowerCase().includes(query.toLowerCase()) ||
            a.description?.toLowerCase().includes(query.toLowerCase())
          ) {
            dynamic.push({
              id: `ann-${a.id}`,
              section: "Annotations",
              icon: MessageSquareText,
              title: a.title,
              subtitle: `${a.category} · ${a.date_start}`,
              path: "/annotations",
            });
          }
        }

        // Notes
        const noteRes = await apiFetch(`${API_BASE}/notes`);
        const noteData = await noteRes.json();
        for (const n of noteData.notes || []) {
          if (n.body?.toLowerCase().includes(query.toLowerCase())) {
            dynamic.push({
              id: `note-${n.id}`,
              section: "Notes",
              icon: StickyNote,
              title: n.body.slice(0, 60) + (n.body.length > 60 ? "..." : ""),
              subtitle: n.page_path,
              path: n.page_path,
            });
          }
        }

        // Alerts
        const alertRes = await apiFetch(`${API_BASE}/alerts`);
        const alertData = await alertRes.json();
        for (const a of alertData.alerts || []) {
          if (
            a.label?.toLowerCase().includes(query.toLowerCase()) ||
            a.description?.toLowerCase().includes(query.toLowerCase())
          ) {
            dynamic.push({
              id: `alert-${a.id}`,
              section: "Alerts",
              icon: Bell,
              title: a.label,
              subtitle: `${a.enabled ? "Active" : "Disabled"} · ${a.dataset}`,
              path: `/alerts`,
            });
          }
        }

        // Docs
        const docsRes = await apiFetch(`${API_BASE}/docs`);
        const docsData = await docsRes.json();
        for (const doc of docsData.docs || []) {
          if (
            doc.title?.toLowerCase().includes(query.toLowerCase()) ||
            doc.slug?.toLowerCase().includes(query.toLowerCase())
          ) {
            dynamic.push({
              id: `doc-${doc.slug}`,
              section: "Docs",
              icon: BookOpen,
              title: doc.title,
              subtitle: doc.category || "Documentation",
              path: `/docs/${doc.slug}`,
            });
          }
        }
      } catch {
        // Silently fail on search errors
      }

      setDynamicResults(dynamic);
      setLoadingDynamic(false);
    }, 200); // Debounce

    return () => clearTimeout(timer);
  }, [query]);

  // Combine static + dynamic results, filter by query
  useEffect(() => {
    const q = query.toLowerCase();
    let all: SearchResult[] = [];

    if (!q) {
      // Show core pages + installed plugins when empty
      all = [...PAGES.slice(0, 6), ...pluginPages.filter(r => r.section === "Plugins")];
    } else {
      // Filter static results
      const matchStatic = (r: SearchResult) =>
        r.title.toLowerCase().includes(q) ||
        (r.subtitle && r.subtitle.toLowerCase().includes(q)) ||
        (r.aliases && r.aliases.some(a => a.toLowerCase().includes(q)));

      all = [
        ...PAGES.filter(matchStatic),
        ...pluginPages.filter(matchStatic),
        ...HELP.filter(matchStatic),
        ...dynamicResults,
      ];
    }

    setResults(all);
    setSelectedIdx(0);
  }, [query, dynamicResults]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && results[selectedIdx]) {
        e.preventDefault();
        const result = results[selectedIdx];
        if (result.path) {
          navigate(result.path);
          onClose();
        } else if (result.action) {
          result.action();
          onClose();
        }
      } else if (e.key === "Escape") {
        onClose();
      }
    },
    [results, selectedIdx, navigate, onClose]
  );

  if (!open) return null;

  // Group results by section
  const grouped = new Map<string, SearchResult[]>();
  for (const r of results) {
    if (!grouped.has(r.section)) grouped.set(r.section, []);
    grouped.get(r.section)!.push(r);
  }

  // Flatten for index tracking
  let flatIdx = 0;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-[60]" onClick={onClose} />

      {/* Palette */}
      <div className="fixed top-[15%] left-1/2 -translate-x-1/2 w-[560px] max-h-[500px] bg-card border border-border rounded-xl shadow-2xl z-[60] flex flex-col overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 h-12 border-b border-border shrink-0">
          <Search className="w-4 h-4 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, plugins, datasets, annotations..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none font-body"
          />
          <kbd className="h-5 px-1.5 rounded border border-border bg-background text-[10px] font-mono-deck text-muted-foreground flex items-center">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto py-2">
          {results.length === 0 && query.length > 0 && !loadingDynamic && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No results for "{query}"
            </div>
          )}

          {loadingDynamic && results.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              Searching...
            </div>
          )}

          {SECTION_ORDER.map((section) => {
            const items = grouped.get(section);
            if (!items || items.length === 0) return null;
            const SectionIcon = SECTION_ICONS[section] || Hash;

            return (
              <div key={section}>
                <div className="px-4 pt-2 pb-1 flex items-center gap-1.5">
                  <SectionIcon className="w-3 h-3 text-muted-foreground" />
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                    {section}
                  </span>
                </div>
                {items.map((result) => {
                  const idx = flatIdx++;
                  const isSelected = idx === selectedIdx;
                  const Icon = result.icon;

                  return (
                    <button
                      key={result.id}
                      onClick={() => {
                        if (result.path) navigate(result.path);
                        else if (result.action) result.action();
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIdx(idx)}
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-2 text-left transition-colors",
                        isSelected ? "bg-primary/10" : "hover:bg-secondary/50"
                      )}
                    >
                      <Icon className={cn("w-4 h-4 shrink-0", isSelected ? "text-primary" : "text-muted-foreground")} />
                      <div className="flex-1 min-w-0">
                        <p className={cn("text-sm truncate", isSelected ? "text-foreground" : "text-foreground/80")}>
                          {result.title}
                        </p>
                        {result.subtitle && (
                          <p className="text-xs text-muted-foreground truncate mt-0.5">{result.subtitle}</p>
                        )}
                      </div>
                      {isSelected && <ArrowRight className="w-3 h-3 text-primary shrink-0" />}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-border flex items-center gap-4 text-[10px] text-muted-foreground shrink-0">
          <span className="flex items-center gap-1">
            <kbd className="h-4 px-1 rounded border border-border bg-background font-mono-deck">↑↓</kbd> Navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="h-4 px-1 rounded border border-border bg-background font-mono-deck">↵</kbd> Open
          </span>
          <span className="flex items-center gap-1">
            <kbd className="h-4 px-1 rounded border border-border bg-background font-mono-deck">ESC</kbd> Close
          </span>
        </div>
      </div>
    </>
  );
}
