import { useState, useEffect, useRef } from "react";
import { useLocation, Link, NavLink } from "react-router-dom";
import SidebarLogo from "./SidebarLogo";
import { Search, Github, MessageSquare, RefreshCw, Menu, Shield, X, CheckCircle2, AlertTriangle, XCircle, LogOut, User } from "lucide-react";
import SslSetupModal from "@/components/SslSetupModal";
import SetupWizard from "@/components/SetupWizard";
import CheckAction from "@/components/health/CheckAction";
import { evaluateChecks, summarize, type HealthData, type ConfigData } from "@/lib/health-checks";
import { useCompactNumbers } from "@/hooks/useCompactNumbers";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import NotesPanel from "@/widgets/NotesPanel";
import ShareButton from "@/widgets/ShareButton";
import CommandPalette from "@/widgets/CommandPalette";

const API_BASE = "/api";
const TOKEN_KEY = "nousviz_auth_token";

const PAGE_TITLES: Record<string, string> = {
  "/": "Home",
  "/marketplace": "Plugin Marketplace",
  "/connections": "Connections",
  "/datasets": "Datasets",
  "/alerts": "Alerts",
  "/annotations": "Annotations",
  "/reports": "Reports",
  "/plugins": "Installed Plugins",
  "/settings": "Settings",
  "/analytics": "Usage Analytics",
  "/shares": "Shared Links",
  "/system": "System Status",
  "/health-overview": "System Status",
};

