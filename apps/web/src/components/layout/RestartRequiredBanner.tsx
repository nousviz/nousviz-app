import { apiFetch } from "@/lib/api";
import { useState, useEffect, useCallback } from "react";
import { RefreshCw, X } from "lucide-react";

const STORAGE_KEY = "nousviz_restart_required";
const NAMES_KEY = "nousviz_restart_plugin_names";
const SET_AT_KEY = "nousviz_restart_set_at";
const POLL_INTERVAL_MS = 10_000;

export default function RestartRequiredBanner() {
  const [visible, setVisible] = useState(
    () => localStorage.getItem(STORAGE_KEY) === "true"
  );
  const [pluginNames, setPluginNames] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem(NAMES_KEY) || "[]"); }
    catch { return []; }
  });

  const dismiss = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(NAMES_KEY);
    localStorage.removeItem(SET_AT_KEY);
    setVisible(false);
  }, []);

  // On mount: two dismissal conditions —
  // 1. The server has already restarted since the banner was set (startup_time > set_at).
  // 2. All named plugins are currently installed (banner is stale from a prior session).
  useEffect(() => {
    if (!visible) return;

    const setAt = localStorage.getItem(SET_AT_KEY);

    apiFetch("/api/health", { cache: "no-store" })
      .then(r => r.json())
      .then(data => {
        // If the server started after the banner was set, the restart already happened.
        // Also dismiss if there's no set_at (legacy banner from before this fix was deployed).
        if (data.startup_time && (!setAt || new Date(data.startup_time) > new Date(setAt))) {
          dismiss();
          return;
        }

        // Otherwise check if all named plugins are already installed (banner is stale).
        apiFetch("/api/plugins", { cache: "no-store" })
          .then(r => r.json())
          .then(pluginData => {
            const installedSlugs = new Set<string>(
              (pluginData.plugins || []).map((p: { id: string }) => p.id)
            );
            const pendingNames = pluginNames.filter(name => {
              const slug = name.toLowerCase().replace(/\s+/g, "-");
              return !installedSlugs.has(slug);
            });
            if (pendingNames.length === 0) {
              dismiss();
            } else if (pendingNames.length !== pluginNames.length) {
              localStorage.setItem(NAMES_KEY, JSON.stringify(pendingNames));
              setPluginNames(pendingNames);
            }
          })
          .catch(() => {});
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll /api/health — clear banner once the server has restarted.
  // Strategy: record the server's startup_time on first poll; if it ever
  // changes (new process), the server was restarted and routes are gone.
  useEffect(() => {
    if (!visible) return;

    let baseStartup: string | null = null;
    let serverWasDown = false;

    const check = () => {
      apiFetch("/api/health", { cache: "no-store" })
        .then(r => r.json())
        .then(data => {
          const startup: string | undefined = data.startup_time ?? data.started_at;
          if (startup) {
            if (baseStartup === null) {
              baseStartup = startup;
            } else if (startup !== baseStartup) {
              // startup_time changed → new process → plugin routes are gone
              dismiss();
            }
          } else {
            // Health endpoint has no startup_time — fall back to: if the
            // server went down and came back up, treat that as a restart.
            if (serverWasDown) {
              dismiss();
            }
          }
          serverWasDown = false;
        })
        .catch(() => {
          serverWasDown = true;
        });
    };

    check();
    const id = setInterval(check, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [visible, dismiss]);

  if (!visible) return null;

  const nameText = pluginNames.length > 0
    ? pluginNames.join(", ")
    : "The plugin";

  const message = pluginNames.length === 1
    ? `${nameText} was removed. Its API routes will stop working after the next restart.`
    : pluginNames.length > 1
    ? `${nameText} were removed. Their API routes will stop working after the next restart.`
    : "A plugin was removed. Its API routes will stop working after the next restart.";

  return (
    <div className="bg-orange-500/10 border-b border-orange-500/20 px-4 py-2 text-sm text-orange-400 flex items-center gap-2 shrink-0">
      <RefreshCw className="w-4 h-4 shrink-0" />
      <span className="flex-1">{message}</span>
      <button
        onClick={dismiss}
        className="ml-2 text-orange-400/60 hover:text-orange-400 transition-colors"
        title="Dismiss — routes remain active until restart"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
