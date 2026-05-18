import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ThemeProvider } from "@/hooks/useTheme";
import { CompactNumbersProvider } from "@/hooks/useCompactNumbers";
import { CurrentUserProvider } from "@/hooks/useCurrentUser";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}
import AuthGate from "./components/layout/AuthGate";
import SetupWizard, { SETUP_KEY } from "./components/SetupWizard";
import AppLayout from "./components/layout/AppLayout";
import EmbedLayout from "./components/layout/EmbedLayout";
import DashboardPage from "./pages/DashboardPage";
import MarketplacePage from "./pages/MarketplacePage";

import ConnectionsPage from "./pages/ConnectionsPage";
import ConnectionDetailPage from "./pages/ConnectionDetailPage";
import ConnectionTableRowsPage from "./pages/ConnectionTableRowsPage";
import DataPage from "./pages/DataPage";
import DatasetsPage from "./pages/DatasetsPage";
import DatasetDetailPage from "./pages/DatasetDetailPage";
import SharesPage from "./pages/SharesPage";
import AlertsPage from "./pages/AlertsPage";
import AnnotationsPage from "./pages/AnnotationsPage";
import PluginsPage from "./pages/PluginsPage";
import SettingsPage from "./pages/SettingsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import HealthOverviewPage from "./pages/HealthOverviewPage";
import PluginPage from "./pages/PluginPage";
import EmbedDashboardPage from "./pages/EmbedDashboardPage";
import EmbedWidgetPage from "./pages/EmbedWidgetPage";
import EmbedPluginPage from "./pages/EmbedPluginPage";
import EmbedMultiPage from "./pages/EmbedMultiPage";
import CanvasLayout from "./components/layout/CanvasLayout";
import CanvasPage from "./pages/CanvasPage";
import BuildAPluginPage from "./pages/BuildAPluginPage";
import PluginDetailPage from "./pages/PluginDetailPage";
import DocsPage from "./pages/DocsPage";
import SharedViewPage from "./pages/SharedViewPage";
import AcceptInvitePage from "./pages/AcceptInvitePage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AdminCliPage from "./pages/AdminCliPage";
import ApiReferencePage from "./pages/ApiReferencePage";
import SystemPermissionsPage from "./pages/SystemPermissionsPage";
import SystemUsersPage from "./pages/SystemUsersPage";
import InstallPluginPage from "./pages/InstallPluginPage";
import DashboardManagerPage from "./pages/DashboardManagerPage";
import DashboardViewPage from "./pages/DashboardViewPage";
import DashboardBuilderPage from "./pages/DashboardBuilderPage";

// Apply saved instance name to document.title on load
const savedName = localStorage.getItem("nousviz:instance_name");
if (savedName) {
  document.title = `${savedName} — Data Intelligence Platform`;
}

