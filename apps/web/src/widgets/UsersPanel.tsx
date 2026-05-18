import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import { UserPlus, Copy, Check, Trash2, Shield, ChevronDown, UserCheck, Puzzle, X } from "lucide-react";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import PluginAccessPicker, { PluginAccessValue } from "@/widgets/PluginAccessPicker";

const BUILTIN_ROLE_RANK: Record<string, number> = {
  viewer: 1,
  analyst: 2,
  admin: 3,
  superadmin: 4,
};

function rank(role: string | null | undefined): number {
  return role ? (BUILTIN_ROLE_RANK[role] ?? 0) : 0;
}

interface PluginAccessSummary {
  mode: "all" | "specific";
  count: number;
  total: number;
  unrestricted_by_role: boolean;
}

interface User {
  id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  last_seen_at: string | null;
  updated_at: string | null;
  created_at: string;
  // B305 (v0.10.0.6): batched plugin allowlist summary.
  plugin_access_summary?: PluginAccessSummary;
}

function onlineStatus(lastSeen: string | null): "online" | "away" | "offline" {
  if (!lastSeen) return "offline";
  const diff = Date.now() - new Date(lastSeen).getTime();
  if (diff < 5 * 60_000) return "online";
  if (diff < 30 * 60_000) return "away";
  return "offline";
}

const STATUS_DOT: Record<string, string> = {
  online: "bg-green-400",
  away: "bg-yellow-400",
  offline: "bg-muted-foreground/30",
};

interface Invite {
  id: string;
  email: string;
  role: string;
  inviter_name: string | null;
  inviter_email: string | null;
  expires_at: string;
  used_at: string | null;
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  superadmin: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  admin: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  analyst: "bg-green-500/10 text-green-400 border-green-500/30",
  viewer: "bg-secondary text-muted-foreground border-border",
};

async function startImpersonation(targetUserId: string): Promise<void> {
  const r = await apiFetch(`/api/auth/impersonate/${targetUserId}`, { method: "POST" });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    const detail = data?.detail;
    const message = typeof detail === "string"
      ? detail
      : (detail?.message ?? "Failed to start impersonation");
    throw new Error(message);
  }
  // B254 (v0.9.10.0.5): the response no longer carries a token — the
  // server set the impersonation flags on our existing session. We
  // discard the response body and just reload to root so /api/auth/me
  // is re-fetched and the impersonation banner appears.
  await r.json().catch(() => ({}));
  window.location.href = "/";
}


