/**
 * SystemPermissionsPage — read-only RBAC audit matrix (B230, v0.9.8.3).
 *
 * Final release in the v0.9.8.x RBAC redesign sequence. Operators
 * answer three questions on this page:
 *   1. What can role X do?
 *   2. What permission does route Y need, and which roles hold it?
 *   3. Is anyone actually using this permission? (last-accessed column)
 *
 * Read-only. Edit affordances arrive in v0.9.9.x along with the
 * DB-backed override table and operator-controlled permission mapping.
 *
 * Plugin routes get a "default, not enforced" badge — they're in the
 * registry for visibility but the auto-default permission isn't yet
 * enforced via the registry dependency. The banner at the top of the
 * page calls this out explicitly.
 */

import { apiFetch } from "@/lib/api";
import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import {
  Shield, Lock, AlertTriangle, RefreshCw, Download, Search,
  ChevronRight, ChevronDown, Check, Loader2, AlertCircle, Info,
  CheckCircle2, XCircle, User, X,
} from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import SystemTabBar from "@/components/system/SystemTabBar";

// ── Types ────────────────────────────────────────────────────────────

interface PermissionMeta {
  description: string;
  sensitive: boolean;
}

interface RouteEntry {
  method: string;
  path: string;
  permission: string;
  is_plugin_route: boolean;
  is_plugin_default: boolean;
  last_accessed: Record<string, string | null>;
}

interface AuditSummary {
  window_hours: number;
  decisions: { allow: number; deny: number; shadow_mismatch: number };
  top_denials: { permission: string; count: number }[];
}

interface RoleData {
  kind: "built_in" | "custom";
  display_name: string;
  description?: string | null;
  based_on?: string | null;
  default_permissions: string[];
  permissions: string[];
  overrides: { grants: string[]; revokes: string[] };
  created_by?: string;
  created_at?: string;
}

interface RegistrySnapshot {
  permissions: Record<string, PermissionMeta>;
  roles: Record<string, string[]>;            // backward-compat: resolved set
  role_data?: Record<string, RoleData>;        // B232+: richer per-role data
  routes: RouteEntry[];
  public_routes: [string, string][];
  audit_summary: AuditSummary;
  shadow_mode: boolean;
  version: string;
}

interface UserEntry {
  id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  permissions: string[];
  last_activity_at: string | null;
  last_activity_route: string | null;
}

type View = "matrix" | "routes" | "users" | "history" | "defaults";

interface AuditEntry {
  id: number;
  occurred_at: string;
  actor_user_id: string | null;
  actor_email: string | null;
  actor_role: string | null;
  action:
    | "grant" | "revoke" | "clear" | "create_role" | "delete_role"
    | "impersonate_start" | "impersonate_end"
    | "password_reset_cli" | "password_reset_request"
    | "password_reset_completed" | "password_change_self"
    | "acl_grant" | "acl_revoke" | "set_default_policy";
  target_role: string | null;
  target_permission: string | null;
  target_resource_type?: string | null;
  target_resource_id?: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  note: string | null;
}

interface AuditLogResponse {
  entries: AuditEntry[];
  next_cursor: number | null;
}

const ROLE_ORDER = ["viewer", "analyst", "admin", "superadmin"] as const;
type Role = (typeof ROLE_ORDER)[number];

// Resource grouping by permission prefix — drives the resource filter.
function resourceOf(permission: string): string {
  const dot = permission.indexOf(".");
  return dot === -1 ? "other" : permission.slice(0, dot);
}

// ── Page ─────────────────────────────────────────────────────────────

