import { apiFetch } from "@/lib/api";
import { useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import { Link } from "react-router-dom";
import {
  Package,
  RefreshCw,
  Store,
  Trash2,
  ExternalLink,
  ArrowUp,
  CheckCircle2,
} from "lucide-react";
import UninstallPluginModal from "@/components/plugins/UninstallPluginModal";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface UpdateStatus {
  source_class: string;
  installed_version: string | null;
  latest_version: string | null;
  update_available: boolean;
  last_error: string | null;
}

interface FrontendStatus {
  components: { name: string; path: string }[];
  trusted: boolean;
  needs_consent: boolean;
  // B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path.
  admin_proxy?: boolean;
}

interface Plugin {
  id: string;
  display_name: string;
  version: string;
  description?: string;
  publisher?: { name: string; verified?: boolean; website?: string };
  category?: string;
  type?: string;
  dashboards?: { name: string; label: string }[];
  update_status?: UpdateStatus;
  frontend?: FrontendStatus;
}

// v0.10.0.7 (Phase 14 / P14.1): data fetch moved to TanStack Query.
// Repeat navigation to /plugins now reads from the shared query cache
// instead of re-fetching. Sidebar prefetch on hover (see Sidebar.tsx)
// warms the cache so the click feels instant.

// Shape of /api/plugins — either a bare array (legacy) or {plugins: [...]}.
type PluginsResponse = Plugin[] | { plugins: Plugin[] };

// Cache key — used by useApiQuery and by the sidebar hover-prefetch.
export const PLUGINS_QUERY_KEY = ["plugins", "list"] as const;

export default function PluginsPage() {
  useMarkBootReadyOnMount();
  const queryClient = useQueryClient();

  // Mutation-side state (these are operator-visible action states, not data).
  const [uninstallTarget, setUninstallTarget] = useState<{ id: string; name: string } | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);

  // Data fetch via the shared query cache.
  // Retry budget mirrors the pre-v0.10.0.7 logic: 5 attempts × ~1.5s spacing
  // covers the typical PM2 reload window during plugin install/uninstall.
  // Pre-existing cached data stays on screen if a refetch fails (TanStack
  // default — no manual "preserve on error" handling needed).
  const { data, isLoading, error } = useApiQuery<PluginsResponse>(
    PLUGINS_QUERY_KEY,
    "/api/plugins",
    {
      retry: 4,                                  // 5 attempts total
      retryDelay: () => 1500,                    // fixed 1.5s — matches old behaviour
    },
  );

  const plugins: Plugin[] = useMemo(
    () => (Array.isArray(data) ? data : data?.plugins ?? []),
    [data],
  );

  const loadError = error
    ? "Failed to load plugins. Reload the page to retry."
    : null;

  // Trigger a background refresh after mutations. The cache shows
  // stale-while-revalidate — UI doesn't flash a loading state, but
  // new data appears once the refetch lands.
  const refreshPlugins = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: PLUGINS_QUERY_KEY });
  }, [queryClient]);

  const handleTrustFrontend = async (pluginId: string) => {
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/trust-frontend`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setUpdateMessage(`Trust failed for ${pluginId}: ${body?.detail || res.status}`);
      } else {
        setUpdateMessage(`Trusted ${pluginId} frontend code. Hard-refresh to load components.`);
        refreshPlugins();
      }
    } catch (e: unknown) {
      setUpdateMessage(`Trust failed for ${pluginId}: ${e instanceof Error ? e.message : "request failed"}`);
    }
  };

  const handleRevokeFrontend = async (pluginId: string) => {
    if (!confirm(`Revoke frontend code trust for ${pluginId}? Custom widgets from this plugin will stop loading on next page load.`)) {
      return;
    }
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/revoke-frontend-trust`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setUpdateMessage(`Revoke failed for ${pluginId}: ${body?.detail || res.status}`);
      } else {
        setUpdateMessage(`Revoked ${pluginId} frontend trust.`);
        refreshPlugins();
      }
    } catch (e: unknown) {
      setUpdateMessage(`Revoke failed for ${pluginId}: ${e instanceof Error ? e.message : "request failed"}`);
    }
  };

  const handleCheckUpdate = async (pluginId: string, displayName: string) => {
    setUpdateMessage(`Checking ${displayName} for updates...`);
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/check-update`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setUpdateMessage(`Check failed for ${displayName}: ${data?.detail || res.status}`);
        return;
      }
      if (data.update_available) {
        setUpdateMessage(
          `${displayName}: update available (v${data.installed_version} → v${data.latest_version})`,
        );
      } else if (data.last_error) {
        setUpdateMessage(`${displayName}: ${data.last_error}`);
      } else {
        setUpdateMessage(`${displayName} is up to date (v${data.installed_version})`);
      }
      refreshPlugins();
    } catch (e: unknown) {
      setUpdateMessage(`Check failed for ${displayName}: ${e instanceof Error ? e.message : "request failed"}`);
    }
  };

  const handleUpdate = async (pluginId: string, displayName: string) => {
    if (updatingId) return;
    setUpdatingId(pluginId);
    setUpdateMessage(null);
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/update`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setUpdateMessage(`Update failed for ${displayName}: ${data?.detail || "unknown error"}`);
      } else {
        setUpdateMessage(
          `Updated ${displayName}: v${data.from_version || "?"} → v${data.to_version || "?"}`
        );
        refreshPlugins();
      }
    } catch (e: unknown) {
      setUpdateMessage(`Update failed for ${displayName}: ${e instanceof Error ? e.message : "request failed"}`);
    } finally {
      setUpdatingId(null);
    }
  };

  // No useEffect needed for initial load — useApiQuery fetches on mount.

  return (
    <div className="max-w-[1400px] space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground font-body">
            Manage your active plugins and configure settings.
          </p>
        </div>
        <Link
          to="/marketplace"
          className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <Store className="w-4 h-4" /> Browse Marketplace
        </Link>
      </div>

      {isLoading && plugins.length === 0 && (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-md bg-secondary" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 w-32 bg-secondary rounded" />
                  <div className="h-2.5 w-20 bg-secondary/60 rounded" />
                </div>
              </div>
              <div className="h-3 w-full bg-secondary/40 rounded" />
              <div className="h-3 w-2/3 bg-secondary/40 rounded" />
            </div>
          ))}
        </div>
      )}
      {loadError && <p className="text-sm text-red-400">{loadError}</p>}
      {updateMessage && (
        <div className="rounded-md border border-blue-500/40 bg-blue-500/10 p-3 text-sm text-blue-300 flex items-center justify-between">
          <span>{updateMessage}</span>
          <button
            type="button"
            onClick={() => setUpdateMessage(null)}
            className="text-blue-300 hover:text-blue-100 text-xs"
          >
            dismiss
          </button>
        </div>
      )}

      {!isLoading && !loadError && plugins.length === 0 && (
        <div className="py-20 text-center border border-dashed border-border rounded-lg">
          <Store className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
          <p className="text-sm text-muted-foreground mb-4">No plugins installed yet.</p>
          <Link
            to="/marketplace"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Browse the Marketplace
          </Link>
        </div>
      )}

      {!isLoading && !loadError && plugins.length > 0 && (
        <div className="space-y-3">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="bg-card rounded-lg border border-border p-5 flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0 bg-blue-500/10 text-blue-400">
                <Package className="w-5 h-5" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-display text-sm text-foreground">{plugin.display_name || plugin.id}</h3>
                  <span className="text-xs font-mono-deck text-muted-foreground">v{plugin.version}</span>
                  {plugin.publisher?.name && (
                    <span className="text-xs text-muted-foreground inline-flex items-center gap-1">
                      by {plugin.publisher.name}
                      {plugin.publisher.verified && <CheckCircle2 className="w-3 h-3 text-blue-400" />}
                    </span>
                  )}
                  {plugin.type === "utility" && (
                    <span className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      utility
                    </span>
                  )}
                  {plugin.update_status?.update_available && (
                    <span
                      className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40 inline-flex items-center gap-1"
                      title={`Latest: v${plugin.update_status.latest_version}`}
                    >
                      <ArrowUp className="w-2.5 h-2.5" />
                      v{plugin.update_status.latest_version}
                    </span>
                  )}
                  {/* B151 (v0.9.4): frontend trust state */}
                  {plugin.frontend && plugin.frontend.components.length > 0 && (
                    plugin.frontend.trusted ? (
                      <span
                        className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        title={`Frontend code trusted: ${plugin.frontend.components.map(c => c.name).join(", ")}`}
                      >
                        Frontend trusted
                      </span>
                    ) : (
                      <span
                        className="text-[10px] font-display uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        title={`Pending trust: ${plugin.frontend.components.map(c => c.name).join(", ")}`}
                      >
                        Frontend pending
                      </span>
                    )
                  )}
                </div>
                {plugin.description && (
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{plugin.description}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                {plugin.frontend && plugin.frontend.components.length > 0 && !plugin.frontend.trusted && (
                  <button
                    onClick={() => handleTrustFrontend(plugin.id)}
                    className="h-8 px-3 rounded-md text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 transition-colors"
                    title="Plugin includes custom frontend code. Click to grant trust."
                  >
                    Trust frontend
                  </button>
                )}
                {plugin.frontend && plugin.frontend.trusted && (
                  <button
                    onClick={() => handleRevokeFrontend(plugin.id)}
                    className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors"
                    title="Revoke frontend code trust"
                  >
                    Revoke trust
                  </button>
                )}
                {plugin.update_status?.update_available && (
                  <button
                    onClick={() => handleUpdate(plugin.id, plugin.display_name || plugin.id)}
                    disabled={updatingId === plugin.id}
                    className={`h-8 px-3 rounded-md flex items-center gap-1.5 text-xs transition-colors ${
                      updatingId === plugin.id
                        ? "bg-muted text-muted-foreground cursor-wait"
                        : "bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 border border-blue-500/40"
                    }`}
                    title={`Update from v${plugin.update_status.installed_version} to v${plugin.update_status.latest_version}`}
                  >
                    <ArrowUp className="w-3.5 h-3.5" />
                    {updatingId === plugin.id ? "Updating…" : "Update"}
                  </button>
                )}
                <Link
                  to={plugin.type === "utility" ? `/plugin/${plugin.id}/settings` : `/plugins/${plugin.id}`}
                  className="h-8 px-3 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> {plugin.type === "utility" ? "Configure" : "Details"}
                </Link>
                <button
                  onClick={() => handleCheckUpdate(plugin.id, plugin.display_name || plugin.id)}
                  className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                  title="Check for updates"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setUninstallTarget({ id: plugin.id, name: plugin.display_name || plugin.id })}
                  className="h-8 w-8 rounded-md bg-red-500/10 hover:bg-red-500/20 flex items-center justify-center text-red-400 hover:text-red-300 transition-colors"
                  title={`Uninstall ${plugin.display_name || plugin.id}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {uninstallTarget && (
        <UninstallPluginModal
          pluginId={uninstallTarget.id}
          pluginName={uninstallTarget.name}
          onClose={() => setUninstallTarget(null)}
          onComplete={() => {
            setUninstallTarget(null);
            refreshPlugins();
            window.dispatchEvent(new CustomEvent("nousviz:plugins-changed"));
          }}
        />
      )}
    </div>
  );
}