export default function UsersPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  // B236 (v0.9.10.0): impersonation needs actor-vs-target rank comparison.
  // The actor is the real authenticated user (`user`), not the effective.
  // (When already impersonating, the Impersonate button on rows is hidden
  // anyway — the backend rejects with 409 if you try, but the UI hides
  // the button entirely to avoid confusion.)
  const { user: actor, impersonating } = useCurrentUser();
  const [impersonatingTarget, setImpersonatingTarget] = useState<string | null>(null);
  const [impersonateError, setImpersonateError] = useState<string | null>(null);

  // Invite form
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("analyst");
  const [invitePluginAccess, setInvitePluginAccess] = useState<PluginAccessValue>({
    mode: "all",
    plugin_ids: [],
  });
  const [inviting, setInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{ url?: string; sent?: boolean; error?: string; emailError?: string } | null>(null);
  const [copiedUrl, setCopiedUrl] = useState(false);

  // B305 (v0.10.0.6): per-user plugin-access edit modal state.
  const [editingAccess, setEditingAccess] = useState<{
    user: User;
    value: PluginAccessValue;
    loading: boolean;
    saving: boolean;
    error: string | null;
  } | null>(null);

  const [accessDenied, setAccessDenied] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiFetch("/api/auth/users").then(r => {
        if (r.status === 403) { setAccessDenied(true); return { users: [] }; }
        return r.json();
      }).catch(() => ({ users: [] })),
      apiFetch("/api/auth/users/invites").then(r => r.json()).catch(() => ({ invites: [] })),
    ]).then(([u, i]) => {
      setUsers(u.users || []);
      setInvites((i.invites || []).filter((inv: Invite) => !inv.used_at));
      setLoading(false);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleInvite() {
    setInviting(true);
    setInviteResult(null);
    try {
      // B305: only send plugin_access when role is restrictable AND the
      // operator picked "specific". For "all" we omit the field so the
      // server treats the invite as backward-compat (no ACL rows).
      const isAdminRole = inviteRole === "admin" || inviteRole === "superadmin";
      const body: Record<string, unknown> = { email: inviteEmail, role: inviteRole };
      if (!isAdminRole && invitePluginAccess.mode === "specific" && invitePluginAccess.plugin_ids.length > 0) {
        body.plugin_access = invitePluginAccess;
      }
      const res = await apiFetch("/api/auth/users/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setInviteResult({ error: data.detail || "Failed to invite." });
      } else {
        setInviteResult({ url: data.invite_url, sent: data.email_sent, emailError: data.email_error });
        setInviteEmail("");
        setInvitePluginAccess({ mode: "all", plugin_ids: [] });
        load();
      }
    } catch {
      setInviteResult({ error: "Could not connect to server." });
    } finally {
      setInviting(false);
    }
  }

  async function openEditAccess(u: User) {
    setEditingAccess({
      user: u,
      value: { mode: "all", plugin_ids: [] },
      loading: true,
      saving: false,
      error: null,
    });
    try {
      const res = await apiFetch(`/api/auth/users/${u.id}/plugin-access`);
      const data = await res.json();
      if (!res.ok) {
        setEditingAccess((prev) =>
          prev && prev.user.id === u.id
            ? { ...prev, loading: false, error: data.detail || "Failed to load." }
            : prev,
        );
        return;
      }
      setEditingAccess((prev) =>
        prev && prev.user.id === u.id
          ? {
              ...prev,
              loading: false,
              value: {
                mode: data.mode || "all",
                plugin_ids: data.plugin_ids || [],
              },
            }
          : prev,
      );
    } catch (e) {
      setEditingAccess((prev) =>
        prev && prev.user.id === u.id
          ? { ...prev, loading: false, error: "Could not load plugin access." }
          : prev,
      );
    }
  }

  async function handleSaveAccess() {
    if (!editingAccess) return;
    setEditingAccess({ ...editingAccess, saving: true, error: null });
    try {
      const res = await apiFetch(
        `/api/auth/users/${editingAccess.user.id}/plugin-access`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(editingAccess.value),
        },
      );
      const data = await res.json();
      if (!res.ok) {
        setEditingAccess({
          ...editingAccess,
          saving: false,
          error: data.detail || "Failed to save.",
        });
        return;
      }
      setEditingAccess(null);
      load();
    } catch {
      setEditingAccess({
        ...editingAccess,
        saving: false,
        error: "Could not connect to server.",
      });
    }
  }

  async function handleRevokeInvite(id: string) {
    await apiFetch(`/api/auth/users/invite/${id}`, { method: "DELETE" });
    load();
  }

  async function handleRoleChange(userId: string, newRole: string) {
    await apiFetch(`/api/auth/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: newRole }),
    });
    load();
  }

  async function handleDeactivate(userId: string) {
    if (!confirm("Deactivate this user? They won't be able to log in.")) return;
    const res = await apiFetch(`/api/auth/users/${userId}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(data.detail || "Failed to deactivate.");
      return;
    }
    load();
  }

  async function handleReactivate(userId: string) {
    await apiFetch(`/api/auth/users/${userId}/reactivate`, { method: "POST" });
    load();
  }

  if (loading) return <p className="text-sm text-muted-foreground py-4">Loading users...</p>;

  if (accessDenied) return (
    <div className="py-6 text-center">
      <p className="text-sm text-muted-foreground">Admin access required to manage users.</p>
      <p className="text-xs text-muted-foreground mt-1">Ask an admin or superadmin to manage user accounts.</p>
    </div>
  );

  const activeUsers = users.filter(u => u.is_active);
  const inactiveUsers = users.filter(u => !u.is_active);

  return (
    <div className="space-y-6">
      {/* Invite form */}
      <div className="bg-secondary/30 rounded-lg border border-border p-4">
        <h4 className="text-sm font-display text-foreground mb-3 flex items-center gap-2">
          <UserPlus className="w-4 h-4" /> Invite a User
        </h4>
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Email</label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="user@example.com"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div className="w-32">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Role</label>
            <div className="relative">
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full h-9 px-3 pr-8 rounded-md bg-background border border-border text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
            </div>
          </div>
          <button
            onClick={handleInvite}
            disabled={inviting || !inviteEmail}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-2 shrink-0"
          >
            {inviting ? "Sending..." : "Send Invite"}
          </button>
        </div>

        {/* B305: invite-time plugin allowlist picker. Hidden for admin
            roles — admins are unrestricted by design. */}
        {inviteRole !== "admin" && inviteRole !== "superadmin" && (
          <div className="mt-3 pt-3 border-t border-border">
            <PluginAccessPicker
              value={invitePluginAccess}
              onChange={setInvitePluginAccess}
              withInlineLabel
            />
          </div>
        )}

        {inviteResult && (
          <div className={cn("mt-3 px-3 py-2 rounded-md text-xs", inviteResult.error ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400")}>
            {inviteResult.error ? (
              inviteResult.error
            ) : inviteResult.sent ? (
              "Invitation email sent!"
            ) : inviteResult.url ? (
              <div className="space-y-1">
                <p>{inviteResult.emailError || "Email could not be sent"} — copy this invite link and send it manually:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-background px-2 py-1 rounded text-foreground font-mono-deck text-[11px] truncate">
                    {inviteResult.url}
                  </code>
                  <button
                    onClick={() => { navigator.clipboard.writeText(inviteResult.url!); setCopiedUrl(true); setTimeout(() => setCopiedUrl(false), 2000); }}
                    className="shrink-0"
                  >
                    {copiedUrl ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {/* Pending invites */}
      {invites.length > 0 && (
        <div>
          <h4 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-2">Pending Invites</h4>
          <div className="space-y-1.5">
            {invites.map(inv => (
              <div key={inv.id} className="flex items-center gap-3 px-3 py-2 rounded-md bg-secondary/20 text-xs">
                <span className="text-foreground flex-1 truncate">{inv.email}</span>
                <span className={cn("px-1.5 py-0.5 rounded-full border text-[10px]", ROLE_COLORS[inv.role] || ROLE_COLORS.viewer)}>
                  {inv.role}
                </span>
                <span className="text-muted-foreground font-mono-deck">Expires {formatRelativeTime(inv.expires_at)}</span>
                <button onClick={() => handleRevokeInvite(inv.id)} className="text-muted-foreground hover:text-red-400 transition-colors" title="Revoke invite">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active users */}
      <div>
        <h4 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-2">
          Users ({activeUsers.length})
        </h4>
        {impersonateError && (
          <p className="text-xs text-rose-400 mb-2">
            Impersonate failed: {impersonateError}
          </p>
        )}
        <div className="space-y-1.5">
          {activeUsers.map(u => (
            <div key={u.id} className="flex items-center gap-3 px-3 py-2.5 rounded-md bg-secondary/20 text-xs">
              <span className={cn("w-2 h-2 rounded-full shrink-0", STATUS_DOT[onlineStatus(u.last_seen_at)])} title={onlineStatus(u.last_seen_at)} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-foreground font-medium truncate">{u.name || u.email}</span>
                  {u.role === "superadmin" && <Shield className="w-3 h-3 text-purple-400 shrink-0" />}
                </div>
                <p className="text-muted-foreground truncate">{u.email}</p>
              </div>
              <span className={cn("px-1.5 py-0.5 rounded-full border text-[10px] shrink-0", ROLE_COLORS[u.role] || ROLE_COLORS.viewer)}>
                {u.role}
              </span>
              {/* B253 (v0.9.10.0.4): show Last Active (last_seen_at —
                  activity heartbeat) instead of Last Login. Sessions are
                  long-lived (default 30 days), so 'last login' was
                  misleading on this view; 'last active' reflects whether
                  the user is actually using the platform. The original
                  last_login is preserved in the tooltip for cases where
                  authentication recency matters. */}
              <span
                className="text-muted-foreground font-mono-deck shrink-0 text-right"
                title={
                  u.last_seen_at
                    ? `Last active: ${u.last_seen_at}` +
                      (u.last_login ? `\nLast login: ${u.last_login}` : "")
                    : u.last_login
                      ? `Never seen active. Last login: ${u.last_login}`
                      : "Never seen active or logged in"
                }
              >
                Last active: {u.last_seen_at ? formatRelativeTime(u.last_seen_at) : "Never"}
              </span>
              {/* B305: plugin-access chip. Admins are unrestricted; show
                  "All" but disable the edit affordance with a tooltip. */}
              {u.plugin_access_summary && (
                <button
                  type="button"
                  onClick={() =>
                    u.plugin_access_summary?.unrestricted_by_role
                      ? undefined
                      : openEditAccess(u)
                  }
                  disabled={u.plugin_access_summary.unrestricted_by_role}
                  title={
                    u.plugin_access_summary.unrestricted_by_role
                      ? "Admins are unrestricted — demote first to limit plugin access."
                      : "Edit plugin access"
                  }
                  className={cn(
                    "shrink-0 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] border",
                    u.plugin_access_summary.unrestricted_by_role
                      ? "bg-secondary text-muted-foreground border-border cursor-not-allowed"
                      : u.plugin_access_summary.mode === "all"
                        ? "bg-secondary text-muted-foreground border-border hover:text-foreground"
                        : "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20",
                  )}
                >
                  <Puzzle className="w-3 h-3" />
                  {u.plugin_access_summary.mode === "all"
                    ? "All plugins"
                    : `${u.plugin_access_summary.count} of ${u.plugin_access_summary.total}`}
                </button>
              )}
              {u.role !== "superadmin" && (
                <div className="flex items-center gap-1 shrink-0">
                  <select
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    className="h-7 px-2 rounded bg-background border border-border text-[10px] text-foreground appearance-none"
                  >
                    <option value="admin">Admin</option>
                    <option value="analyst">Analyst</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  {/* B236 (v0.9.10.0): Impersonate. Visible iff actor outranks
                      target (strict) AND not currently impersonating AND target
                      is not the actor itself. Server also enforces (rank check
                      + already-impersonating guard); the UI mirror is for UX. */}
                  {!impersonating && actor && actor.id !== u.id && rank(actor.role) > rank(u.role) && (
                    <button
                      onClick={async () => {
                        setImpersonatingTarget(u.id);
                        setImpersonateError(null);
                        try {
                          await startImpersonation(u.id);
                          // Page reloads to / on success — control doesn't return here.
                        } catch (err) {
                          setImpersonatingTarget(null);
                          setImpersonateError(err instanceof Error ? err.message : "Failed");
                        }
                      }}
                      disabled={impersonatingTarget === u.id}
                      className="text-muted-foreground hover:text-amber-400 transition-colors disabled:opacity-50"
                      title={`Impersonate ${u.name || u.email} — view the platform as them`}
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button onClick={() => handleDeactivate(u.id)} className="text-muted-foreground hover:text-red-400 transition-colors" title="Deactivate">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* B305: plugin-access edit modal */}
      {editingAccess && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="plugin-access-title"
          onClick={() => !editingAccess.saving && setEditingAccess(null)}
        >
          <div
            className="bg-card border border-border rounded-lg shadow-xl w-full max-w-lg mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <h3 id="plugin-access-title" className="text-sm font-display text-foreground flex items-center gap-2">
                <Puzzle className="w-4 h-4" />
                Plugin access — {editingAccess.user.name || editingAccess.user.email}
              </h3>
              <button
                onClick={() => !editingAccess.saving && setEditingAccess(null)}
                disabled={editingAccess.saving}
                className="text-muted-foreground hover:text-foreground disabled:opacity-50"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="px-4 py-4 space-y-3">
              {editingAccess.loading ? (
                <p className="text-xs text-muted-foreground">Loading current access...</p>
              ) : editingAccess.error ? (
                <p className="text-xs text-red-400">{editingAccess.error}</p>
              ) : (
                <PluginAccessPicker
                  value={editingAccess.value}
                  onChange={(v) => setEditingAccess({ ...editingAccess, value: v })}
                  disabled={editingAccess.saving}
                />
              )}
            </div>
            <div className="px-4 py-3 border-t border-border flex items-center justify-end gap-2">
              <button
                onClick={() => setEditingAccess(null)}
                disabled={editingAccess.saving}
                className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAccess}
                disabled={editingAccess.saving || editingAccess.loading}
                className="h-8 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
              >
                {editingAccess.saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inactive users */}
      {inactiveUsers.length > 0 && (
        <div>
          <h4 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-2">
            Deactivated ({inactiveUsers.length})
          </h4>
          <div className="space-y-1.5">
            {inactiveUsers.map(u => (
              <div key={u.id} className="flex items-center gap-3 px-3 py-2.5 rounded-md bg-secondary/10 text-xs">
                <div className="flex-1 min-w-0">
                  <span className="text-foreground truncate">{u.name || u.email}</span>
                  <p className="text-muted-foreground truncate">{u.email}</p>
                </div>
                <span className="text-muted-foreground font-mono-deck shrink-0" title={u.updated_at || undefined}>
                  Deactivated {formatRelativeTime(u.updated_at)}
                </span>
                <button
                  onClick={() => handleReactivate(u.id)}
                  className="h-7 px-2.5 rounded bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/20 transition-colors shrink-0"
                >
                  Reactivate
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