export default function App() {
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    // Only show wizard if localStorage hasn't recorded completion
    if (localStorage.getItem(SETUP_KEY)) return;
    // Also skip if the server is already configured (e.g. after localStorage clear)
    fetch("/api/health/config", { cache: "no-store" })
      .then(r => r.json())
      .then((d: { superadmin_exists?: boolean }) => {
        if (d.superadmin_exists) {
          localStorage.setItem(SETUP_KEY, "true");
        } else {
          setShowWizard(true);
        }
      })
      .catch(() => {
        // API unreachable — show wizard so operator can diagnose
        setShowWizard(true);
      });
  }, []);

  return (
    <ThemeProvider>
    <CompactNumbersProvider>
    {showWizard && <SetupWizard onClose={() => setShowWizard(false)} />}
    <AuthGate>
    <CurrentUserProvider>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {/* Main app — with sidebar + topbar */}
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="marketplace" element={<MarketplacePage />} />
          <Route path="build-a-plugin" element={<BuildAPluginPage />} />
          {/* B165 (v0.9.5): Connections promoted to top-level. The
              old /settings/connections URL redirects here for bookmark
              compatibility. ConnectionsPanel.tsx (the duplicate inside
              Settings) was deleted as part of the same release. */}
          {/* v1.0: unified Data Explorer. /data is the one nav entry that
              lists every source (operator connections + plugin sources).
              /connections and /datasets stay live for bookmark compat and
              are still the right home for credential management. */}
          <Route path="data" element={<DataPage />} />
          <Route path="connections" element={<ConnectionsPage />} />
          <Route path="connections/:id" element={<ConnectionDetailPage />} />
          <Route path="connections/:id/tables/:schema/:table" element={<ConnectionTableRowsPage />} />
          <Route path="settings/connections" element={<Navigate to="/connections" replace />} />
          <Route path="datasets" element={<DatasetsPage />} />
          {/* B170 (v0.9.5.2): row-browsing for a single (plugin, table)
              moved from a top-level /data-port page to a drilldown leaf. */}
          <Route path="datasets/:plugin/:table" element={<DatasetDetailPage />} />
          <Route path="shares" element={<SharesPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="annotations" element={<AnnotationsPage />} />
          <Route path="plugins" element={<PluginsPage />} />
          <Route path="plugins/:pluginId" element={<PluginDetailPage />} />
          <Route path="marketplace/:pluginId" element={<PluginDetailPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="settings/:tab" element={<SettingsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          {/* P112 v0.8.3: /system/:tab is canonical; /system bare redirects
              to /system/health. /health-overview stays working for existing
              bookmarks. Path params match the rest of the app's convention
              (/settings/:tab etc) — no query strings. */}
          <Route path="health-overview" element={<Navigate to="/system/health" replace />} />
          <Route path="system" element={<Navigate to="/system/health" replace />} />
          {/* B230 (v0.9.8.3): RBAC audit matrix. Specific path before
              /system/:tab so the literal match beats the param match. */}
          <Route path="system/permissions" element={<SystemPermissionsPage />} />
          {/* B252 (v0.9.10.0.2): user management moved from Settings → Users
              to System → Users. Same component (UsersPanel); cleaner home. */}
          <Route path="system/users" element={<SystemUsersPage />} />
          {/* Backward-compat: bookmarks to /settings/users redirect. */}
          <Route path="settings/users" element={<Navigate to="/system/users" replace />} />
          <Route path="system/:tab" element={<HealthOverviewPage />} />
          <Route path="admin/cli" element={<AdminCliPage />} />
          {/* B221 (v0.9.7.1): native API reference page. Path is
              /docs/api — NOT /api/* — because /api/* is reserved for the
              FastAPI backend namespace and gets caught by AuthMiddleware. */}
          <Route path="docs/api" element={<ApiReferencePage />} />
          <Route path="install-plugin" element={<InstallPluginPage />} />
          {/* B170 (v0.9.5.2): /data-port retired. Old bookmarks redirect
              to /datasets. Deep-links with ?plugin=&table= are NOT preserved
              (the new URL shape is /datasets/:plugin/:table). */}
          <Route path="data-port" element={<Navigate to="/datasets" replace />} />
          <Route path="data-port/*" element={<Navigate to="/datasets" replace />} />
          <Route path="plugin/:pluginId/*" element={<PluginPage />} />
          <Route path="dashboards" element={<DashboardManagerPage />} />
          <Route path="dashboards/new" element={<DashboardBuilderPage />} />
          <Route path="dashboards/edit/:slug" element={<DashboardBuilderPage />} />
          <Route path="dashboards/:slug" element={<DashboardViewPage />} />
          <Route path="docs" element={<DocsPage />} />
          <Route path="docs/:slug" element={<DocsPage />} />
        </Route>

        {/* Embed routes — no sidebar/topbar, just the content + badge */}
        <Route element={<EmbedLayout />}>
          <Route path="embed/dashboard/:pluginId/:dashboardName" element={<EmbedDashboardPage />} />
          <Route path="embed/widget/:pluginId/:dashboardName/:widgetIndex" element={<EmbedWidgetPage />} />
          <Route path="embed/page/:pluginId/:pageName" element={<EmbedPluginPage />} />
          <Route path="embed/plugin/:pluginId" element={<EmbedMultiPage />} />
        </Route>
        {/* Canvas routes — full-page takeover, custom theming, no app shell */}
        <Route element={<CanvasLayout />}>
          <Route path="canvas/:pluginId/:pageName" element={<CanvasPage />} />
        </Route>

        {/* Shared view — no app shell, no auth (password checked by the share API) */}
        <Route path="shared/:shareId" element={<SharedViewPage />} />

        {/* Accept invite — no app shell, no auth (token in URL validates the invite) */}
        <Route path="accept-invite" element={<AcceptInvitePage />} />

        {/* B251 (v0.9.10.0.3): password reset link landing page — no app shell, no
            auth (token in URL validates and is consumed by /api/auth/reset-password). */}
        <Route path="reset-password" element={<ResetPasswordPage />} />
      </Routes>
    </BrowserRouter>
    </CurrentUserProvider>
    </AuthGate>
    </CompactNumbersProvider>
    </ThemeProvider>
  );
}