export default function SystemPermissionsPage() {
  useMarkBootReadyOnMount();
  const { hasPermission, loading: userLoading } = useCurrentUser();
  const canEdit = hasPermission("rbac.edit");

  const [snapshot, setSnapshot] = useState<RegistrySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const lastRefreshRef = useRef<number>(0);

  const [view, setView] = useState<View>("matrix");
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [resourceFilter, setResourceFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [explainerOpen, setExplainerOpen] = useState(false);

  // B231 (v0.9.8.4 followup): the matrix notice can be dismissed;
  // preference persists across sessions in localStorage so returning
  // operators don't have to re-acknowledge it. The key is versioned by
  // its content — when the message changes substantively, bump the key
  // so previously-dismissed operators see the updated text once.
  const NOTICE_KEY = "nousviz:rbac_matrix_notice_dismissed_v0991";
  const [noticeDismissed, setNoticeDismissed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(NOTICE_KEY) === "true";
  });
  const dismissNotice = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem(NOTICE_KEY, "true");
    }
    setNoticeDismissed(true);
  };
  const restoreNotice = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(NOTICE_KEY);
    }
    setNoticeDismissed(false);
  };

  // B231: Users tab data — fetched lazily on first activation.
  const [users, setUsers] = useState<UserEntry[] | null>(null);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);

  // B234: History tab data — RBAC config audit log entries.
  const [auditEntries, setAuditEntries] = useState<AuditEntry[] | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditExpandedId, setAuditExpandedId] = useState<number | null>(null);
  const [auditActionFilter, setAuditActionFilter] = useState<string>("all");

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const r = await apiFetch("/api/system/permissions");
      if (!r.ok) {
        if (r.status === 403) {
          throw new Error("You need the system.audit permission to view this page.");
        }
        throw new Error(`Failed to load registry (${r.status}).`);
      }
      const data: RegistrySnapshot = await r.json();
      setSnapshot(data);
      setError(null);
      lastRefreshRef.current = Date.now();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const r = await apiFetch("/api/system/users-with-permissions");
      if (!r.ok) {
        throw new Error(`Failed to load users (${r.status}).`);
      }
      const data: { users: UserEntry[] } = await r.json();
      setUsers(data.users);
      setUsersError(null);
    } catch (e) {
      setUsersError(e instanceof Error ? e.message : "Unknown error.");
    } finally {
      setUsersLoading(false);
    }
  }, []);

  // B234: load the RBAC config audit log. Filters via the existing
  // `roleFilter` (target role) and `auditActionFilter`. No cursor
  // pagination wired up yet — first 50 entries is enough for v0.9.9.2;
  // pagination lands when log volume justifies it.
  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const params = new URLSearchParams();
      if (roleFilter !== "all") params.set("target_role", roleFilter);
      if (auditActionFilter !== "all") params.set("action", auditActionFilter);
      params.set("limit", "100");
      const r = await apiFetch(`/api/system/rbac-audit-log?${params}`);
      if (!r.ok) {
        throw new Error(`Failed to load audit log (${r.status}).`);
      }
      const data: AuditLogResponse = await r.json();
      setAuditEntries(data.entries);
      setAuditError(null);
    } catch (e) {
      setAuditError(e instanceof Error ? e.message : "Unknown error.");
    } finally {
      setAuditLoading(false);
    }
  }, [roleFilter, auditActionFilter]);

  useEffect(() => {
    load();
  }, [load]);

  // B231: lazy-load users when the Users tab first activates. Re-loads
  // on Refresh button click via the global load() chain (see below).
  useEffect(() => {
    if (view === "users" && users === null && !usersLoading) {
      loadUsers();
    }
  }, [view, users, usersLoading, loadUsers]);

  // B234: lazy-load audit log when the History tab first activates.
  // Re-loads when the role or action filter changes (loadAudit's deps).
  useEffect(() => {
    if (view === "history" && !auditLoading) {
      loadAudit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, roleFilter, auditActionFilter]);

  // Auto-refresh the last-accessed column every 60s. Don't auto-refresh
  // permissions/roles — those don't change between requests.
  useEffect(() => {
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  const allResources = useMemo(() => {
    if (!snapshot) return [];
    const set = new Set<string>();
    for (const name of Object.keys(snapshot.permissions)) {
      set.add(resourceOf(name));
    }
    return Array.from(set).sort();
  }, [snapshot]);

  // Build role_data with a backward-compat fallback. v0.9.9.0+ servers
  // return role_data directly. Older servers (v0.9.8.x) only return the
  // flat `roles` mapping; synthesize a minimal RoleData from that so the
  // matrix still renders (cells just show as default-only).
  const roleData = useMemo<Record<string, RoleData>>(() => {
    if (!snapshot) return {};
    if (snapshot.role_data) return snapshot.role_data;
    const fallback: Record<string, RoleData> = {};
    for (const [role, perms] of Object.entries(snapshot.roles)) {
      fallback[role] = {
        kind: "built_in",
        display_name: role,
        default_permissions: perms,
        permissions: perms,
        overrides: { grants: [], revokes: [] },
      };
    }
    return fallback;
  }, [snapshot]);

  // Cell click handler. Confirms before editing built-in roles. Calls the
  // appropriate API endpoint, then reloads the snapshot to pick up the
  // change. We could optimistic-update but reloading is simpler and the
  // request is fast.
  const onCellEdit = useCallback(async (
    role: string,
    permission: string,
    state: CellState,
    isSensitive: boolean,
  ) => {
    if (!canEdit) return;

    const data = roleData[role];
    if (!data) return;

    // If sensitive and would be a grant on a non-admin role, block.
    const wouldGrant = state.overrideKind === null && !state.default;
    if (wouldGrant && isSensitive && !["admin", "superadmin"].includes(role)) {
      window.alert(
        `Cannot grant sensitive permission "${permission}" to role "${role}". ` +
        "Sensitive permissions can only be held by admin or superadmin roles."
      );
      return;
    }

    // Confirm dialog for built-in role edits.
    if (data.kind === "built_in") {
      const action = state.overrideKind !== null
        ? "clear the override on"
        : (state.default ? "revoke the default permission" : "grant the permission")
          + " on";
      const ok = window.confirm(
        `You're about to ${action} the built-in "${role}" role for permission "${permission}". ` +
        "This affects every user with this role across the platform. Continue?"
      );
      if (!ok) return;
    }

    try {
      if (state.overrideKind !== null) {
        // Clear the override.
        const r = await apiFetch(
          `/api/system/role-overrides/${encodeURIComponent(role)}/${encodeURIComponent(permission)}`,
          { method: "DELETE" },
        );
        if (!r.ok && r.status !== 204) {
          throw new Error(`Failed to clear override (${r.status})`);
        }
      } else {
        // Create an override that opposes the default.
        const kind = state.default ? "revoke" : "grant";
        const r = await apiFetch("/api/system/role-overrides", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role, permission, kind }),
        });
        if (!r.ok) {
          let detail = `${r.status}`;
          try {
            const j = await r.json();
            detail = j.detail || detail;
          } catch { /* ignore */ }
          throw new Error(`Failed to save override: ${detail}`);
        }
      }
      // Reload to pick up the change.
      await load();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Failed to update permission");
    }
  }, [canEdit, roleData]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Permissions filtered by role + resource + search.
  const filteredPermissions = useMemo(() => {
    if (!snapshot) return [] as [string, PermissionMeta][];
    const term = search.trim().toLowerCase();
    const entries = Object.entries(snapshot.permissions);

    return entries
      .filter(([name, meta]) => {
        if (resourceFilter !== "all" && resourceOf(name) !== resourceFilter) return false;
        if (roleFilter !== "all") {
          const heldBy = snapshot.roles[roleFilter] || [];
          if (!heldBy.includes(name)) return false;
        }
        if (term) {
          if (
            !name.toLowerCase().includes(term) &&
            !meta.description.toLowerCase().includes(term)
          ) return false;
        }
        return true;
      })
      .sort(([a], [b]) => a.localeCompare(b));
  }, [snapshot, roleFilter, resourceFilter, search]);

  // Routes filtered by role/resource/search/permission.
  const filteredRoutes = useMemo(() => {
    if (!snapshot) return [] as RouteEntry[];
    const term = search.trim().toLowerCase();
    return snapshot.routes
      .filter((r) => {
        if (resourceFilter !== "all" && resourceOf(r.permission) !== resourceFilter) return false;
        if (roleFilter !== "all") {
          const heldBy = snapshot.roles[roleFilter] || [];
          if (!heldBy.includes(r.permission)) return false;
        }
        if (term) {
          if (
            !r.path.toLowerCase().includes(term) &&
            !r.permission.toLowerCase().includes(term) &&
            !r.method.toLowerCase().includes(term)
          ) return false;
        }
        return true;
      });
  }, [snapshot, roleFilter, resourceFilter, search]);

  const togglePermissionExpanded = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  const handleExport = () => {
    if (!snapshot) return;
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nousviz-rbac-snapshot-${snapshot.version}-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ── Render guards ──────────────────────────────────────────────────

  // Wait for user context to resolve before deciding what to show.
  if (userLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-12">
        <Loader2 className="w-4 h-4 animate-spin" />
        Checking permissions…
      </div>
    );
  }

  // Graceful 403 — caught client-side before the API call would have
  // failed anyway. Saves a round-trip and lets us show a useful message.
  if (!hasPermission("system.audit")) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <div className="bg-card rounded-lg border border-amber-500/30 p-6 text-sm">
          <div className="flex items-start gap-3">
            <Lock className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-foreground mb-1">Not authorized</p>
              <p className="text-muted-foreground">
                The RBAC permissions matrix is admin-only. Your account
                doesn&apos;t hold the <span className="font-mono-deck">system.audit</span> permission.
              </p>
              <p className="text-muted-foreground mt-2 text-xs">
                Operators with admin or superadmin role have access. Ask your administrator
                if you need to audit role-permission mappings.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-12">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading RBAC registry…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <div className="bg-card rounded-lg border border-rose-500/30 p-6 text-sm">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-foreground mb-1">Could not load permissions</p>
              <p className="text-muted-foreground">{error}</p>
              <button
                type="button"
                onClick={load}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!snapshot) return null;

  // ── Page body ──────────────────────────────────────────────────────

  return (
    <div className="space-y-4 max-w-[1400px]">
      {/* B271 v0.9.11.13.1: shared tab strip across all /system/* pages */}
      <SystemTabBar active="permissions" />
      {/* Page header */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-muted-foreground" />
          <h1 className="font-display text-base text-foreground">RBAC permissions</h1>
          <span className="text-xs font-mono-deck text-muted-foreground">
            v{snapshot.version}
          </span>
          {snapshot.shadow_mode && (
            <span
              className="text-[10px] font-mono-deck uppercase tracking-wide bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded"
              title="Registry verdicts are logged to auth_audit but not enforced. Inline _require_* shims do the actual gating until v0.9.9.x."
            >
              shadow mode
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* B236 (v0.9.10.0): the v0.9.8.4 "view as" picker was removed.
              Real impersonation lives on the Users page. The matrix
              displays the registry as the operator sees it; impersonating
              a target user is a different action with its own audit trail. */}
          <button
            type="button"
            onClick={() => {
              load();
              if (view === "users") loadUsers();
              if (view === "history") loadAudit();
            }}
            disabled={refreshing || usersLoading || auditLoading}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-secondary"
            title="Refresh"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", (refreshing || usersLoading || auditLoading) && "animate-spin")} />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleExport}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-secondary"
            title="Export the current registry snapshot as JSON"
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>
      </header>

      {/* Honest-banner: matrix capabilities. Dismissable; persists. */}
      {!noticeDismissed ? (
        <div className="bg-card rounded-lg border border-amber-500/30 p-4 text-xs flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-muted-foreground space-y-1 flex-1">
            <p>
              <strong className="text-foreground">Editing live.</strong>{" "}
              {canEdit ? (
                <>Click any cell to grant or revoke a permission for that role. Modified cells
                get an amber dot. Built-in role edits prompt for confirmation, then for
                password re-authentication.</>
              ) : (
                <>Editing requires the <span className="font-mono-deck">rbac.edit</span> permission
                (held by superadmin). Your role can audit but not modify.</>
              )}
            </p>
            <p>
              <strong className="text-foreground">Permissions are enforced.</strong> The registry
              gates every authenticated request: <span className="font-mono-deck">requires(...)</span>{" "}
              dependencies raise 403 on permission denial. Every decision is logged to{" "}
              <span className="font-mono-deck">auth_audit</span>; configuration changes log to{" "}
              <span className="font-mono-deck">rbac_config_audit</span>. The History tab shows the
              mutation timeline.
            </p>
            <p>
              Plugin routes (rows tagged{" "}
              <span className="inline-block px-1.5 py-0.5 text-[10px] font-mono-deck bg-secondary text-muted-foreground rounded">
                plugin
              </span>
              ) are gated by per-plugin permissions of the form{" "}
              <span className="font-mono-deck">plugin.&lt;slug&gt;.&lt;level&gt;</span>{" "}
              (B247, v0.9.10.6). Plugins that haven&apos;t declared a{" "}
              <span className="font-mono-deck">permissions:</span> block in their manifest fall back
              to the legacy method-derived default and show the{" "}
              <span className="inline-block px-1.5 py-0.5 text-[10px] font-mono-deck bg-secondary text-muted-foreground rounded">
                legacy
              </span>{" "}
              tag. Operators override per-plugin grants the same way as core permissions.
            </p>
          </div>
          <button
            type="button"
            onClick={dismissNotice}
            className="text-muted-foreground hover:text-foreground p-1 -m-1 rounded hover:bg-secondary"
            title="Dismiss this notice (you can restore it from the link below)"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="text-[11px] text-muted-foreground/60 -mb-2">
          <button
            type="button"
            onClick={restoreNotice}
            className="hover:text-muted-foreground underline-offset-2 hover:underline"
          >
            Show release notice
          </button>
        </div>
      )}

      {/* Audit summary tiles */}
      <AuditSummaryRow summary={snapshot.audit_summary} />

      <ExplainerBlock open={explainerOpen} onToggle={() => setExplainerOpen((v) => !v)} />

      {/* View tabs + filters */}
      <div className="bg-card rounded-lg border border-border p-3 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 bg-secondary rounded-md p-0.5">
            <ViewTab active={view === "matrix"} onClick={() => setView("matrix")}>
              Role × Permission
            </ViewTab>
            <ViewTab active={view === "routes"} onClick={() => setView("routes")}>
              Routes
            </ViewTab>
            <ViewTab active={view === "users"} onClick={() => setView("users")}>
              Users
            </ViewTab>
            <ViewTab active={view === "history"} onClick={() => setView("history")}>
              History
            </ViewTab>
            <ViewTab active={view === "defaults"} onClick={() => setView("defaults")}>
              Resource defaults
            </ViewTab>
          </div>

          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="search"
                placeholder={
                  view === "matrix" ? "Search permissions…"
                  : view === "routes" ? "Search routes…"
                  : view === "users" ? "Search users by email…"
                  : "Search history (actor email, target, permission)…"
                }
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-8 pl-8 pr-3 rounded-md border border-border bg-background text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <Filter
            label="Role"
            value={roleFilter}
            onChange={(v) => setRoleFilter(v as Role | "all")}
            options={[
              { value: "all", label: "All roles" },
              ...ROLE_ORDER.map((r) => ({ value: r, label: r })),
            ]}
          />

          <Filter
            label="Resource"
            value={resourceFilter}
            onChange={setResourceFilter}
            options={[
              { value: "all", label: "All resources" },
              ...allResources.map((r) => ({ value: r, label: r })),
            ]}
          />
        </div>

        {/* Stats line */}
        <div className="text-[11px] font-mono-deck text-muted-foreground">
          {view === "matrix" && (
            <>
              {filteredPermissions.length} permission{filteredPermissions.length === 1 ? "" : "s"} ·{" "}
              {Object.keys(snapshot.roles).length} roles ·{" "}
              {snapshot.routes.length} registered routes ·{" "}
              {snapshot.public_routes.length} public
            </>
          )}
          {view === "routes" && (
            <>
              {filteredRoutes.length} route{filteredRoutes.length === 1 ? "" : "s"}
              {snapshot.routes.length !== filteredRoutes.length && (
                <> (of {snapshot.routes.length})</>
              )}
            </>
          )}
          {view === "users" && users && (
            <>
              {users.length} user{users.length === 1 ? "" : "s"} ·{" "}
              {users.filter((u) => u.is_active).length} active ·{" "}
              {users.filter((u) => !u.is_active).length} inactive
            </>
          )}
          {view === "history" && auditEntries && (
            <>
              {auditEntries.length} change{auditEntries.length === 1 ? "" : "s"}
              {auditActionFilter !== "all" && (
                <> · filtered by action <span className="text-foreground">{auditActionFilter}</span></>
              )}
              {roleFilter !== "all" && (
                <> · target role <span className="text-foreground">{roleFilter}</span></>
              )}
            </>
          )}
        </div>

        {/* B234: action filter only visible on the History tab. */}
        {view === "history" && (
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/50 mt-1">
            <Filter
              label="Action"
              value={auditActionFilter}
              onChange={setAuditActionFilter}
              options={[
                { value: "all", label: "All actions" },
                { value: "grant", label: "grant" },
                { value: "revoke", label: "revoke" },
                { value: "clear", label: "clear" },
                { value: "create_role", label: "create_role" },
                { value: "delete_role", label: "delete_role" },
              ]}
            />
          </div>
        )}
      </div>

      {/* Body */}
      {view === "matrix" && (
        <MatrixView
          permissions={filteredPermissions}
          roleData={roleData}
          routes={snapshot.routes}
          expanded={expanded}
          onToggle={togglePermissionExpanded}
          canEdit={canEdit}
          onCellEdit={onCellEdit}
        />
      )}
      {view === "routes" && (
        <RoutesView routes={filteredRoutes} roles={snapshot.roles} />
      )}
      {view === "users" && (
        <UsersView
          users={users}
          loading={usersLoading}
          error={usersError}
          roleFilter={roleFilter}
          search={search}
          expandedUserId={expandedUserId}
          onToggleUser={(id) => setExpandedUserId((cur) => cur === id ? null : id)}
          onRetry={loadUsers}
        />
      )}
      {view === "history" && (
        <HistoryView
          entries={auditEntries}
          loading={auditLoading}
          error={auditError}
          search={search}
          expandedId={auditExpandedId}
          onToggle={(id) => setAuditExpandedId((cur) => cur === id ? null : id)}
          onRetry={loadAudit}
        />
      )}
      {view === "defaults" && <ResourceDefaultsView canEdit={canEdit} />}
    </div>
  );
}

// ── View components ──────────────────────────────────────────────────

function AuditSummaryRow({ summary }: { summary: AuditSummary }) {
  const total =
    summary.decisions.allow + summary.decisions.deny + summary.decisions.shadow_mismatch;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <SummaryTile
        label={`Allows (${summary.window_hours}h)`}
        value={summary.decisions.allow.toLocaleString()}
        tone="ok"
        title="Successful permission checks. Each operator click on a page typically generates 5–15 of these as the page loads multiple endpoints in parallel."
      />
      <SummaryTile
        label={`Denies (${summary.window_hours}h)`}
        value={summary.decisions.deny.toLocaleString()}
        tone={summary.decisions.deny > 0 ? "warn" : "neutral"}
        title="Permission rejections. Some are normal (anonymous probes, load-balancer health checks before auth, frontend deep links during auth-state transitions). A sustained spike or many denies on the same route by an authenticated user warrants investigation."
      />
      <SummaryTile
        label={`Mismatches (${summary.window_hours}h)`}
        value={summary.decisions.shadow_mismatch.toLocaleString()}
        tone={summary.decisions.shadow_mismatch > 0 ? "error" : "ok"}
        title="Routes where the registry's verdict disagrees with the inline _require_* shim. Zero is the only acceptable value. If this is non-zero, the registry mapping is wrong somewhere — fix before v0.9.9.x flips enforcement to registry-only."
      />
      <SummaryTile
        label="Total decisions"
        value={total.toLocaleString()}
        tone="neutral"
        title="Sum of all permission checks (allows + denies + mismatches) in the window. Useful as a load indicator — a sudden drop suggests the API is down or quiet; a spike suggests heavy traffic or a runaway client."
      />
    </div>
  );
}

