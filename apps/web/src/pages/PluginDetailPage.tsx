import { apiFetch } from "@/lib/api";
/**
 * Plugin detail page — full-page view for a single plugin from the catalog.
 * Reachable from:
 *   /plugins/:pluginId          — from the Installed Plugins page
 *   /marketplace/:pluginId      — from the Marketplace
 *
 * Loads from GET /api/plugins/catalog and filters by slug. Falls back to
 * GET /api/plugins/:id for installed plugins not in the catalog.
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate, Navigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpRight,
  BarChart3,
  Bell,
  CheckCircle2,
  Database,
  Download,
  ExternalLink,
  GitBranch,
  Globe,
  Layout,
  Lock,
  Navigation,
  Package,
  Plug,
  Settings,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import UninstallPluginModal from "@/components/plugins/UninstallPluginModal";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PluginDetail {
  id: string;
  display_name: string;
  description?: string;
  long_description?: string;
  version: string;
  icon?: string;
  category?: string;
  type?: string;
  tags?: string[];
  visibility?: string;
  license?: string;
  homepage?: string;
  repository?: string;
  changelog_url?: string;
  support_url?: string;
  installed: boolean;
  publisher?: { slug: string; name: string; verified?: boolean; website?: string; contact_email?: string };
  dashboards?: { name: string; label: string }[];
  requires?: Record<string, boolean | string>;
  connections?: { name: string; type: string; required?: boolean; label?: string; description?: string }[];
  databases?: {
    postgres?: { tables: string[] };
  };
  navigation?: { label: string; href: string; icon?: string }[];
  datasets?: { name: string; label?: string; grain?: string; db?: string }[];
  settings?: { key: string; label: string; type: string; default?: unknown; description?: string }[];
  alerts?: { name: string; label?: string; description?: string }[];
  depends_on?: { plugin: string; display_name?: string; reason?: string }[];
  screenshots?: string[];
}

// ── Install button ─────────────────────────────────────────────────────────────

function InstallButton({ pluginId, onInstalled }: { pluginId: string; onInstalled: () => void }) {
  const [state, setState] = useState<"idle" | "installing" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function install() {
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

  if (state === "done") {
    return (
      <span className="inline-flex items-center gap-2 h-10 px-5 rounded-md bg-green-500/10 text-green-400 text-sm">
        <CheckCircle2 className="w-4 h-4" /> Installed
      </span>
    );
  }

  return (
    <button
      onClick={install}
      disabled={state === "installing"}
      className="inline-flex items-center gap-2 h-10 px-5 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
      title={state === "error" ? errorMsg : undefined}
    >
      <Download className="w-4 h-4" />
      {state === "installing" ? "Installing…" : state === "error" ? "Failed — retry" : "Install plugin"}
    </button>
  );
}

// ── Section heading ────────────────────────────────────────────────────────────

function SectionHeading({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider flex items-center gap-2 mb-3">
      <Icon className="w-3.5 h-3.5" />
      {label}
    </h3>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PluginDetailPage() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  const [plugin, setPlugin] = useState<PluginDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [uninstalling, setUninstalling] = useState(false);

  function load() {
    setLoading(true);
    // Try catalog first (has installed flag + full metadata)
    apiFetch("/api/plugins/catalog")
      .then(r => r.json())
      .then(data => {
        const found = (data.plugins ?? []).find((p: PluginDetail) => p.id === pluginId);
        if (found) {
          setPlugin(found);
        } else {
          // Fallback: installed plugin not in catalog
          return apiFetch(`/api/plugins/${pluginId}`)
            .then(r => r.json())
            .then(d => setPlugin({ ...d, installed: true }));
        }
      })
      .catch(() => setPlugin(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [pluginId]);

  if (loading) {
    return (
      <div className="max-w-[1000px] space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-secondary rounded" />
        <div className="bg-card rounded-lg border border-border p-8 space-y-4">
          <div className="h-12 w-12 rounded-xl bg-secondary" />
          <div className="h-6 w-64 bg-secondary rounded" />
          <div className="h-4 w-full bg-secondary rounded" />
          <div className="h-4 w-3/4 bg-secondary rounded" />
        </div>
      </div>
    );
  }

  if (!plugin) {
    return (
      <div className="max-w-[1000px] space-y-4">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <Package className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="font-display text-lg text-foreground mb-2">Plugin not found</h2>
          <p className="text-sm text-muted-foreground">"{pluginId}" is not in the catalog.</p>
          <Link to="/marketplace" className="mt-6 inline-flex items-center gap-1.5 text-sm text-primary hover:text-primary/80">
            Browse Marketplace
          </Link>
        </div>
      </div>
    );
  }

  // Installed plugins go to the live plugin page, not the catalog view
  if (plugin.installed) {
    return <Navigate to={`/plugin/${plugin.id}/overview`} replace />;
  }

  const isPremium = plugin.visibility === "public_premium" || plugin.visibility === "fully_private";
  const pgTables = plugin.databases?.postgres?.tables ?? [];

  return (
    <div className="max-w-[1000px] space-y-6">

      {/* Back nav */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* Hero card */}
      <div className="bg-card rounded-lg border border-border p-8">
        <div className="flex items-start gap-5">
          {/* Icon */}
          <div className={cn(
            "h-16 w-16 rounded-xl flex items-center justify-center shrink-0",
            isPremium ? "bg-orange-500/10 text-orange-400"
              : plugin.installed ? "bg-green-500/10 text-green-400"
              : "bg-primary/10 text-primary"
          )}>
            <Package className="w-8 h-8" />
          </div>

          {/* Title block */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="font-display text-2xl text-foreground">{plugin.display_name}</h1>
              {plugin.publisher?.verified && (
                <span className="flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3" /> Verified
                </span>
              )}
              {isPremium && (
                <span className="flex items-center gap-1 text-xs text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded-full">
                  <Lock className="w-3 h-3" /> Premium
                </span>
              )}
              {plugin.installed && (
                <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3" /> Installed
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              <span className="font-mono-deck">v{plugin.version}</span>
              {plugin.publisher?.name && <> · by {plugin.publisher.name}</>}
              {plugin.license && <> · {plugin.license}</>}
              {plugin.category && <> · <span className="capitalize">{plugin.category}</span></>}
            </p>

            {/* Description */}
            <p className="text-sm text-muted-foreground font-body mt-3 leading-relaxed">
              {plugin.description || "No description provided."}
            </p>

            {/* Tags */}
            {plugin.tags && plugin.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {plugin.tags.map(tag => (
                  <span key={tag} className="text-[10px] font-mono-deck px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* CTA block */}
          <div className="shrink-0 flex flex-col items-end gap-2">
            {plugin.installed ? (
              <>
                <Link
                  to={`/plugin/${plugin.id}/dashboards/${plugin.dashboards?.[0]?.name || "overview"}`}
                  className="inline-flex items-center gap-2 h-10 px-5 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors"
                >
                  Open <ArrowUpRight className="w-4 h-4" />
                </Link>
                <button
                  onClick={() => setUninstalling(true)}
                  className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Uninstall
                </button>
              </>
            ) : isPremium ? (
              <button disabled className="inline-flex items-center gap-2 h-10 px-5 rounded-md bg-orange-500/10 text-orange-400/60 text-sm cursor-not-allowed">
                <Lock className="w-4 h-4" /> Premium only
              </button>
            ) : (
              <InstallButton pluginId={plugin.id} onInstalled={load} />
            )}
          </div>
        </div>
      </div>

      {/* Long description */}
      {plugin.long_description && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Package} label="About this plugin" />
          <p className="text-sm text-muted-foreground font-body leading-relaxed whitespace-pre-line">
            {plugin.long_description}
          </p>
        </div>
      )}

      {/* Details grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Requirements */}
        {plugin.requires && Object.keys(plugin.requires).length > 0 && (
          <div className="bg-card rounded-lg border border-border p-6">
            <SectionHeading icon={ShieldCheck} label="Requirements" />
            <div className="space-y-2">
              {Object.entries(plugin.requires).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="font-mono-deck text-foreground capitalize">{key}</span>
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full font-mono-deck",
                    val === true ? "bg-green-500/10 text-green-400" : "bg-secondary text-muted-foreground"
                  )}>
                    {String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* External connections — hidden for utility plugins (config is on Connections page) */}
        {plugin.type !== "utility" && plugin.connections && plugin.connections.length > 0 && (
          <div className="bg-card rounded-lg border border-border p-6">
            <SectionHeading icon={Plug} label="External connections" />
            <div className="space-y-3">
              {plugin.connections.map(c => (
                <div key={c.name} className="space-y-0.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{c.label || c.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono-deck text-xs text-muted-foreground">{c.type}</span>
                      {c.required && <span className="text-xs text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded">required</span>}
                    </div>
                  </div>
                  {c.description && <p className="text-xs text-muted-foreground">{c.description}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data tables */}
        {pgTables.length > 0 && (
          <div className="bg-card rounded-lg border border-border p-6">
            <SectionHeading icon={Database} label="Data tables" />
            <div className="space-y-1.5">
              {pgTables.map(t => (
                <div key={t} className="flex items-center justify-between text-sm">
                  <span className="font-mono-deck text-foreground">{t}</span>
                  <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded">postgres</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dashboards */}
        {plugin.dashboards && plugin.dashboards.length > 0 && (
          <div className="bg-card rounded-lg border border-border p-6">
            <SectionHeading icon={BarChart3} label="Dashboards" />
            <div className="space-y-1.5">
              {plugin.dashboards.map(d => (
                <div key={d.name} className="text-sm text-foreground">
                  {d.label || d.name}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dependencies */}
        {plugin.depends_on && plugin.depends_on.length > 0 && (
          <div className="bg-card rounded-lg border border-border border-orange-500/20 bg-orange-500/5 p-6">
            <SectionHeading icon={GitBranch} label="Depends on" />
            <div className="space-y-2">
              {plugin.depends_on.map(dep => (
                <div key={dep.plugin} className="text-sm">
                  <span className="text-foreground font-display">{dep.display_name || dep.plugin}</span>
                  {dep.reason && <p className="text-xs text-muted-foreground mt-0.5">{dep.reason}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Publisher */}
        {plugin.publisher && (
          <div className="bg-card rounded-lg border border-border p-6">
            <SectionHeading icon={CheckCircle2} label="Publisher" />
            <div className="space-y-1.5 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-foreground font-display">{plugin.publisher.name}</span>
                {plugin.publisher.verified && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />}
              </div>
              {plugin.publisher.website && (
                <a href={plugin.publisher.website} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1">
                  <Globe className="w-3 h-3" /> {plugin.publisher.website}
                </a>
              )}
              {plugin.publisher.contact_email && (
                <p className="text-xs text-muted-foreground">{plugin.publisher.contact_email}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Navigation entries */}
      {plugin.navigation && plugin.navigation.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Navigation} label="Navigation" />
          <div className="space-y-1.5">
            {plugin.navigation.map((n, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-foreground">{n.label}</span>
                <span className="font-mono-deck text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded">{n.href}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Datasets */}
      {plugin.datasets && plugin.datasets.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Layout} label="Datasets" />
          <div className="space-y-1.5">
            {plugin.datasets.map((ds: any) => (
              <div key={ds.name} className="flex items-center justify-between text-sm">
                <span className="font-mono-deck text-foreground">{ds.label || ds.name}</span>
                <div className="flex items-center gap-1.5">
                  {ds.grain && <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded font-mono-deck">{ds.grain}</span>}
                  {ds.db && <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded font-mono-deck">{ds.db}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Settings */}
      {plugin.settings && plugin.settings.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Settings} label="Configurable settings" />
          <div className="space-y-2">
            {plugin.settings.map((s: any) => (
              <div key={s.key} className="flex items-start justify-between gap-4 text-sm">
                <div>
                  <span className="text-foreground">{s.label}</span>
                  {s.description && <p className="text-xs text-muted-foreground mt-0.5">{s.description}</p>}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded font-mono-deck">{s.type}</span>
                  {s.default != null && <span className="text-xs text-muted-foreground font-mono-deck">default: {String(s.default)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alert definitions */}
      {plugin.alerts && plugin.alerts.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Bell} label="Alert definitions" />
          <div className="space-y-1.5">
            {plugin.alerts.map((a: any) => (
              <div key={a.name} className="text-sm">
                <span className="text-foreground">{a.label || a.name}</span>
                {a.description && <p className="text-xs text-muted-foreground mt-0.5">{a.description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Links */}
      {(plugin.homepage || plugin.repository || plugin.changelog_url || plugin.support_url) && (
        <div className="bg-card rounded-lg border border-border p-6">
          <SectionHeading icon={Globe} label="Links" />
          <div className="flex flex-wrap gap-3">
            {plugin.homepage && (
              <a href={plugin.homepage} target="_blank" rel="noopener noreferrer"
                className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
                <Globe className="w-3.5 h-3.5" /> Homepage <ExternalLink className="w-3 h-3 text-muted-foreground" />
              </a>
            )}
            {plugin.repository && (
              <a href={plugin.repository} target="_blank" rel="noopener noreferrer"
                className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
                <GitBranch className="w-3.5 h-3.5" /> Repository <ExternalLink className="w-3 h-3 text-muted-foreground" />
              </a>
            )}
            {plugin.changelog_url && (
              <a href={plugin.changelog_url} target="_blank" rel="noopener noreferrer"
                className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
                Changelog <ExternalLink className="w-3 h-3 text-muted-foreground" />
              </a>
            )}
            {plugin.support_url && (
              <a href={plugin.support_url} target="_blank" rel="noopener noreferrer"
                className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
                Support <ExternalLink className="w-3 h-3 text-muted-foreground" />
              </a>
            )}
          </div>
        </div>
      )}

      {/* Uninstall modal */}
      {uninstalling && (
        <UninstallPluginModal
          pluginId={plugin.id}
          pluginName={plugin.display_name}
          onClose={() => setUninstalling(false)}
          onComplete={() => {
            setUninstalling(false);
            window.dispatchEvent(new CustomEvent("nousviz:plugins-changed"));
            navigate("/plugins");
          }}
        />
      )}
    </div>
  );
}
