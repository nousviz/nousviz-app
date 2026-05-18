/**
 * B305 (v0.10.0.6) — install-success grant nudge.
 *
 * When an operator installs a new plugin, this banner surfaces any
 * users whose `plugin_access.mode === 'specific'` and whose allowlist
 * does NOT yet contain the new slug. The operator can tick the users
 * to grant + save in one click, preventing the silent visibility gap
 * where a viewer never sees the freshly-installed plugin because
 * nobody remembered to grant them.
 *
 * Renders nothing if there are no restricted users — the common case
 * for a fresh install.
 */
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Users, Check } from "lucide-react";

interface RestrictedUser {
  user_id: string;
  email: string;
  role: string;
}

interface Props {
  /**
   * The slug of the newly-installed plugin. Used as the
   * `exclude_slug` query param: the banner surfaces users whose
   * allowlist does NOT already include this slug.
   */
  pluginSlug: string;
}

export default function RestrictedUsersGrantBanner({ pluginSlug }: Props) {
  const [users, setUsers] = useState<RestrictedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [perUserStatus, setPerUserStatus] = useState<Record<string, "ok" | "err">>({});
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch(
      `/api/auth/users/with-restricted-plugin-access?exclude_slug=${encodeURIComponent(pluginSlug)}`,
    )
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data?.users)) {
          setUsers(data.users);
        } else {
          setUsers([]);
        }
        setLoading(false);
      })
      .catch((e) => {
        setError(e?.message || "Failed to load");
        setLoading(false);
      });
  }, [pluginSlug]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (loading) return null;
  if (error) {
    return (
      <div className="mt-3 flex items-start gap-3 px-3 py-2.5 rounded-md bg-amber-500/5 border border-amber-500/20 text-xs text-amber-400">
        <span>Could not check restricted-user access: {error}</span>
      </div>
    );
  }
  if (users.length === 0) return null;

  function toggle(id: string) {
    const next = new Set(picked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  }

  function tickAll() {
    setPicked(new Set(users.map((u) => u.user_id)));
  }

  function tickNone() {
    setPicked(new Set());
  }

  async function grantToOne(userId: string): Promise<boolean> {
    try {
      // Fetch the user's current allowlist so we don't overwrite their
      // existing slugs — we ADD the new slug to the set.
      const cur = await apiFetch(`/api/auth/users/${userId}/plugin-access`);
      const data = await cur.json();
      if (!cur.ok) return false;
      const current: string[] = data.plugin_ids || [];
      const next = Array.from(new Set([...current, pluginSlug])).sort();
      const res = await apiFetch(`/api/auth/users/${userId}/plugin-access`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "specific", plugin_ids: next }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async function grantTicked() {
    if (picked.size === 0) return;
    setSaving(true);
    const status: Record<string, "ok" | "err"> = {};
    // Run in parallel — independent writes.
    await Promise.all(
      Array.from(picked).map(async (id) => {
        status[id] = (await grantToOne(id)) ? "ok" : "err";
      }),
    );
    setPerUserStatus(status);
    setSaving(false);
    const anySuccess = Object.values(status).some((v) => v === "ok");
    if (anySuccess) {
      // Re-fetch to reflect new state. If everyone succeeded, the
      // banner naturally disappears.
      setDone(true);
      reload();
      setPicked(new Set());
    }
  }

  return (
    <div className="mt-3 px-3 py-3 rounded-md bg-amber-500/5 border border-amber-500/20 text-xs">
      <div className="flex items-start gap-2 text-amber-400">
        <Users className="w-4 h-4 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-foreground">
            {users.length} user{users.length === 1 ? "" : "s"} ha
            {users.length === 1 ? "s" : "ve"} restricted plugin access — they can't see this
            plugin yet.
          </p>
          <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
            <button type="button" onClick={tickAll} className="hover:text-foreground">
              Select all
            </button>
            <span>·</span>
            <button type="button" onClick={tickNone} className="hover:text-foreground">
              Clear
            </button>
          </div>
          <ul className="mt-2 space-y-1">
            {users.map((u) => (
              <li key={u.user_id} className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-foreground cursor-pointer flex-1">
                  <input
                    type="checkbox"
                    checked={picked.has(u.user_id)}
                    onChange={() => toggle(u.user_id)}
                    disabled={saving}
                    className="accent-primary"
                  />
                  <span className="truncate">{u.email}</span>
                  <span className="text-muted-foreground text-[10px]">({u.role})</span>
                </label>
                {perUserStatus[u.user_id] === "ok" && (
                  <Check className="w-3.5 h-3.5 text-green-400 shrink-0" />
                )}
                {perUserStatus[u.user_id] === "err" && (
                  <span className="text-red-400 text-[10px] shrink-0">failed</span>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={grantTicked}
              disabled={saving || picked.size === 0}
              className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? "Granting..." : `Grant access (${picked.size})`}
            </button>
            {done && (
              <span className="text-[10px] text-muted-foreground">
                {Object.values(perUserStatus).filter((v) => v === "ok").length} granted
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
