import { apiFetch } from "@/lib/api";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Download,
  CheckCircle2,
  ArrowUpRight,
  RefreshCw,
  BarChart3,
  Lock,
  Package,
  Trash2,
  ChevronRight,
  AlertTriangle,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import UninstallPluginModal from "@/components/plugins/UninstallPluginModal";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

type PluginCategory = "all" | "analytics" | "marketing" | "finance" | "monitoring" | "content" | "integration" | "premium";

interface CatalogPlugin {
  id: string;
  display_name: string;
  description: string;
  version: string;
  icon?: string;
  category?: string;
  tags?: string[];
  visibility?: string;
  license?: string;
  installed: boolean;
  source?: "official" | "community" | "installed" | "utility";
  type?: string;  // "utility" for utility plugins
  provides?: string[];
  publisher?: { slug: string; name: string; verified?: boolean; website?: string };
  dashboards?: { name: string; label: string }[];
}

const CATEGORIES: { value: PluginCategory; label: string }[] = [
  { value: "all", label: "All" },
  { value: "analytics", label: "Analytics" },
  { value: "integration", label: "Integrations" },
  { value: "monitoring", label: "Monitoring" },
  { value: "content", label: "Content" },
  { value: "premium", label: "Premium" },
];

// ── Community trust warning modal ─────────────────────────────────────────────

