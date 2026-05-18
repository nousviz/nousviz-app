import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Layers, Database, BarChart3, Plug, Settings, AlertTriangle,
  CheckCircle2, Package, XCircle,
} from "lucide-react";

interface ModuleInfo {
  name: string;
  display_name: string;
  description: string;
  version: string;
  enabled: boolean;
  enabled_by_default: boolean;
  dashboards: { name: string; label: string }[];
  navigation: { label: string; path: string }[];
  tables: string[];
  has_routes: boolean;
  has_settings: boolean;
}

export default function PluginModulesTab({ pluginId }: { pluginId: string }) {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [disableTarget, setDisableTarget] = useState<ModuleInfo | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [restartNeeded, setRestartNeeded] = useState(false);

  useEffect(() => {
    apiFetch(`/api/plugins/${pluginId}/modules`)
      .then((r) => r.json())
      .then((d) => setModules(d.modules || []))
      .catch((e) => console.error("Modules load failed:", e))
      .finally(() => setLoading(false));
  }, [pluginId]);

  async function toggle(name: string, enable: boolean) {
    setToggling(name);
    try {
      await apiFetch(`/api/plugins/${pluginId}/modules/${name}/${enable ? "enable" : "disable"}`, { method: "POST" });
      setModules((prev) => prev.map((m) => (m.name === name ? { ...m, enabled: enable } : m)));
      setRestartNeeded(true);
    } catch (e) {
      console.error("Module toggle failed:", e);
    } finally {
      setToggling(null);
      setDisableTarget(null);
    }
  }

  const enabledCount = modules.filter((m) => m.enabled).length;

  if (loading) {
    return (
      <div className="max-w-[900px]">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-5 animate-pulse">
              <div className="h-10 w-10 bg-secondary rounded-xl mb-4" />
              <div className="h-4 w-24 bg-secondary rounded mb-2" />
              <div className="h-3 w-40 bg-secondary rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (modules.length === 0) {
    return (
      <div className="py-16 text-center border border-dashed border-border rounded-lg max-w-[500px] mx-auto">
        <Layers className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">This plugin has no modules</p>
      </div>
    );
  }

  return (
    <div className="max-w-[900px] space-y-6">
      <div>
        <h2 className="font-display text-xl text-foreground">Modules</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {enabledCount} of {modules.length} modules enabled. Each module adds dashboards, API routes, and features.
        </p>
      </div>

      {restartNeeded && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-orange-500/10 border border-orange-500/20 text-sm text-orange-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          API restart required to apply module changes.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((mod) => (
          <div
            key={mod.name}
            className={cn(
              "bg-card rounded-xl border overflow-hidden transition-all hover:shadow-md",
              mod.enabled ? "border-border" : "border-border/50 opacity-70"
            )}
          >
            <div className="p-5 pb-3">
              <div className="flex items-start justify-between mb-3">
                <div className={cn(
                  "h-10 w-10 rounded-xl flex items-center justify-center",
                  mod.enabled ? "bg-primary/10" : "bg-secondary"
                )}>
                  <Package className={cn("w-5 h-5", mod.enabled ? "text-primary" : "text-muted-foreground")} />
                </div>
                <div className={cn(
                  "flex items-center gap-1 text-[10px] font-mono-deck px-2 py-0.5 rounded-full",
                  mod.enabled ? "bg-green-500/10 text-green-400" : "bg-secondary text-muted-foreground"
                )}>
                  {mod.enabled ? <CheckCircle2 className="w-2.5 h-2.5" /> : <XCircle className="w-2.5 h-2.5" />}
                  {mod.enabled ? "Enabled" : "Disabled"}
                </div>
              </div>

              <h3 className="font-display text-sm text-foreground">{mod.display_name}</h3>
              <p className="text-[10px] font-mono-deck text-muted-foreground mt-0.5">v{mod.version}</p>

              {mod.description && (
                <p className="text-xs text-muted-foreground mt-2 leading-relaxed line-clamp-2">{mod.description}</p>
              )}
            </div>

            <div className="px-5 pb-3">
              <div className="flex flex-wrap gap-2">
                {mod.dashboards.map((d) => (
                  <span key={d.name} className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full">
                    <BarChart3 className="w-2.5 h-2.5" />{d.label}
                  </span>
                ))}
                {mod.has_routes && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full">
                    <Plug className="w-2.5 h-2.5" />API
                  </span>
                )}
                {mod.tables.length > 0 && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full">
                    <Database className="w-2.5 h-2.5" />{mod.tables.length} table{mod.tables.length > 1 ? "s" : ""}
                  </span>
                )}
                {mod.has_settings && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full">
                    <Settings className="w-2.5 h-2.5" />Config
                  </span>
                )}
              </div>
            </div>

            <div className="px-5 py-3 border-t border-border bg-secondary/10 flex items-center gap-2">
              {mod.enabled ? (
                <>
                  {mod.has_settings && (
                    <a href={`/plugin/${pluginId}/settings`}
                      className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80 transition-colors inline-flex items-center gap-1.5 flex-1 justify-center">
                      <Settings className="w-3 h-3" />Configure
                    </a>
                  )}
                  <button onClick={() => setDisableTarget(mod)} disabled={toggling === mod.name}
                    className={cn("h-8 px-3 rounded-md text-xs transition-colors inline-flex items-center justify-center text-muted-foreground hover:text-red-400 hover:bg-red-500/10", !mod.has_settings && "flex-1")}>
                    {toggling === mod.name ? "Disabling…" : "Disable"}
                  </button>
                </>
              ) : (
                <button onClick={() => toggle(mod.name, true)} disabled={toggling === mod.name}
                  className="h-8 px-4 rounded-md bg-primary text-xs text-white hover:bg-primary/90 transition-colors flex-1 flex items-center justify-center gap-1.5 disabled:opacity-50">
                  {toggling === mod.name ? "Enabling…" : "Enable Module"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {disableTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDisableTarget(null)}>
          <div className="bg-card border border-border rounded-xl p-6 max-w-md mx-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="h-10 w-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                <Package className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="font-display text-base text-foreground">Disable {disableTarget.display_name}?</h3>
                <p className="text-xs text-muted-foreground">v{disableTarget.version}</p>
              </div>
            </div>
            <div className="space-y-2 text-sm mb-5">
              {disableTarget.dashboards.length > 0 && (
                <p className="flex items-start gap-2 text-muted-foreground">
                  <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <span>Removes: <strong className="text-foreground">{disableTarget.dashboards.map((d) => d.label).join(", ")}</strong></span>
                </p>
              )}
              {disableTarget.has_routes && (
                <p className="flex items-start gap-2 text-muted-foreground">
                  <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  Unloads API routes
                </p>
              )}
              {disableTarget.tables.length > 0 && (
                <p className="flex items-start gap-2 text-muted-foreground">
                  <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                  <span>Data in <strong className="font-mono-deck text-foreground">{disableTarget.tables.join(", ")}</strong> preserved</span>
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-500/5 border border-orange-500/20 text-xs text-orange-400 mb-5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Requires API restart to take effect
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button onClick={() => setDisableTarget(null)}
                className="h-9 px-4 rounded-md bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors">Cancel</button>
              <button onClick={() => toggle(disableTarget.name, false)} disabled={toggling === disableTarget.name}
                className="h-9 px-4 rounded-md bg-red-500 text-sm text-white hover:bg-red-600 transition-colors disabled:opacity-50">
                {toggling === disableTarget.name ? "Disabling…" : "Disable Module"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
