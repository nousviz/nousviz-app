import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import RestartRequiredBanner from "./RestartRequiredBanner";
import ImpersonationBanner from "./ImpersonationBanner";
import ImpersonationExpiredToast from "./ImpersonationExpiredToast";
import StepUpController from "@/components/auth/StepUpController";
import ErrorBoundary from "@/components/ErrorBoundary";
import { useActivityTracking } from "@/hooks/useActivityTracking";

export default function AppLayout() {
  useActivityTracking();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {/* B236 (v0.9.10.0): real impersonation banner — replaces v0.9.8.4's
          frontend-only PreviewBanner. Shown when /api/auth/me reports an
          acting_as field (i.e. the session is impersonating). */}
      <ImpersonationBanner />
      {/* B254 (v0.9.10.0.5): toast that fires when an impersonation
          auto-expired on the server side (acting_as_until passed). The
          banner above disappears at the same moment; the toast is the
          one-shot heads-up that the user is back as themselves. */}
      <ImpersonationExpiredToast />
      {/* B236: globally-mounted re-auth modal triggered by 401-stepup_required
          responses from apiFetch. Lives outside Sidebar/Topbar so it
          covers the whole app. */}
      <StepUpController />
      <Sidebar
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        onClose={() => setSidebarOpen(false)}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
      />
      <Topbar
        sidebarCollapsed={sidebarCollapsed}
        onMenuClick={() => {
          if (window.innerWidth < 768) {
            setSidebarOpen(o => !o);
          } else {
            setSidebarCollapsed(c => !c);
          }
        }}
      />
      <main className={`pt-[calc(var(--topbar-h)+var(--banner-h,0px))] min-h-screen transition-all duration-200 flex flex-col ${
        sidebarCollapsed ? "md:ml-16" : "md:ml-[var(--sidebar-w)]"
      }`}>
        <RestartRequiredBanner />
        <div className="flex-1 p-4 md:p-6 [overflow-x:clip]">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
