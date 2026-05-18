/**
 * SystemUsersPage — operator-facing user management.
 *
 * B252 (v0.9.10.0.2): moved from Settings → Users to System → Users.
 * Reasoning: user management is operational (RBAC, impersonation,
 * deactivation), not configuration; sits naturally alongside Health,
 * Jobs, Logs, Permissions in the System sidebar section.
 *
 * The /settings/users route still works (redirects here) so existing
 * bookmarks don't break.
 *
 * Identical content to the old Settings → Users tab — just rendered
 * at a top-level system page with appropriate header.
 */

import { Users } from "lucide-react";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import UsersPanel from "@/widgets/UsersPanel";
import SystemTabBar from "@/components/system/SystemTabBar";

export default function SystemUsersPage() {
  useMarkBootReadyOnMount();

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* B271 v0.9.11.13.1: shared tab strip across all /system/* pages */}
      <SystemTabBar active="users" />
      <header className="flex items-center gap-2">
        <Users className="w-4 h-4 text-muted-foreground" />
        <h1 className="font-display text-base text-foreground">Users</h1>
      </header>

      <UsersPanel />
    </div>
  );
}