function ExplainerBlock({
  open, onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="bg-card rounded-lg border border-border">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 px-4 py-2.5 text-xs text-muted-foreground hover:text-foreground"
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-2">
          <Info className="w-3.5 h-3.5" />
          What do these numbers mean?
        </span>
        {open
          ? <ChevronDown className="w-3.5 h-3.5" />
          : <ChevronRight className="w-3.5 h-3.5" />}
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-3 text-xs text-muted-foreground border-t border-border">
          <div>
            <p className="font-medium text-foreground mb-1">Allows</p>
            <p>
              Every successful permission check. The dashboard alone fans out to ~10 API calls
              per load — each one is a row here. Operators clicking around generate hundreds of
              allows per session. This number tracks load, not security.
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Denies</p>
            <p>
              Permission rejections. <strong className="text-foreground">Many denies are
              normal:</strong>
            </p>
            <ul className="list-disc pl-5 mt-1 space-y-0.5">
              <li>Load balancers and uptime monitors hitting authenticated routes (e.g. probes
                of <span className="font-mono-deck">/api/health/record</span>) before
                the request has a session token.</li>
              <li>Anonymous browser requests during the auth flow (e.g. before login completes).</li>
              <li>Frontend code deep-linking to a permissioned page that briefly tries to fetch
                its data before the role-aware nav has hidden the link.</li>
            </ul>
            <p className="mt-1">
              What to investigate: a single user generating dozens of denies on a particular
              route (possible role drift), or a sustained order-of-magnitude jump from baseline.
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Mismatches</p>
            <p>
              Routes where the registry's verdict disagrees with the inline shim's verdict (the
              two-check belt-and-suspenders the v0.9.8.x sequence runs in shadow mode).{" "}
              <strong className="text-rose-400">Zero is the only acceptable value.</strong> A
              non-zero count means the registry has a wrong permission for some route, and
              fixing it is a prerequisite for the v0.9.9.x enforcement flip.
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">Total decisions</p>
            <p>
              Sum of the above. Useful as a load gauge: a sudden drop suggests the API is down
              or quiet, a sustained spike suggests heavy traffic or a misbehaving client looping.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryTile({
  label, value, tone, title,
}: {
  label: string;
  value: string;
  tone: "ok" | "warn" | "error" | "neutral";
  title?: string;
}) {
  const toneClass =
    tone === "ok" ? "text-emerald-400" :
    tone === "warn" ? "text-amber-400" :
    tone === "error" ? "text-rose-400" :
    "text-foreground";
  return (
    <div className="bg-card rounded-lg border border-border p-3" title={title}>
      <div className="text-[10px] font-mono-deck uppercase tracking-wide text-muted-foreground mb-1">
        {label}
      </div>
      <div className={cn("text-lg font-display", toneClass)}>{value}</div>
    </div>
  );
}

function ViewTab({
  active, onClick, children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "px-2.5 py-1 text-xs rounded transition-colors",
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

function Filter({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span className="font-mono-deck uppercase tracking-wide">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 px-2 rounded-md border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}

// ── Matrix view (Role × Permission) ─────────────────────────────────

interface CellState {
  default: boolean;     // is in role's static catalog default?
  effective: boolean;   // is in resolved set (post-override)?
  overrideKind: "grant" | "revoke" | null;
}

function cellState(roleData: RoleData, permission: string): CellState {
  const isDefault = roleData.default_permissions.includes(permission);
  const isEffective = roleData.permissions.includes(permission);
  let overrideKind: "grant" | "revoke" | null = null;
  if (roleData.overrides.grants.includes(permission)) overrideKind = "grant";
  else if (roleData.overrides.revokes.includes(permission)) overrideKind = "revoke";
  return { default: isDefault, effective: isEffective, overrideKind };
}

function MatrixView({
  permissions, roleData, routes, expanded, onToggle,
  canEdit, onCellEdit,
}: {
  permissions: [string, PermissionMeta][];
  roleData: Record<string, RoleData>;
  routes: RouteEntry[];
  expanded: Set<string>;
  onToggle: (name: string) => void;
  canEdit: boolean;
  onCellEdit: (role: string, permission: string, current: CellState, isSensitive: boolean) => Promise<void>;
}) {
  if (permissions.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        No permissions match the current filters.
      </div>
    );
  }

  // Pre-bucket routes by permission for fast expand-row rendering.
  const routesByPermission = useMemo(() => {
    const m = new Map<string, RouteEntry[]>();
    for (const r of routes) {
      const list = m.get(r.permission);
      if (list) list.push(r);
      else m.set(r.permission, [r]);
    }
    return m;
  }, [routes]);

  // Column order: built-in roles in fixed order, then custom roles
  // alphabetically.
  const orderedRoles = useMemo(() => {
    const builtin = ROLE_ORDER.filter((r) => r in roleData);
    const custom = Object.keys(roleData)
      .filter((r) => !ROLE_ORDER.includes(r as Role))
      .sort();
    return [...builtin, ...custom];
  }, [roleData]);

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-secondary/50">
            <tr className="border-b border-border">
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Permission
              </th>
              {orderedRoles.map((r) => {
                const data = roleData[r];
                return (
                  <th
                    key={r}
                    className="text-center px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground"
                    title={`${data.permissions.length} permissions${data.kind === "custom" ? " (custom role)" : ""}`}
                  >
                    <div className="inline-flex items-center gap-1">
                      <span>{data.display_name || r}</span>
                      {data.kind === "custom" && (
                        <span
                          className="text-[8px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400 normal-case"
                          title="Custom role"
                        >
                          custom
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
              <th className="text-right px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Routes
              </th>
            </tr>
          </thead>
          <tbody>
            {permissions.map(([name, meta]) => {
              const isExpanded = expanded.has(name);
              const perRoutes = routesByPermission.get(name) ?? [];
              return (
                <PermissionRow
                  key={name}
                  name={name}
                  meta={meta}
                  roleData={roleData}
                  orderedRoles={orderedRoles}
                  routes={perRoutes}
                  expanded={isExpanded}
                  onToggle={() => onToggle(name)}
                  canEdit={canEdit}
                  onCellEdit={onCellEdit}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PermissionRow({
  name, meta, roleData, orderedRoles, routes, expanded, onToggle,
  canEdit, onCellEdit,
}: {
  name: string;
  meta: PermissionMeta;
  roleData: Record<string, RoleData>;
  orderedRoles: string[];
  routes: RouteEntry[];
  expanded: boolean;
  onToggle: () => void;
  canEdit: boolean;
  onCellEdit: (role: string, permission: string, current: CellState, isSensitive: boolean) => Promise<void>;
}) {
  return (
    <>
      <tr
        className={cn(
          "border-b border-border/50 hover:bg-secondary/30",
          expanded && "bg-secondary/30"
        )}
      >
        <td className="px-3 py-2 cursor-pointer" onClick={onToggle}>
          <div className="flex items-start gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              className="mt-0.5 text-muted-foreground hover:text-foreground"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded
                ? <ChevronDown className="w-3 h-3" />
                : <ChevronRight className="w-3 h-3" />}
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-mono-deck text-foreground">{name}</span>
                {meta.sensitive && (
                  <span
                    className="inline-flex items-center gap-0.5 text-[10px] font-mono-deck bg-rose-500/10 text-rose-400 px-1.5 py-0.5 rounded"
                    title="Sensitive — cannot be granted to non-admin or custom roles"
                  >
                    <Lock className="w-2.5 h-2.5" />
                    sensitive
                  </span>
                )}
              </div>
              <p className="text-muted-foreground mt-0.5">{meta.description}</p>
            </div>
          </div>
        </td>
        {orderedRoles.map((role) => {
          const data = roleData[role];
          const state = cellState(data, name);
          return (
            <PermissionCell
              key={role}
              role={role}
              roleData={data}
              state={state}
              canEdit={canEdit}
              isSensitive={meta.sensitive}
              onEdit={() => onCellEdit(role, name, state, meta.sensitive)}
            />
          );
        })}
        <td className="text-right px-3 py-2 font-mono-deck text-muted-foreground cursor-pointer" onClick={onToggle}>
          {routes.length}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-border/50 bg-background/40">
          <td colSpan={orderedRoles.length + 2} className="px-3 py-3">
            {routes.length === 0 ? (
              <p className="text-[11px] text-muted-foreground italic px-6">
                No routes currently require this permission.
              </p>
            ) : (
              <div className="space-y-1 px-6">
                {routes.map((r) => (
                  <div
                    key={`${r.method}-${r.path}`}
                    className="flex items-center gap-2 text-[11px]"
                  >
                    <MethodPill method={r.method} />
                    <span className="font-mono-deck text-foreground">{r.path}</span>
                    {r.is_plugin_default && <DefaultBadge />}
                    {r.is_plugin_route && !r.is_plugin_default && <PluginBadge />}
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function PermissionCell({
  role, roleData, state, canEdit, isSensitive, onEdit,
}: {
  role: string;
  roleData: RoleData;
  state: CellState;
  canEdit: boolean;
  isSensitive: boolean;
  onEdit: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);

  const isModified = state.overrideKind !== null;

  // Click handler: if there's an override, clear it. If no override,
  // create one that opposes the default.
  // Disabled if the user can't edit OR if granting a sensitive permission
  // to a non-admin role (the API will 409 anyway, but we should preempt).
  const isSensitiveToNonAdmin =
    isSensitive && roleData.kind !== "built_in"
      ? true  // custom roles can never grant sensitive
      : isSensitive && !["admin", "superadmin"].includes(role);
  const wouldBeGrant = !isModified && !state.default;
  const blocked = canEdit && wouldBeGrant && isSensitiveToNonAdmin;

  const interactive = canEdit && !blocked;

  const click = async () => {
    if (!interactive || busy) return;
    setBusy(true);
    try {
      await onEdit();
    } finally {
      setBusy(false);
    }
  };

  // Visual: held = ✓ (emerald if explicit, faint if default); not held = —
  // Modified cells show an amber dot.
  const baseTitle = (() => {
    if (state.overrideKind === "grant") return `Explicit grant — modified from default`;
    if (state.overrideKind === "revoke") return `Explicit revoke — modified from default`;
    if (state.default) return `Default permission for this role`;
    return `Not held by this role`;
  })();

  const editHint = !canEdit
    ? ""
    : blocked
      ? " · Sensitive permission cannot be granted here"
      : isModified
        ? " · Click to clear override (back to default)"
        : ` · Click to ${state.default ? "revoke" : "grant"}`;

  const title = baseTitle + editHint;

  return (
    <td
      className={cn(
        "text-center px-3 py-2 relative",
        interactive && "cursor-pointer hover:bg-secondary/40",
        blocked && "cursor-not-allowed opacity-50",
      )}
      onClick={click}
      title={title}
      aria-disabled={!interactive}
    >
      {state.effective ? (
        <Check
          className={cn(
            "w-3.5 h-3.5 inline",
            isModified && state.overrideKind === "grant"
              ? "text-amber-400"
              : "text-emerald-400",
          )}
          aria-label="Held"
        />
      ) : (
        isModified && state.overrideKind === "revoke" ? (
          <span className="text-rose-400 font-bold" aria-label="Explicitly revoked">✗</span>
        ) : (
          <span className="text-border" aria-label="Not held">—</span>
        )
      )}
      {isModified && (
        <span
          className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-400"
          aria-label="Modified from default"
        />
      )}
    </td>
  );
}

// ── Routes view ──────────────────────────────────────────────────────

function RoutesView({
  routes, roles,
}: {
  routes: RouteEntry[];
  roles: Record<string, string[]>;
}) {
  if (routes.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        No routes match the current filters.
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-secondary/50">
            <tr className="border-b border-border">
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Method
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Path
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Required permission
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Held by
              </th>
              {ROLE_ORDER.map((r) => (
                <th
                  key={r}
                  className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground"
                  title={`Most recent allow decision by ${r} in the last 30 days`}
                >
                  {r} last
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {routes.map((r) => {
              const heldBy = ROLE_ORDER.filter((role) =>
                (roles[role] || []).includes(r.permission),
              );
              return (
                <tr
                  key={`${r.method}-${r.path}`}
                  className="border-b border-border/50 hover:bg-secondary/30"
                >
                  <td className="px-3 py-2"><MethodPill method={r.method} /></td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono-deck text-foreground">{r.path}</span>
                      {r.is_plugin_default && <DefaultBadge />}
                      {r.is_plugin_route && !r.is_plugin_default && <PluginBadge />}
                    </div>
                  </td>
                  <td className="px-3 py-2 font-mono-deck text-foreground">{r.permission}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1 flex-wrap">
                      {heldBy.length === 0 ? (
                        <span className="text-muted-foreground italic">none</span>
                      ) : heldBy.map((role) => (
                        <span
                          key={role}
                          className="text-[10px] font-mono-deck bg-secondary text-muted-foreground px-1.5 py-0.5 rounded"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  </td>
                  {ROLE_ORDER.map((role) => {
                    const ts = r.last_accessed[role];
                    return (
                      <td key={role} className="px-3 py-2 text-muted-foreground">
                        {ts ? (
                          <span title={ts}>{formatRelativeTime(ts)}</span>
                        ) : (
                          <span className="text-border">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── History view (B234) ─────────────────────────────────────────────

const ACTION_LABELS: Record<AuditEntry["action"], string> = {
  grant: "granted",
  revoke: "revoked",
  clear: "cleared override on",
  create_role: "created role",
  delete_role: "deleted role",
  impersonate_start: "started impersonating",
  impersonate_end: "stopped impersonating",
  password_reset_cli: "reset password (CLI)",
  password_reset_request: "requested password reset for",
  password_reset_completed: "completed password reset for",
  password_change_self: "changed own password",
  acl_grant: "granted ACL on",
  acl_revoke: "revoked ACL on",
  set_default_policy: "changed default policy on",
};

const ACTION_TONES: Record<AuditEntry["action"], string> = {
  grant: "text-emerald-400",
  revoke: "text-rose-400",
  clear: "text-muted-foreground",
  create_role: "text-blue-400",
  delete_role: "text-amber-400",
  impersonate_start: "text-amber-400",
  impersonate_end: "text-muted-foreground",
  password_reset_cli: "text-amber-400",
  password_reset_request: "text-muted-foreground",
  password_reset_completed: "text-amber-400",
  password_change_self: "text-muted-foreground",
  acl_grant: "text-emerald-400",
  acl_revoke: "text-rose-400",
  set_default_policy: "text-amber-400",
};

function HistoryView({
  entries, loading, error, search, expandedId, onToggle, onRetry,
}: {
  entries: AuditEntry[] | null;
  loading: boolean;
  error: string | null;
  search: string;
  expandedId: number | null;
  onToggle: (id: number) => void;
  onRetry: () => void;
}) {
  const filtered = useMemo(() => {
    if (!entries) return [] as AuditEntry[];
    const term = search.trim().toLowerCase();
    if (!term) return entries;
    return entries.filter((e) => {
      const haystack = [
        e.actor_email || "",
        e.actor_user_id || "",
        e.target_role,
        e.target_permission || "",
        e.note || "",
      ].join(" ").toLowerCase();
      return haystack.includes(term);
    });
  }, [entries, search]);

  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
        Loading audit log…
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border border-rose-500/30 p-6 text-sm">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-foreground mb-1">Could not load audit log</p>
            <p className="text-muted-foreground">{error}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 text-xs text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!entries || filtered.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        {entries && entries.length === 0
          ? "No RBAC config changes have been recorded yet. Edit a permission or create a custom role to start the audit trail."
          : "No entries match the current filters."}
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <ul className="divide-y divide-border/50">
        {filtered.map((entry) => (
          <HistoryRow
            key={entry.id}
            entry={entry}
            expanded={entry.id === expandedId}
            onToggle={() => onToggle(entry.id)}
          />
        ))}
      </ul>
    </div>
  );
}

function HistoryRow({
  entry, expanded, onToggle,
}: {
  entry: AuditEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const verb = ACTION_LABELS[entry.action];
  const tone = ACTION_TONES[entry.action];

  // Build the headline. Examples:
  //   "admin@example.com granted data.sync to viewer"
  //   "admin@example.com revoked dashboards.write from analyst"
  //   "admin@example.com cleared override on viewer / data.sync"
  //   "admin@example.com created role data-team"
  //   "admin@example.com deleted role data-team"
  const actor = entry.actor_email || entry.actor_user_id || "unknown";
  const headlineRest = (() => {
    if (entry.action === "grant" && entry.target_permission)
      return <>{entry.target_permission} to <span className="font-mono-deck">{entry.target_role}</span></>;
    if (entry.action === "revoke" && entry.target_permission)
      return <>{entry.target_permission} from <span className="font-mono-deck">{entry.target_role}</span></>;
    if (entry.action === "clear" && entry.target_permission)
      return <><span className="font-mono-deck">{entry.target_role}</span> / {entry.target_permission}</>;
    return <span className="font-mono-deck">{entry.target_role}</span>;
  })();

  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "w-full text-left px-4 py-2.5 hover:bg-secondary/30 flex items-start gap-3 text-xs",
          expanded && "bg-secondary/30",
        )}
      >
        <span className="mt-0.5 text-muted-foreground">
          {expanded
            ? <ChevronDown className="w-3 h-3" />
            : <ChevronRight className="w-3 h-3" />}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-1.5 flex-wrap">
            <span className="font-mono-deck text-foreground">{actor}</span>
            <span className={cn("font-mono-deck", tone)}>{verb}</span>
            <span className="text-foreground">{headlineRest}</span>
            {entry.actor_role && (
              <span className="text-[10px] font-mono-deck bg-secondary text-muted-foreground px-1.5 py-0.5 rounded">
                as {entry.actor_role}
              </span>
            )}
          </div>
          <div className="text-muted-foreground mt-0.5 flex items-center gap-2">
            <span title={entry.occurred_at}>{formatRelativeTime(entry.occurred_at)}</span>
            {entry.note && (
              <span className="italic">— {entry.note}</span>
            )}
          </div>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-3 pl-10 space-y-2 text-[11px]">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[10px] font-mono-deck uppercase tracking-wide text-muted-foreground mb-1">
                Before
              </div>
              <pre className="bg-background/50 border border-border rounded p-2 overflow-x-auto text-foreground/80">
                {entry.before_state
                  ? JSON.stringify(entry.before_state, null, 2)
                  : <span className="text-muted-foreground italic">none</span>}
              </pre>
            </div>
            <div>
              <div className="text-[10px] font-mono-deck uppercase tracking-wide text-muted-foreground mb-1">
                After
              </div>
              <pre className="bg-background/50 border border-border rounded p-2 overflow-x-auto text-foreground/80">
                {entry.after_state
                  ? JSON.stringify(entry.after_state, null, 2)
                  : <span className="text-muted-foreground italic">none</span>}
              </pre>
            </div>
          </div>
          <div className="text-muted-foreground">
            <span className="font-mono-deck text-[10px] uppercase tracking-wide">Audit ID:</span>{" "}
            <span className="font-mono-deck text-foreground">#{entry.id}</span>
          </div>
        </div>
      )}
    </li>
  );
}


// ── Users view ───────────────────────────────────────────────────────

function UsersView({
  users, loading, error, roleFilter, search, expandedUserId, onToggleUser, onRetry,
}: {
  users: UserEntry[] | null;
  loading: boolean;
  error: string | null;
  roleFilter: Role | "all";
  search: string;
  expandedUserId: string | null;
  onToggleUser: (id: string) => void;
  onRetry: () => void;
}) {
  const filtered = useMemo(() => {
    if (!users) return [] as UserEntry[];
    const term = search.trim().toLowerCase();
    return users.filter((u) => {
      if (roleFilter !== "all" && u.role !== roleFilter) return false;
      if (term && !u.email.toLowerCase().includes(term)) return false;
      return true;
    });
  }, [users, roleFilter, search]);

  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
        Loading users…
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg border border-rose-500/30 p-6 text-sm">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-foreground mb-1">Could not load users</p>
            <p className="text-muted-foreground">{error}</p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 text-xs text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!users || filtered.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        {users && users.length === 0
          ? "No users found."
          : "No users match the current filters."}
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-secondary/50">
            <tr className="border-b border-border">
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Email
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Name
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Role
              </th>
              <th className="text-right px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Permissions
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Status
              </th>
              <th className="text-left px-3 py-2 font-mono-deck uppercase tracking-wide text-[10px] text-muted-foreground">
                Last activity
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <UserRow
                key={u.id}
                user={u}
                expanded={u.id === expandedUserId}
                onToggle={() => onToggleUser(u.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UserRow({
  user, expanded, onToggle,
}: {
  user: UserEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={cn(
          "border-b border-border/50 hover:bg-secondary/30 cursor-pointer",
          expanded && "bg-secondary/30",
        )}
        onClick={onToggle}
      >
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onToggle(); }}
              className="text-muted-foreground hover:text-foreground"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded
                ? <ChevronDown className="w-3 h-3" />
                : <ChevronRight className="w-3 h-3" />}
            </button>
            <span className="font-mono-deck text-foreground">{user.email}</span>
          </div>
        </td>
        <td className="px-3 py-2 text-muted-foreground">
          {user.name || <span className="text-border">—</span>}
        </td>
        <td className="px-3 py-2">
          <RoleBadge role={user.role} />
        </td>
        <td className="text-right px-3 py-2 font-mono-deck text-muted-foreground">
          {user.permissions.length}
        </td>
        <td className="px-3 py-2">
          {user.is_active ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-emerald-400">
              <CheckCircle2 className="w-2.5 h-2.5" />
              active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono-deck text-muted-foreground">
              <XCircle className="w-2.5 h-2.5" />
              inactive
            </span>
          )}
        </td>
        <td className="px-3 py-2 text-muted-foreground">
          {user.last_activity_at ? (
            <span title={`${user.last_activity_route ?? ""} at ${user.last_activity_at}`}>
              {formatRelativeTime(user.last_activity_at)}
            </span>
          ) : (
            <span className="text-border" title="No allow decisions in the last 30 days">
              —
            </span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-border/50 bg-background/40">
          <td colSpan={6} className="px-3 py-3">
            <div className="px-6 space-y-3">
              {/* Last activity detail */}
              {user.last_activity_at && user.last_activity_route && (
                <div className="text-[11px] text-muted-foreground">
                  <span className="font-mono-deck uppercase tracking-wide">Last activity:</span>{" "}
                  <span className="font-mono-deck text-foreground">{user.last_activity_route}</span>{" "}
                  · {formatRelativeTime(user.last_activity_at)}
                  <span className="text-border"> · </span>
                  <span title={user.last_activity_at}>{user.last_activity_at}</span>
                </div>
              )}
              {/* Permission chips */}
              <div>
                <div className="text-[10px] font-mono-deck uppercase tracking-wide text-muted-foreground mb-1.5">
                  Permissions held ({user.permissions.length})
                </div>
                {user.permissions.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground italic">
                    This role grants no permissions. (Possible role typo in the database.)
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {user.permissions.map((p) => (
                      <span
                        key={p}
                        className="text-[10px] font-mono-deck bg-secondary text-foreground px-1.5 py-0.5 rounded"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function RoleBadge({ role }: { role: string }) {
  const tone =
    role === "superadmin" ? "bg-rose-500/10 text-rose-400" :
    role === "admin" ? "bg-amber-500/10 text-amber-400" :
    role === "analyst" ? "bg-blue-500/10 text-blue-400" :
    role === "viewer" ? "bg-emerald-500/10 text-emerald-400" :
    "bg-secondary text-muted-foreground";
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono-deck",
      tone,
    )}>
      <User className="w-2.5 h-2.5" />
      {role}
    </span>
  );
}

// ── Small components ─────────────────────────────────────────────────

function MethodPill({ method }: { method: string }) {
  const tone =
    method === "GET" ? "bg-emerald-500/10 text-emerald-400" :
    method === "POST" ? "bg-blue-500/10 text-blue-400" :
    method === "PATCH" || method === "PUT" ? "bg-amber-500/10 text-amber-400" :
    method === "DELETE" ? "bg-rose-500/10 text-rose-400" :
    "bg-secondary text-muted-foreground";
  return (
    <span className={cn(
      "inline-block px-1.5 py-0.5 rounded text-[10px] font-mono-deck",
      tone,
    )}>
      {method}
    </span>
  );
}

function DefaultBadge() {
  return (
    <span
      className="inline-block px-1.5 py-0.5 text-[10px] font-mono-deck bg-amber-500/10 text-amber-400 rounded"
      title="Legacy default — this plugin hasn't declared a `permissions:` block in its manifest. Permission falls back to the method-derived global (plugins.read or plugins.configure). Plugin author should add `permissions:` to plugin.yaml; see docs/contributing-a-plugin.md."
    >
      legacy
    </span>
  );
}

function PluginBadge() {
  return (
    <span
      className="inline-block px-1.5 py-0.5 text-[10px] font-mono-deck bg-secondary text-muted-foreground rounded"
      title="Plugin route, permission set by plugin author or platform"
    >
      plugin
    </span>
  );
}

// ── Resource defaults (B248 v0.9.10.7) ───────────────────────────────

const RESOURCE_TYPES = ["dashboard", "fusion", "connection", "share", "plugin"] as const;
type ResourceType = (typeof RESOURCE_TYPES)[number];

interface DefaultPolicyRow {
  resource_type: ResourceType;
  policy: "allow" | "deny";
  loading: boolean;
  error: string | null;
}

function ResourceDefaultsView({ canEdit }: { canEdit: boolean }) {
  const [rows, setRows] = useState<DefaultPolicyRow[]>(() =>
    RESOURCE_TYPES.map((rt) => ({ resource_type: rt, policy: "allow", loading: true, error: null })),
  );
  const [confirmFlip, setConfirmFlip] = useState<{ rt: ResourceType; next: "allow" | "deny" } | null>(null);

  const load = useCallback(async () => {
    const next = await Promise.all(
      RESOURCE_TYPES.map(async (rt): Promise<DefaultPolicyRow> => {
        try {
          const res = await apiFetch(`/api/resource-acls/defaults/${rt}`);
          if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
          const body = (await res.json()) as { policy: "allow" | "deny" };
          return { resource_type: rt, policy: body.policy, loading: false, error: null };
        } catch (e) {
          return {
            resource_type: rt,
            policy: "allow",
            loading: false,
            error: e instanceof Error ? e.message : String(e),
          };
        }
      }),
    );
    setRows(next);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const applyFlip = async (rt: ResourceType, policy: "allow" | "deny") => {
    setRows((prev) => prev.map((r) => (r.resource_type === rt ? { ...r, loading: true, error: null } : r)));
    try {
      const res = await apiFetch(`/api/resource-acls/defaults/${rt}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `${res.status} ${res.statusText}`);
      }
      setRows((prev) => prev.map((r) => (r.resource_type === rt ? { ...r, policy, loading: false } : r)));
    } catch (e) {
      setRows((prev) => prev.map((r) =>
        r.resource_type === rt
          ? { ...r, loading: false, error: e instanceof Error ? e.message : String(e) }
          : r,
      ));
    }
  };

  const onToggle = (row: DefaultPolicyRow) => {
    if (!canEdit) return;
    const next = row.policy === "allow" ? "deny" : "allow";
    if (next === "deny") {
      setConfirmFlip({ rt: row.resource_type, next });
    } else {
      void applyFlip(row.resource_type, next);
    }
  };

  return (
    <div className="bg-card rounded-lg border border-border p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-sm text-foreground">Resource defaults</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
            Per-resource-type default policy. <span className="font-mono-deck">allow</span> means
            holding the role permission is enough; <span className="font-mono-deck">deny</span>{" "}
            means access requires an explicit grant on the specific resource (or the user is the
            owner). Owners always retain implicit access.
          </p>
        </div>
      </div>

      <table className="w-full text-xs">
        <thead className="text-muted-foreground border-b border-border">
          <tr>
            <th className="text-left font-normal py-2">Resource type</th>
            <th className="text-left font-normal py-2">Default policy</th>
            <th className="text-left font-normal py-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.resource_type} className="border-b border-border/40">
              <td className="py-2 font-mono-deck">{row.resource_type}</td>
              <td className="py-2">
                <span
                  className={cn(
                    "inline-block px-2 py-0.5 rounded text-[10px] font-mono-deck",
                    row.policy === "allow"
                      ? "bg-green-500/10 text-green-400"
                      : "bg-red-500/10 text-red-400",
                  )}
                >
                  {row.policy}
                </span>
              </td>
              <td className="py-2">
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => onToggle(row)}
                    disabled={row.loading}
                    className="text-xs px-2 py-1 rounded border border-border hover:bg-secondary disabled:opacity-50"
                  >
                    {row.loading ? "Saving…" : row.policy === "allow" ? "Switch to deny" : "Switch to allow"}
                  </button>
                )}
                {row.error && (
                  <span className="ml-2 text-[11px] text-red-400">{row.error}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {confirmFlip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setConfirmFlip(null)}>
          <div className="bg-card border border-border rounded-lg p-6 max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-base text-foreground mb-2">
              Switch <span className="font-mono-deck">{confirmFlip.rt}</span> default to deny?
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Users without an explicit ACL grant on a {confirmFlip.rt} will lose access — even if
              their role normally holds the relevant permission. Owners retain implicit access.
              You can reverse this at any time.
            </p>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={() => setConfirmFlip(null)}
                className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  void applyFlip(confirmFlip.rt, confirmFlip.next);
                  setConfirmFlip(null);
                }}
                className="h-8 px-3 rounded-md bg-red-500 text-xs text-white hover:bg-red-600"
              >
                Switch to deny
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