export default function Topbar({ sidebarCollapsed, onMenuClick }: { sidebarCollapsed: boolean; onMenuClick: () => void }) {
  const location = useLocation();
  useCompactNumbers(); // register context — values consumed by child components
  const [notesOpen, setNotesOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const [noteCount, setNoteCount] = useState(0);
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [configData, setConfigData] = useState<ConfigData | null>(null);
  const [healthOpen, setHealthOpen] = useState(false);
  const [healthChecking, setHealthChecking] = useState(false);
  const healthRef = useRef<HTMLDivElement>(null);
  const [healthWarnings, setHealthWarnings] = useState<{ id: string; label: string; detail: string; onClick?: string; href?: string }[]>([]);
  const [showBanner, setShowBanner] = useState(false);
  const [showSslModal, setShowSslModal] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  // B236 (v0.9.10.0): Topbar shows the EFFECTIVE user — when impersonating
  // Alice, the topbar should show Alice's avatar and name, matching the
  // session's effective identity. The actor's identity is surfaced via the
  // ImpersonationBanner mounted in AppLayout.
  const { effective: currentUser } = useCurrentUser();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Sync banner visibility to a CSS variable so AppLayout can adjust top padding
  const bannerVisible = showBanner && healthWarnings.length > 0;
  useEffect(() => {
    document.documentElement.style.setProperty("--banner-h", bannerVisible ? "30px" : "0px");
  }, [bannerVisible]);

  // Close health dropdown on outside click
  useEffect(() => {
    if (!healthOpen) return;
    function handleClick(e: MouseEvent) {
      if (healthRef.current && !healthRef.current.contains(e.target as Node)) {
        setHealthOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [healthOpen]);
  const path = location.pathname;
  const title =
    PAGE_TITLES[path] ||
    (path.startsWith("/plugin/")
      ? path.split("/")[2]?.charAt(0).toUpperCase() + path.split("/")[2]?.slice(1) || "Plugin"
      : "NousViz");

  // Cmd+K to open search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Health check polling — every 30 seconds
  useEffect(() => {
    const checkHealth = async () => {
      setHealthChecking(true);
      try {
        const bust = `?_=${Date.now()}`;
        const [healthRes, configRes] = await Promise.all([
          fetch(`${API_BASE}/health${bust}`, { signal: AbortSignal.timeout(5000), cache: "no-store" }),
          fetch(`${API_BASE}/health/config${bust}`, { signal: AbortSignal.timeout(5000), cache: "no-store" }),
        ]);
        let hData: HealthData | null = null;
        let cData: ConfigData | null = null;
        if (healthRes.ok) { hData = await healthRes.json(); setHealthData(hData); }
        if (configRes.ok) { cData = await configRes.json(); setConfigData(cData); }

        // Compute warnings for banner
        const checks = evaluateChecks(hData, cData);
        const warns = checks.filter(c => c.status === "warn" || c.status === "fail");
        setHealthWarnings(warns.map(c => ({ id: c.id, label: c.label, detail: c.detail, onClick: c.action?.onClick, href: c.action?.href })));
        const dismissed = sessionStorage.getItem("nousviz:banner_dismissed") === "true";
        setShowBanner(warns.length > 0 && !dismissed);
      } catch {
        setHealthData(null);
      } finally {
        setHealthChecking(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
    return () => clearInterval(interval);
  }, []);

  // B230 (v0.9.8.3): currentUser comes from useCurrentUser() context
  // (provided by CurrentUserProvider in App.tsx). No per-component
  // /api/auth/me fetch — single source of truth.

  // Close user menu on outside click
  useEffect(() => {
    if (!userMenuOpen) return;
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setUserMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [userMenuOpen]);

  // Close user menu on navigation
  useEffect(() => { setUserMenuOpen(false); }, [path]);

  function handleLogout() {
    apiFetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = "/";
  }

  // Fetch note count for current page
  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE}/notes?page_path=${encodeURIComponent(path)}`);
        const data = await res.json();
        setNoteCount(data.count);
      } catch {
        setNoteCount(0);
      }
    })();
  }, [path, notesOpen]);

  return (
    <>
      {showSslModal && (
        <SslSetupModal
          onClose={() => setShowSslModal(false)}
          onComplete={() => { setShowBanner(false); }}
        />
      )}
      {showWizard && (
        <SetupWizard onClose={() => setShowWizard(false)} />
      )}
      <div className={cn(
        "fixed top-0 right-0 left-0 z-30 flex flex-col transition-all duration-200",
        sidebarCollapsed ? "md:left-16" : "md:left-[var(--sidebar-w)]"
      )}>
      {/* Health warning banner — solid bg so scrolled content doesn't bleed through */}
      {showBanner && healthWarnings.length > 0 && (
        <div className="bg-background border-b border-yellow-500/30 px-4 py-1.5 flex items-center justify-center gap-3 relative before:absolute before:inset-0 before:bg-yellow-500/10 before:pointer-events-none">
          <Shield className="w-3 h-3 text-yellow-400 shrink-0" />
          <span className="text-[11px] text-yellow-400">
            {healthWarnings.length === 1
              ? `${healthWarnings[0].label}: ${healthWarnings[0].detail}`
              : `${healthWarnings.length} items need attention`}
          </span>
          {healthWarnings.length === 1 && healthWarnings[0].onClick === "ssl-setup" && (
            <button onClick={() => setShowSslModal(true)} className="text-[11px] text-primary hover:underline font-medium">Configure</button>
          )}
          {healthWarnings.length === 1 && healthWarnings[0].onClick === "setup-wizard" && (
            <button onClick={() => setShowWizard(true)} className="text-[11px] text-primary hover:underline font-medium">Fix now</button>
          )}
          {healthWarnings.length === 1 && !healthWarnings[0].onClick && healthWarnings[0].href && (
            <Link to={healthWarnings[0].href} className="text-[11px] text-primary hover:underline font-medium">Configure</Link>
          )}
          {healthWarnings.length > 1 && (
            <button onClick={() => setHealthOpen(true)} className="text-[11px] text-primary hover:underline font-medium">View</button>
          )}
          <button
            onClick={() => { setShowBanner(false); sessionStorage.setItem("nousviz:banner_dismissed", "true"); }}
            className="text-yellow-400/40 hover:text-yellow-400 ml-1"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
      <header className="h-[var(--topbar-h)] bg-background/80 backdrop-blur-xl border-b border-border flex items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-3">
          {/* Hamburger — mobile only */}
          <button
            onClick={onMenuClick}
            className="md:hidden h-9 w-9 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            <Menu className="h-4 w-4" />
          </button>
          {/* Logo — mobile only (sidebar is hidden; show the N lettermark so the brand is visible) */}
          <NavLink to="/" className="md:hidden shrink-0">
            <SidebarLogo collapsed />
          </NavLink>
          {/* Page title — hidden on very small screens where it crowds the topbar */}
          <h1 className="font-display text-lg text-foreground hidden sm:block">{title}</h1>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <button
            onClick={() => setSearchOpen(true)}
            className="h-9 px-3 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-2 text-sm text-muted-foreground transition-colors"
          >
            <Search className="h-4 w-4" />
            <span className="hidden sm:inline">Search</span>
            <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-border bg-background px-1.5 font-mono-deck text-[10px] text-muted-foreground">
              <span className="text-xs">⌘</span>K
            </kbd>
          </button>

          {/* Notes — hidden on mobile */}
          <button
            onClick={() => setNotesOpen(true)}
            className="hidden sm:flex h-9 px-3 rounded-md bg-secondary hover:bg-secondary/80 items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            title="Page notes"
          >
            <MessageSquare className="h-4 w-4" />
            {noteCount > 0 && (
              <span className="text-xs font-mono-deck">{noteCount}</span>
            )}
          </button>

          {/* Share — only renders on shareable dashboard pages */}
          <ShareButton />

          {/* GitHub — hidden on mobile */}
          <a
            href="https://github.com/nousviz/nousviz-app"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex h-9 w-9 rounded-md bg-secondary hover:bg-secondary/80 items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <Github className="h-4 w-4" />
          </a>

          {/* Health indicator */}
          {(() => {
            const checks = evaluateChecks(healthData, configData);
            const { level, label } = summarize(checks);
            const dotColor = level === "loading" ? "bg-muted-foreground animate-pulse" : level === "healthy" ? "bg-green-400" : level === "warning" ? "bg-yellow-400" : "bg-red-400";
            const textColor = level === "loading" ? "text-muted-foreground" : level === "healthy" ? "text-green-400" : level === "warning" ? "text-yellow-400" : "text-red-400";
            const CheckIcon = ({ status }: { status: string }) =>
              status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-green-400 shrink-0" /> :
              status === "warn" ? <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 shrink-0" /> :
              <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />;

            return (
              <div className="relative" ref={healthRef}>
                <button
                  onClick={() => setHealthOpen(!healthOpen)}
                  className={cn("h-9 px-2.5 rounded-md bg-secondary hover:bg-secondary/80 flex items-center gap-2 text-xs transition-colors", textColor)}
                  title="System status"
                >
                  <span className={cn("w-2 h-2 rounded-full", dotColor)} />
                  <span className="hidden lg:inline font-mono-deck">{healthData ? label : "Checking…"}</span>
                </button>

                {healthOpen && (
                  <div className="absolute right-0 top-11 z-50 w-[320px] bg-card border border-border rounded-lg shadow-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="font-display text-sm text-foreground">System Status</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono-deck text-muted-foreground">NousViz v{healthData?.version ?? "—"}</span>
                        <button onClick={() => setHealthOpen(false)} className="text-muted-foreground hover:text-foreground">
                          <RefreshCw className={cn("w-3.5 h-3.5", healthChecking && "animate-spin")} />
                        </button>
                      </div>
                    </div>

                    <div className="space-y-1">
                      {checks.map((check) => (
                        <div key={check.id} className="flex items-start gap-2.5 py-1.5">
                          <div className="pt-0.5 shrink-0"><CheckIcon status={check.status} /></div>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-foreground truncate">{check.label}</div>
                            {check.detail && !check.action && (
                              <div className={cn(
                                "text-[10px] font-mono-deck mt-0.5 break-words",
                                check.status === "pass" ? "text-green-400/80" : check.status === "warn" ? "text-yellow-400/80" : "text-red-400/80"
                              )}>
                                {check.detail}
                              </div>
                            )}
                            {check.detail && check.action && (
                              <div className="text-[10px] text-muted-foreground mt-0.5 break-words">{check.detail}</div>
                            )}
                          </div>
                          {check.action && (
                            <div className="shrink-0">
                              <CheckAction
                                action={check.action}
                                onFire={() => setHealthOpen(false)}
                                onSslSetup={() => setShowSslModal(true)}
                                onSetupWizard={() => setShowWizard(true)}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="border-t border-border pt-2 flex items-center justify-between">
                      <span className="text-[10px] text-muted-foreground">
                        {checks.filter(c => c.status === "pass").length} of {checks.length} checks passing
                      </span>
                      <Link
                        to="/system"
                        onClick={() => setHealthOpen(false)}
                        className="text-[11px] text-primary hover:underline"
                      >
                        Open System Status
                      </Link>
                      <span className="text-muted-foreground/30 mx-1">·</span>
                      <Link
                        to="/settings"
                        onClick={() => setHealthOpen(false)}
                        className="text-[11px] text-primary hover:underline"
                      >
                        Settings
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* User menu */}
          {currentUser && (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(o => !o)}
                className="h-9 w-9 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center transition-colors"
                title={`${currentUser.name || currentUser.email} (${currentUser.role})`}
              >
                {currentUser.avatar_url ? (
                  <img src={currentUser.avatar_url} alt="" className="w-6 h-6 rounded-full object-cover" />
                ) : (
                  <span className="w-6 h-6 rounded-full bg-primary/20 text-primary text-[10px] font-semibold flex items-center justify-center">
                    {(currentUser.name || currentUser.email)[0].toUpperCase()}
                  </span>
                )}
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 top-11 z-50 w-56 bg-card border border-border rounded-lg shadow-xl overflow-hidden">
                  <div className="px-3 py-2.5 border-b border-border">
                    <p className="text-xs text-foreground font-medium truncate">{currentUser.name || currentUser.email}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{currentUser.email}</p>
                    <span className={cn(
                      "inline-block mt-1 px-1.5 py-0.5 rounded-full border text-[9px]",
                      currentUser.role === "superadmin" ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
                      : currentUser.role === "admin" ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                      : currentUser.role === "analyst" ? "bg-green-500/10 text-green-400 border-green-500/30"
                      : "bg-secondary text-muted-foreground border-border"
                    )}>{currentUser.role}</span>
                  </div>
                  <Link
                    to="/settings/profile"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
                  >
                    <User className="w-3.5 h-3.5" />
                    Profile
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-muted-foreground hover:text-red-400 hover:bg-secondary/50 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Log out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>
      </div>

      {/* AI Chat */}
      {/* Notes panel */}
      <NotesPanel open={notesOpen} onClose={() => setNotesOpen(false)} />

      {/* Command palette */}
      <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