function CommunityTrustModal({ pluginName, onConfirm, onCancel }: {
  pluginName: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-xl p-6 max-w-md w-full mx-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
          </div>
          <div>
            <h3 className="font-display text-base text-foreground">Community Plugin</h3>
            <p className="text-xs text-muted-foreground">{pluginName}</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground font-body leading-relaxed">
          This is a <strong className="text-foreground">community plugin</strong> — it is maintained by a third party, not the NousViz core team.
        </p>
        <p className="text-sm text-muted-foreground font-body leading-relaxed">
          Installing a plugin grants it full access to the API process, including your environment variables and database connection. <strong className="text-foreground">Only install plugins you trust.</strong>
        </p>
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onCancel}
            className="flex-1 h-9 rounded-md bg-secondary text-muted-foreground hover:text-foreground text-sm font-body transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 h-9 rounded-md bg-yellow-500/15 text-yellow-400 hover:bg-yellow-500/25 text-sm font-body transition-colors flex items-center justify-center gap-2"
          >
            <Download className="w-3.5 h-3.5" /> Install anyway
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Install button ─────────────────────────────────────────────────────────────

function InstallButton({ pluginId, isCommunity, onInstalled, onCommunityInstallRequest }: {
  pluginId: string;
  isCommunity?: boolean;
  onInstalled: () => void;
  onCommunityInstallRequest?: () => void;
}) {
  const [state, setState] = useState<"idle" | "installing" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function doInstall(e?: React.MouseEvent) {
    e?.stopPropagation();
    setState("installing");
    setErrorMsg("");
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/install`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Install failed");
      setState("done");
      onInstalled();
      window.dispatchEvent(new CustomEvent("nousviz:plugins-changed"));
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Install failed");
      setState("error");
      setTimeout(() => { setState("idle"); setErrorMsg(""); }, 4000);
    }
  }

  function install(e: React.MouseEvent) {
    e.stopPropagation();
    if (isCommunity && onCommunityInstallRequest) {
      onCommunityInstallRequest();
      return;
    }
    doInstall();
  }

  if (state === "done") {
    return (
      <span className="text-xs font-mono-deck text-green-400 flex items-center gap-1">
        <CheckCircle2 className="w-3 h-3" /> Installed
      </span>
    );
  }

  if (state === "installing") {
    return (
      <div className="w-32 space-y-1" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-1.5 text-xs text-primary font-body">
          <RefreshCw className="w-3 h-3 animate-spin shrink-0" />
          Installing…
        </div>
        <div className="h-1.5 rounded-full bg-primary/10 overflow-hidden">
          <div className="h-full w-1/2 bg-primary/60 rounded-full" style={{ animation: "progress-indeterminate 1.5s ease-in-out infinite" }} />
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={install}
      className={cn(
        "text-xs font-body px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors",
        state === "error"
          ? "bg-red-500/10 text-red-400 hover:bg-red-500/20"
          : "bg-primary/10 text-primary hover:bg-primary/20"
      )}
      title={state === "error" ? errorMsg : undefined}
    >
      <Download className="w-3 h-3" />
      {state === "error" ? "Failed — retry" : "Install"}
    </button>
  );
}

// ── Plugin card ────────────────────────────────────────────────────────────────

function PluginCard({
  plugin,
  onInstalled,
  onUninstallClick,
  onCommunityInstallRequest,
  onClick,
  featured,
}: {
  plugin: CatalogPlugin;
  onInstalled: () => void;
  onUninstallClick: (plugin: CatalogPlugin) => void;
  onCommunityInstallRequest?: (plugin: CatalogPlugin) => void;
  onClick: (plugin: CatalogPlugin) => void;
  featured?: boolean;
}) {
  const isPremium = plugin.visibility === "public_premium" || plugin.visibility === "fully_private";
  const isCommunity = plugin.source === "community";

  return (
    <div
      className={cn(
        "bg-card rounded-lg border p-5 flex flex-col transition-colors cursor-pointer group",
        featured ? "border-primary/30 hover:border-primary/60" : "border-border hover:border-primary/30",
        plugin.installed && "ring-1 ring-green-500/20"
      )}
      onClick={() => onClick(plugin)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "h-10 w-10 rounded-lg flex items-center justify-center shrink-0",
            isPremium ? "bg-orange-500/10 text-orange-400"
              : plugin.installed ? "bg-green-500/10 text-green-400"
              : featured ? "bg-primary/10 text-primary"
              : "bg-blue-500/10 text-blue-400"
          )}>
            <Package className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-display text-sm text-foreground">{plugin.display_name}</h3>
              {plugin.publisher?.verified && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />}
              {isPremium && <Lock className="w-3.5 h-3.5 text-orange-400" />}
              {isCommunity && (
                <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                  <Users className="w-2.5 h-2.5" /> community
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {plugin.publisher?.name && `by ${plugin.publisher.name} · `}v{plugin.version}
            </p>
          </div>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors shrink-0 mt-1" />
      </div>

      {/* Description */}
      <p className="text-sm text-muted-foreground font-body flex-1 mb-4 line-clamp-2">
        {plugin.description || "No description provided."}
      </p>

      {/* Tags */}
      {plugin.tags && plugin.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {plugin.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="text-[10px] font-mono-deck px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {plugin.dashboards && plugin.dashboards.length > 0 && (
            <span className="flex items-center gap-1">
              <BarChart3 className="w-3 h-3" /> {plugin.dashboards.length} dashboard{plugin.dashboards.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {plugin.installed ? (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono-deck text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Installed
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onUninstallClick(plugin); }}
              className="text-xs font-body px-2 py-1 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors flex items-center gap-1"
              title="Uninstall plugin"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ) : isPremium ? (
          <button
            disabled
            className="text-xs font-body px-3 py-1.5 rounded-md bg-orange-500/10 text-orange-400/60 flex items-center gap-1 cursor-not-allowed"
            title="Premium — contact plugins@nousviz.com"
          >
            <Lock className="w-3 h-3" /> Premium
          </button>
        ) : (
          <InstallButton
            pluginId={plugin.id}
            isCommunity={isCommunity}
            onInstalled={onInstalled}
            onCommunityInstallRequest={onCommunityInstallRequest ? () => onCommunityInstallRequest(plugin) : undefined}
          />
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  useMarkBootReadyOnMount();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<PluginCategory>("all");
  const [plugins, setPlugins] = useState<CatalogPlugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [uninstallTarget, setUninstallTarget] = useState<CatalogPlugin | null>(null);
  const [communityTrustTarget, setCommunityTrustTarget] = useState<CatalogPlugin | null>(null);

  function loadCatalog() {
    apiFetch("/api/plugins/catalog")
      .then((r) => r.json())
      .then((data) => setPlugins(data.plugins ?? []))
      .catch((err) => console.error("MarketplacePage: failed to load plugin catalog", err))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadCatalog(); }, []);

  const filtered = plugins.filter((p) => {
    if (category === "premium") {
      if (p.visibility !== "premium" && p.visibility !== "public_premium" && p.visibility !== "fully_private") return false;
    } else if (category !== "all" && p.category !== category) {
      return false;
    }
    if (
      search &&
      !p.display_name?.toLowerCase().includes(search.toLowerCase()) &&
      !p.description?.toLowerCase().includes(search.toLowerCase())
    )
      return false;
    return true;
  });

  // Each plugin appears in exactly one section (utility / official / more).
  // Installed-state styling lives on the card itself — no separate "Installed" section.
  const utilities = filtered.filter(p => p.type === "utility");
  const regularPlugins = filtered.filter(p => p.type !== "utility");
  const community = regularPlugins.filter(p => p.source === "community");
  const official = regularPlugins.filter(
    p => p.source !== "community" && p.publisher?.verified && p.visibility !== "public_premium" && p.visibility !== "fully_private"
  );
  const rest = regularPlugins.filter(
    p => p.source !== "community" && (!p.publisher?.verified || p.visibility === "public_premium" || p.visibility === "fully_private")
  );

  const handlePluginClick = (plugin: CatalogPlugin) => {
    navigate(`/marketplace/${plugin.id}`);
  };

  return (
    <div className="max-w-[1400px] space-y-6">

      {/* Hero */}
      <div className="bg-card rounded-lg border border-border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-2xl text-foreground mb-1">Plugin Marketplace</h2>
            <p className="text-sm text-muted-foreground font-body">
              Connect your data sources, extend your analytics, and build custom workflows.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => navigate("/install-plugin")}
              className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
            >
              <Download className="w-3.5 h-3.5" /> Install Plugin
            </button>
            <button
              onClick={() => navigate("/build-a-plugin")}
              className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Build a plugin <ArrowUpRight className="w-3 h-3" />
            </button>
          </div>
        </div>
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search plugins…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-4 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
          />
        </div>
        <div className="flex items-center gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategory(cat.value)}
              className={cn(
                "h-9 px-3 rounded-md text-xs font-body transition-colors",
                category === cat.value ? "bg-primary/15 text-primary" : "bg-secondary text-muted-foreground hover:text-foreground"
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-5 space-y-3 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-secondary" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-4 w-32 bg-secondary rounded" />
                  <div className="h-3 w-20 bg-secondary rounded" />
                </div>
              </div>
              <div className="h-3 w-full bg-secondary rounded" />
              <div className="h-3 w-3/4 bg-secondary rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-8">

          {/* Utilities */}
          {utilities.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Package className="w-3.5 h-3.5 text-primary" /> Utilities
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {utilities.map(plugin => (
                  <PluginCard
                    key={plugin.id}
                    plugin={plugin}
                    onInstalled={loadCatalog}
                    onUninstallClick={setUninstallTarget}
                    onClick={handlePluginClick}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Official / featured */}
          {official.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" /> Official
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {official.map(plugin => (
                  <PluginCard
                    key={plugin.id}
                    plugin={plugin}
                    onInstalled={loadCatalog}
                    onUninstallClick={setUninstallTarget}
                    onClick={handlePluginClick}
                    featured
                  />
                ))}
              </div>
            </div>
          )}

          {/* More plugins */}
          {rest.length > 0 && (
            <div className="space-y-3">
              {(utilities.length > 0 || official.length > 0) && (
                <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider">
                  More plugins
                </h3>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {rest.map(plugin => (
                  <PluginCard
                    key={plugin.id}
                    plugin={plugin}
                    onInstalled={loadCatalog}
                    onUninstallClick={setUninstallTarget}
                    onClick={handlePluginClick}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Community plugins */}
          {community.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Users className="w-3.5 h-3.5 text-yellow-400" /> Community
                </h3>
                <span className="text-[10px] font-body text-muted-foreground/60">
                  — Third-party plugins. Review before installing.
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {community.map(plugin => (
                  <PluginCard
                    key={plugin.id}
                    plugin={plugin}
                    onInstalled={loadCatalog}
                    onCommunityInstallRequest={setCommunityTrustTarget}
                    onUninstallClick={setUninstallTarget}
                    onClick={handlePluginClick}
                  />
                ))}
              </div>
            </div>
          )}

          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              No plugins found matching your search.
            </div>
          )}
        </div>
      )}

      {/* Developer CTA */}
      <div className="bg-card rounded-lg border border-border p-6 text-center">
        <h3 className="font-display text-lg text-foreground mb-2">Build for the Marketplace</h3>
        <p className="text-sm text-muted-foreground font-body mb-4 max-w-lg mx-auto">
          Create plugins that connect to any data source. Publish them for the community or sell premium plugins.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => navigate("/build-a-plugin")}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            Plugin Developer Guide <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Uninstall modal */}
      {uninstallTarget && (
        <UninstallPluginModal
          pluginId={uninstallTarget.id}
          pluginName={uninstallTarget.display_name}
          onClose={() => setUninstallTarget(null)}
          onComplete={() => {
            setUninstallTarget(null);
            loadCatalog();
            window.dispatchEvent(new Event("nousviz:plugins-changed"));
          }}
        />
      )}

      {/* Community trust warning modal */}
      {communityTrustTarget && (
        <CommunityTrustModal
          pluginName={communityTrustTarget.display_name}
          onCancel={() => setCommunityTrustTarget(null)}
          onConfirm={async () => {
            const pluginId = communityTrustTarget.id;
            setCommunityTrustTarget(null);
            try {
              const res = await apiFetch(`/api/plugins/${pluginId}/install`, { method: "POST" });
              const data = await res.json();
              if (!res.ok) throw new Error(data.detail || "Install failed");
              loadCatalog();
              window.dispatchEvent(new CustomEvent("nousviz:plugins-changed"));
            } catch {
              // silent — user can retry from the card
            }
          }}
        />
      )}
    </div>
  );
}
