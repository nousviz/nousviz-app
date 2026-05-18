/**
 * SystemTabBar — shared tab strip for all /system/* pages
 * (B271 v0.9.11.13.1).
 *
 * Used by HealthOverviewPage, SystemPermissionsPage, SystemUsersPage so
 * the navigation between operator-observability sections is consistent
 * regardless of which page you're on. Renders as the tab strip + an
 * optional right-side action slot.
 *
 * The 6 tabs match the sidebar's System section exactly so the two
 * surfaces never disagree about what's available.
 */

import { useNavigate, useParams, useLocation } from "react-router-dom";
import { Activity, HardDrive, Clock, FileText, Shield, Users } from "lucide-react";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { ScrollableTabs } from "@/components/ui/ScrollableTabs";

export type SystemTabId = "health" | "resources" | "jobs" | "logs" | "permissions" | "users";

interface SystemTabDef {
  id: SystemTabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Optional permission required to render the tab. Hidden if the user
   * lacks it (matches the sidebar's role-aware filtering). */
  requirePermission?: string;
}

export const SYSTEM_TABS: SystemTabDef[] = [
  { id: "health", label: "Health", icon: Activity },
  { id: "resources", label: "Resources", icon: HardDrive },
  { id: "jobs", label: "Jobs", icon: Clock },
  { id: "logs", label: "Logs", icon: FileText, requirePermission: "system.logs" },
  { id: "permissions", label: "Permissions", icon: Shield, requirePermission: "system.audit" },
  { id: "users", label: "Users", icon: Users, requirePermission: "users.manage" },
];

interface SystemTabBarProps {
  /** Optional override; defaults to detecting from route. */
  active?: SystemTabId;
  /** Renders to the right of the tab strip. Used for refresh buttons etc. */
  rightSlot?: React.ReactNode;
}

export default function SystemTabBar({ active, rightSlot }: SystemTabBarProps) {
  const navigate = useNavigate();
  const params = useParams<{ tab?: string }>();
  const location = useLocation();
  const { hasPermission } = useCurrentUser();

  // Detect active tab from route when not overridden.
  const detected: SystemTabId = (() => {
    if (params.tab && SYSTEM_TABS.some(t => t.id === params.tab)) return params.tab as SystemTabId;
    // /system/permissions and /system/users are literal routes
    if (location.pathname.startsWith("/system/permissions")) return "permissions";
    if (location.pathname.startsWith("/system/users")) return "users";
    return "health";
  })();
  const activeTab = active ?? detected;

  const visibleTabs = SYSTEM_TABS.filter(t => !t.requirePermission || hasPermission(t.requirePermission));

  // B288 (v0.9.11.26): ScrollableTabs primitive — right-edge fade hint
  // when more tabs exist offscreen; rightSlot stacks below on `<sm`.
  return (
    <ScrollableTabs
      tabs={visibleTabs.map((t) => ({
        id: t.id,
        label: t.label,
        icon: <t.icon className="w-4 h-4" />,
      }))}
      current={activeTab}
      onChange={(id) => navigate(`/system/${id}`)}
      ariaLabel="System sections"
      action={rightSlot}
    />
  );
}
