/**
 * B305 (v0.10.0.6) — invite-time + edit-time plugin allowlist picker.
 *
 * Two-mode controlled component:
 *   "all"      → user sees every installed plugin (default; backward-compat
 *                with pre-B305 invite flow).
 *   "specific" → user sees only the ticked slugs (plus utilities, which
 *                bypass the filter regardless and are NOT shown in the
 *                checkbox list — they're infrastructure, not user-facing
 *                nav).
 *
 * Used by:
 *   - UsersPanel invite modal (hidden when role is admin/superadmin)
 *   - UsersPanel edit-plugin-access modal
 *   - Install-success grant banner (Phase 3) — re-uses the checkbox shape
 *
 * Source of truth for available plugins: `/api/plugins`, filtered to
 * `type !== "utility"`. The server already filters this endpoint per
 * current user, so a superadmin operator sees the full set (correct
 * for invite UX).
 */
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export interface PluginAccessValue {
  mode: "all" | "specific";
  plugin_ids: string[];
}

interface InstalledPlugin {
  id: string;
  display_name?: string | null;
  type?: string | null;
}

interface Props {
  value: PluginAccessValue;
  onChange: (next: PluginAccessValue) => void;
  /**
   * When true, render a compact in-form label ("Plugin access"). When
   * false (modal context), the parent renders its own heading.
   */
  withInlineLabel?: boolean;
  /**
   * Optional pre-fetched plugin list. When provided, the picker skips
   * the /api/plugins fetch. Used by the install-success banner where
   * the parent already has the data.
   */
  installedPlugins?: InstalledPlugin[];
  disabled?: boolean;
}

export default function PluginAccessPicker({
  value,
  onChange,
  withInlineLabel = false,
  installedPlugins,
  disabled = false,
}: Props) {
  const [plugins, setPlugins] = useState<InstalledPlugin[]>(installedPlugins || []);
  const [loading, setLoading] = useState(!installedPlugins);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (installedPlugins) {
      setPlugins(installedPlugins);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiFetch("/api/plugins")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const all: InstalledPlugin[] = data.plugins || [];
        // Hide utilities — they're always-visible infrastructure.
        setPlugins(all.filter((p) => p.type !== "utility"));
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || "Failed to load plugins");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [installedPlugins]);

  const ticked = new Set(value.plugin_ids);

  function setMode(mode: "all" | "specific") {
    if (mode === "all") {
      onChange({ mode: "all", plugin_ids: [] });
    } else {
      // Switching to specific keeps the existing ticks; if none, default
      // to empty (operator must tick at least one — submit-side handles).
      onChange({ mode: "specific", plugin_ids: value.plugin_ids });
    }
  }

  function toggle(id: string) {
    if (value.mode !== "specific") return;
    const next = new Set(ticked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange({ mode: "specific", plugin_ids: Array.from(next).sort() });
  }

  function tickAll() {
    onChange({
      mode: "specific",
      plugin_ids: plugins.map((p) => p.id).sort(),
    });
  }

  function tickNone() {
    onChange({ mode: "specific", plugin_ids: [] });
  }

  return (
    <div className="space-y-2">
      {withInlineLabel && (
        <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold block">
          Plugin access
        </label>
      )}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer">
          <input
            type="radio"
            name="plugin-access-mode"
            checked={value.mode === "all"}
            onChange={() => setMode("all")}
            disabled={disabled}
            className="accent-primary"
          />
          <span>All plugins</span>
          <span className="text-muted-foreground text-[10px]">
            (default — every installed plugin, including future ones)
          </span>
        </label>
        <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer">
          <input
            type="radio"
            name="plugin-access-mode"
            checked={value.mode === "specific"}
            onChange={() => setMode("specific")}
            disabled={disabled}
            className="accent-primary"
          />
          <span>Specific plugins</span>
          {value.mode === "specific" && (
            <span className="text-muted-foreground text-[10px]">
              ({ticked.size} ticked)
            </span>
          )}
        </label>
      </div>

      {value.mode === "specific" && (
        <div className="ml-5 mt-2 p-3 rounded-md bg-background border border-border space-y-2">
          {loading ? (
            <p className="text-xs text-muted-foreground">Loading plugins...</p>
          ) : error ? (
            <p className="text-xs text-red-400">{error}</p>
          ) : plugins.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No data plugins installed. (Utility plugins are always visible.)
            </p>
          ) : (
            <>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <button
                  type="button"
                  onClick={tickAll}
                  disabled={disabled}
                  className="hover:text-foreground"
                >
                  Select all
                </button>
                <span>·</span>
                <button
                  type="button"
                  onClick={tickNone}
                  disabled={disabled}
                  className="hover:text-foreground"
                >
                  Clear
                </button>
              </div>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {plugins.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 text-xs text-foreground cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={ticked.has(p.id)}
                      onChange={() => toggle(p.id)}
                      disabled={disabled}
                      className="accent-primary"
                    />
                    <span className="truncate">{p.display_name || p.id}</span>
                    <span className="text-muted-foreground font-mono-deck text-[10px] truncate">
                      {p.id}
                    </span>
                  </label>
                ))}
              </div>
              <p className="text-[10px] text-muted-foreground pt-1 border-t border-border">
                Utility plugins (ClickHouse, Postgres, etc.) are always visible
                regardless of this list.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
