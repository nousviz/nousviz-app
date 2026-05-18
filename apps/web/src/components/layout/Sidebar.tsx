import { apiFetch } from "@/lib/api";
import React, { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import {
  LayoutDashboard,
  Store,
  Plug,
  Database,
  Bell,
  Settings,
  ChevronDown,
  ChevronRight,
  Activity,
  Clock,
  MessageSquareText,
  Puzzle,
  Search,
  Users,
  Link2,
  Gift,
  BarChart2,
  Globe,
  Shield,
  ShieldAlert,
  Zap,
  ChevronLeft,
  BookOpen,
  FileText,
  Share2,
  Terminal,
  Download,
  Layers,
  Code,
  HardDrive,
  type LucideProps,
} from "lucide-react";

// ── Icon resolution (P21) ─────────────────────────────────────────────
// Plugin manifests reference icon names as strings. Explicit allowlist only —
// no dynamic import (bundle size + no tree-shaking).

type IconComponent = React.ComponentType<LucideProps>;

const ICON_MAP: Record<string, IconComponent> = {
  LayoutDashboard,
  Activity,
  BarChart2,
  Database,
  FileText,
  Gift,
  Globe,
  Link2,
  Plug,
  Puzzle,
  Search,
  Settings,
  ShieldAlert,
  Users,
  Zap,
};

function resolveIcon(name?: string): IconComponent {
  return (name && ICON_MAP[name]) ? ICON_MAP[name] : Puzzle;
}
import { cn } from "@/lib/utils";
import SidebarLogo from "./SidebarLogo";

// ── Nav primitives ───────────────────────────────────────────────────

function NavItem({
  to,
  icon,
  label,
  badge,
  end,
  hint,
  notMatching,
  onPrefetch,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  end?: boolean;
  hint?: string;  // B170 (v0.9.5.2): optional richer browser tooltip
  // B252 (v0.9.10.0.2): paths that should NOT activate this item even
  // though they technically nest under `to`. Used for /docs (active for
  // /docs and /docs/<slug>, but NOT /docs/api which is a sibling item).
  notMatching?: string[];
  // v0.10.0.7 (Phase 14): called on first hover so TanStack Query can
  // prefetch the destination's data. By the time the user clicks, the
  // page renders instantly from cache.
  onPrefetch?: () => void;
}) {
  const location = useLocation();
  // If notMatching is provided, override NavLink's default isActive.
  // Otherwise let NavLink decide (using `end` if set).
  const overrideActive = notMatching && notMatching.length > 0
    ? (() => {
        const path = location.pathname;
        // Standard prefix match against `to` (with `end` honored)
        const baseMatch = end
          ? path === to
          : path === to || path.startsWith(to + "/");
        if (!baseMatch) return false;
        // But suppress if any notMatching path is the current pathname
        // or a prefix-with-trailing-slash.
        for (const exclude of notMatching) {
          if (path === exclude || path.startsWith(exclude + "/")) return false;
        }
        return true;
      })()
    : null;

  // v0.10.0.7: fire prefetch at most once per nav item lifetime — repeated
  // hovers are wasteful and TanStack Query's prefetchQuery is a no-op for
  // fresh data, but skipping the fn call keeps things clean.
  const prefetchedRef = React.useRef(false);
  const handleMouseEnter = () => {
    if (onPrefetch && !prefetchedRef.current) {
      prefetchedRef.current = true;
      onPrefetch();
    }
  };

  return (
    <NavLink
      to={to}
      end={end}
      title={hint ?? label}
      onMouseEnter={onPrefetch ? handleMouseEnter : undefined}
      onFocus={onPrefetch ? handleMouseEnter : undefined}
      className={({ isActive }) => {
        const active = overrideActive !== null ? overrideActive : isActive;
        return cn(
          "flex items-center gap-3 py-2 rounded-md text-sm transition-colors overflow-hidden",
          "px-3",
          active
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.5]"
        );
      }}
    >
      <span className="w-4 h-4 shrink-0 ml-0">{icon}</span>
      <span className="flex-1 font-body truncate sidebar-label">{label}</span>
      {badge && (
        <span className="text-xs font-mono-deck px-1.5 py-0.5 rounded bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] sidebar-label">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

function NavSection({ label, children, defaultOpen = true }: { label: string; children?: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 pt-5 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors sidebar-label"
      >
        {label}
        <ChevronDown className={cn("w-3 h-3 transition-transform sidebar-label", !open && "-rotate-90")} />
      </button>
      {open && children}
    </div>
  );
}

function SubNavItem({ to, label }: { to: string; label: string }) {
  const location = useLocation();
  // Match if current path starts with this link's path
  const isActive = location.pathname === to || location.pathname.startsWith(to + "/");
  return (
    <NavLink
      to={to}
      className={() =>
        cn(
          "flex items-center gap-2 pl-10 pr-3 py-1.5 rounded-md text-[13px] transition-colors",
          isActive
            ? "text-sidebar-accent-foreground bg-sidebar-accent/50"
            : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.3]"
        )
      }
    >
      {label}
    </NavLink>
  );
}

// ── Plugin navigation types ───────────────────────────────────────────

function DashboardSubGroup({ entries }: { entries: { label: string; path: string }[] }) {
  const location = useLocation();
  const isActive = entries.some(e => location.pathname.startsWith(e.path));
  const [open, setOpen] = useState(isActive);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center gap-2 pl-10 pr-3 py-1.5 rounded-md text-[13px] transition-colors",
          isActive
            ? "text-sidebar-accent-foreground"
            : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.3]"
        )}
      >
        <span className="flex-1 text-left">Dashboards</span>
        {open ? <ChevronDown className="w-3 h-3 opacity-40" /> : <ChevronRight className="w-3 h-3 opacity-40" />}
      </button>
      {open && (
        <div className="space-y-0.5">
          {entries.map((entry) => (
            <NavLink
              key={entry.path}
              to={entry.path}
              className={() => {
                const active = location.pathname === entry.path || location.pathname.startsWith(entry.path + "/");
                return cn(
                  "flex items-center gap-2 pl-14 pr-3 py-1 rounded-md text-[12px] transition-colors",
                  active
                    ? "text-sidebar-accent-foreground bg-sidebar-accent/50"
                    : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.3]"
                );
              }}
            >
              {entry.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

interface NavEntry {
  label: string;
  path: string;
  icon?: string;
}

interface InstalledPlugin {
  id: string;
  name: string;
  icon?: string;
  navigation: NavEntry[];
  isUtility?: boolean;
  hasModules?: boolean;
}

// ── Collapsible plugin navigation group ──────────────────────────────

function PluginGroup({ plugin, collapsed }: { plugin: InstalledPlugin; collapsed?: boolean }) {
  const location = useLocation();
  const queryClient = useQueryClient();
  const isInPlugin = plugin.navigation.some(n => location.pathname.startsWith(n.path));
  const [open, setOpen] = useState(isInPlugin);
  const GroupIcon = resolveIcon(plugin.icon);

  // v0.10.0.7.1 (Phase 14 / P14.1): prefetch this plugin's manifest on
  // first sidebar hover. PluginPage uses the same query key, so by the
  // time the operator clicks the page renders instantly from cache.
  const prefetchedRef = React.useRef(false);
  const prefetchPlugin = () => {
    if (prefetchedRef.current) return;
    prefetchedRef.current = true;
    queryClient.prefetchQuery({
      queryKey: ["plugin", plugin.id, "manifest"],
      queryFn: () => apiFetch(`/api/plugins/${plugin.id}`).then(r => r.json()),
    });
  };

  if (plugin.navigation.length === 1 || collapsed) {
    const entry = plugin.navigation[0];
    const EntryIcon = resolveIcon(entry.icon ?? plugin.icon);
    return (
      <NavLink
        to={entry.path}
        title={plugin.name}
        onMouseEnter={prefetchPlugin}
        onFocus={prefetchPlugin}
        className={({ isActive }) =>
          cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors overflow-hidden",
            isActive
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.5]"
          )
        }
      >
        <span className="w-4 h-4 shrink-0"><EntryIcon className="w-4 h-4" /></span>
        <span className="flex-1 font-body truncate sidebar-label">{plugin.name}</span>
      </NavLink>
    );
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        onMouseEnter={prefetchPlugin}
        onFocus={prefetchPlugin}
        className={cn(
          "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
          isInPlugin
            ? "text-sidebar-accent-foreground"
            : "text-[hsl(var(--muted-foreground))] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.5]"
        )}
      >
        <span className="w-4 h-4 shrink-0"><GroupIcon className="w-4 h-4" /></span>
        <span className="flex-1 font-body text-left sidebar-label">{plugin.name}</span>
        {open ? (
          <ChevronDown className="w-3 h-3 opacity-40 sidebar-label" />
        ) : (
          <ChevronRight className="w-3 h-3 opacity-40 sidebar-label" />
        )}
      </button>
      {open && (
        <div className="mt-0.5 space-y-0.5">
          {/* First nav entry — "About" for utility plugins, first dashboard
              for data plugins (v0.8.3 P111 rename from "Overview"). */}
          {plugin.navigation.length > 0 && (
            <SubNavItem to={plugin.navigation[0].path} label={plugin.navigation[0].label} />
          )}
          {/* Modules — top level if plugin has modules */}
          {plugin.hasModules && (
            <SubNavItem to={`/plugin/${plugin.id}/modules`} label="Modules" />
          )}
          {/* Dashboards — remaining nav entries grouped */}
          {plugin.navigation.length > 1 && (
            <DashboardSubGroup entries={plugin.navigation.slice(1)} />
          )}
          <SubNavItem to={`/plugin/${plugin.id}/settings`} label="Settings" />
        </div>
      )}
    </div>
  );
}

// ── Default navigation when plugin.yaml has no navigation field ───────

function _defaultNav(slug: string, name: string): NavEntry[] {
  return [{ label: name, path: `/plugin/${slug}`, icon: "Puzzle" }];
}

// ── Sidebar ──────────────────────────────────────────────────────────

export default function Sidebar({ open, collapsed = false, onClose, onToggleCollapse }: { open: boolean; collapsed?: boolean; onClose: () => void; onToggleCollapse?: () => void }) {
  const location = useLocation();
  const { hasPermission } = useCurrentUser();
  const queryClient = useQueryClient();

  // v0.10.0.15: plugin + health fetches go through TanStack Query so they
  // (a) share cache with PluginsPage / DashboardPage and (b) DO NOT refetch
  // on every route change. The previous useEffect([location.pathname])
  // re-issued both fetches on every navigation, which made the sidebar's
  // "Your Plugins" section flash empty and lit up the "loading elements"
  // staged-load the operator was seeing.
  const pluginsQueryKey = ["plugins", "list"] as const;
  const healthQueryKey = ["health", "stats"] as const;

  const { data: pluginsRaw } = useApiQuery<{ plugins?: any[] }>(
    pluginsQueryKey,
    "/api/plugins",
    { staleTime: 60_000 },
  );

  const { data: healthRaw } = useApiQuery<{ stats?: { active_shares?: number } }>(
    healthQueryKey,
    "/api/health",
    { staleTime: 60_000 },
  );

  const plugins: InstalledPlugin[] = (pluginsRaw?.plugins ?? []).map((p: any) => {
    const slug = p.id || p.name;
    const name = p.display_name || p.name || slug;
    const isUtility = p.type === "utility";
    const nav: NavEntry[] = Array.isArray(p.navigation) && p.navigation.length > 0
      ? p.navigation.map((e: any) => ({ ...e, path: e.path ?? e.href }))
      : isUtility
        ? [{ label: name, path: `/plugin/${slug}/overview`, icon: "Puzzle" }]
        : _defaultNav(slug, name);
    const hasModules = Array.isArray(p.modules) && p.modules.length > 0;
    return { id: slug, name, icon: p.icon, navigation: nav, isUtility, hasModules };
  });

  const activeShares = healthRaw?.stats?.active_shares ?? 0;

  // Hover prefetch: PluginsPage uses the same cache key, so by the time the
  // operator clicks "Installed" their list has already loaded.
  const prefetchPluginsList = () => {
    queryClient.prefetchQuery({
      queryKey: pluginsQueryKey,
      queryFn: () => apiFetch("/api/plugins").then(r => r.json()),
    });
  };

  // Auto-close mobile drawer on navigation.
  useEffect(() => { onClose(); }, [location.pathname]);

  // Invalidate the plugins cache when install/uninstall fires the event.
  // Replaces the per-nav refetch — same end behaviour, no per-nav flash.
  useEffect(() => {
    const handler = () => {
      queryClient.invalidateQueries({ queryKey: pluginsQueryKey });
    };
    window.addEventListener("nousviz:plugins-changed", handler);
    return () => window.removeEventListener("nousviz:plugins-changed", handler);
  }, [queryClient]);

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
    <aside className={cn(
      "fixed left-0 top-0 bottom-0 bg-sidebar border-r border-sidebar-border flex flex-col z-40 transition-all duration-200",
      collapsed ? "md:w-16" : "w-[var(--sidebar-w)]",
      "md:translate-x-0",
      open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
    )}>
      {/* Brand */}
      <div className={cn("h-[var(--topbar-h)] flex items-center border-b border-sidebar-border shrink-0 overflow-hidden", collapsed ? "px-2 justify-center" : "px-[18px]")}>
        <NavLink to="/" end>
          <SidebarLogo collapsed={collapsed} />
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className={cn("flex-1 overflow-y-auto scrollbar-hide py-2 sidebar-nav relative", collapsed ? "px-1 collapsed" : "px-2")}>
        {/* Dashboards */}
        <NavSection label="Dashboards">
          <NavItem to="/" icon={<LayoutDashboard className="w-4 h-4" />} label="Home" end />
          <NavItem to="/dashboards" icon={<Layers className="w-4 h-4" />} label="Dashboards" />
          <NavItem to="/alerts" icon={<Bell className="w-4 h-4" />} label="Alerts" />
          <NavItem to="/annotations" icon={<MessageSquareText className="w-4 h-4" />} label="Annotations" />
        </NavSection>

        {/* Plugins — installed user-facing instances (excludes utilities) */}
        {plugins.filter(p => !p.isUtility).length > 0 && (
          <NavSection label="Your Plugins">
            {plugins.filter(p => !p.isUtility).map((plugin) => (
              <PluginGroup key={plugin.id} plugin={plugin} collapsed={collapsed} />
            ))}
          </NavSection>
        )}

        {/* Plugins — discovery & management */}
        <NavSection label="Plugins">
          <NavItem to="/marketplace" icon={<Store className="w-4 h-4" />} label="Marketplace" />
          <NavItem to="/install-plugin" icon={<Download className="w-4 h-4" />} label="Install Plugin" />
          <NavItem to="/plugins" icon={<Puzzle className="w-4 h-4" />} label="Installed" onPrefetch={prefetchPluginsList} />
        </NavSection>

        {/* Utilities — installed platform services, separate from user-facing plugins */}
        {plugins.filter(p => p.isUtility).length > 0 && (
          <NavSection label="Utilities">
            {plugins.filter(p => p.isUtility).map((plugin) => (
              <PluginGroup key={plugin.id} plugin={plugin} collapsed={collapsed} />
            ))}
          </NavSection>
        )}

        {/* Data — v1.0 unified explorer. Replaces the separate Connections
            + Datasets entries; both pages still exist (for credential
            management and per-plugin browsing), but the primary entry point
            is /data which lists every source side-by-side. */}
        <NavSection label="Data">
          <NavItem
            to="/data"
            icon={<Database className="w-4 h-4" />}
            label="Explorer"
            hint="Every data source this instance can read — databases and plugins, browsable in one place."
          />
          <NavItem
            to="/connections"
            icon={<Plug className="w-4 h-4" />}
            label="Connections"
            hint="Manage database credentials and health. Browsing happens in Explorer."
          />
          <NavItem to="/analytics" icon={<Activity className="w-4 h-4" />} label="Usage" />
          <NavItem to="/shares" icon={<Share2 className="w-4 h-4" />} label="Shared Links" badge={activeShares > 0 ? String(activeShares) : undefined} />
        </NavSection>

        {/* System — operator observability: health, resources, jobs, logs, permissions, users.
            Order MUST match SystemTabBar.SYSTEM_TABS so the sidebar and tab strip never disagree.
            B271 v0.9.11.13.1: added Resources between Health and Jobs. */}
        <NavSection label="System">
          <NavItem to="/system/health" icon={<Activity className="w-4 h-4" />} label="Health" />
          {hasPermission("system.audit") && (
            <NavItem to="/system/resources" icon={<HardDrive className="w-4 h-4" />} label="Resources" />
          )}
          <NavItem to="/system/jobs" icon={<Clock className="w-4 h-4" />} label="Jobs" />
          {/* B230 (v0.9.8.3): role-aware nav. Logs and Permissions both
              require admin+ permissions on the backend; hide from non-admins
              rather than showing items that 403 on click. */}
          {hasPermission("system.logs") && (
            <NavItem to="/system/logs" icon={<FileText className="w-4 h-4" />} label="Logs" />
          )}
          {hasPermission("system.audit") && (
            <NavItem to="/system/permissions" icon={<Shield className="w-4 h-4" />} label="Permissions" />
          )}
          {/* B252 (v0.9.10.0.2): user management — moved from Settings →
              Users to System → Users. Gated on users.manage (admin+). */}
          {hasPermission("users.manage") && (
            <NavItem to="/system/users" icon={<Users className="w-4 h-4" />} label="Users" />
          )}
        </NavSection>

        <NavSection label="Resources">
          {/* B252 (v0.9.10.0.2): /docs is active for /docs and /docs/<slug>
              but NOT for /docs/api (which is its own sibling nav item).
              Without notMatching, both items lit up on /docs/api. */}
          <NavItem
            to="/docs"
            icon={<BookOpen className="w-4 h-4" />}
            label="Docs"
            notMatching={["/docs/api"]}
          />
          <NavItem to="/docs/api" icon={<Code className="w-4 h-4" />} label="API Docs" />
          {/* B230: Admin CLI requires superadmin (admin.cli permission) */}
          {hasPermission("admin.cli") && (
            <NavItem to="/admin/cli" icon={<Terminal className="w-4 h-4" />} label="Admin CLI" />
          )}
        </NavSection>
      </nav>

      {/* Scroll fade — hint that nav scrolls */}
      <div className="h-6 bg-gradient-to-t from-sidebar to-transparent shrink-0 -mt-6 pointer-events-none relative z-10" />

      {/* Footer — settings + collapse */}
      <div className={cn("py-2 border-t border-sidebar-border shrink-0 space-y-0.5 bg-sidebar", collapsed ? "px-1" : "px-2")}>
        <NavLink
          to="/settings"
          title="Settings"
          className={({ isActive }) => cn(
            "flex items-center gap-3 py-1.5 rounded-md text-xs transition-colors overflow-hidden",
            collapsed ? "px-2 justify-center" : "px-3",
            isActive
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-[hsl(var(--muted-foreground)/0.6)] hover:text-sidebar-foreground hover:bg-[hsl(var(--sidebar-accent))/0.5]"
          )}
        >
          <Settings className="w-3.5 h-3.5 shrink-0" />
          {!collapsed && <span className="flex-1 font-body">Settings</span>}
        </NavLink>
        <button
          onClick={onToggleCollapse}
          className={cn("hidden md:flex w-full items-center gap-3 py-1.5 rounded-md text-xs text-[hsl(var(--muted-foreground)/0.4)] hover:text-muted-foreground transition-colors", collapsed ? "px-2 justify-center" : "px-3")}
          title={collapsed ? "Expand sidebar" : "Minimize sidebar"}
        >
          <ChevronLeft className={cn("w-3.5 h-3.5 transition-transform", collapsed && "rotate-180")} />
          {!collapsed && <span className="flex-1 font-body text-left">Minimize</span>}
        </button>
      </div>
    </aside>
    </>
  );
}
