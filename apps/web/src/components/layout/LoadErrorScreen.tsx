/**
 * v1.0.2 — recoverable error screen shown when the plugin-component
 * loader fails terminally.
 *
 * Replaces the previous "render anyway" fallback in AuthGate when the
 * /api/plugins fetch couldn't be salvaged by the loader's retry loop.
 * That fallback dropped the user into a dashboard with no widget registry,
 * which looked indistinguishable from "the platform is broken." This
 * screen gives them a clear signal *and* a one-click reload, so a
 * transient API hiccup is recoverable in two seconds instead of becoming
 * a "refresh-and-relogin" loop.
 *
 * Intentionally minimal — no nav, no sidebar, no plugin bundles. Just
 * a card with the failure reason and a reload button.
 */
import { AlertTriangle, RotateCw, Loader2 } from "lucide-react";
import { useState } from "react";
import SidebarLogo from "./SidebarLogo";

interface LoadErrorScreenProps {
  /**
   * Operator-readable reason string from `notifyPluginLoaderFailed()`.
   * E.g. `"Server returned 503 after 3 attempts: Database unavailable"`.
   * Shown verbatim under the headline so the user (or whoever they
   * forward the screenshot to) has context for support.
   */
  reason: string | null;
  /**
   * Click handler for the Reload button. Typically clears the loader's
   * failure state, re-runs the loader, and toggles plugin-loaded back to
   * true on success. Caller decides whether to do an in-app retry or a
   * full `window.location.reload()`.
   */
  onReload: () => Promise<void> | void;
}

export default function LoadErrorScreen({ reason, onReload }: LoadErrorScreenProps) {
  const [reloading, setReloading] = useState(false);

  const handleReload = async () => {
    if (reloading) return;
    setReloading(true);
    try {
      await onReload();
    } finally {
      // Whether the retry succeeds or not, drop the spinner — a successful
      // retry unmounts this screen anyway, and a failure should let the
      // user click again.
      setReloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center mb-8">
          <SidebarLogo collapsed={false} />
        </div>

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="flex flex-col items-center text-center space-y-3">
            <AlertTriangle className="w-8 h-8 text-amber-400" />
            <div className="space-y-1">
              <h2 className="font-display text-base text-foreground">
                Couldn&apos;t load plugins
              </h2>
              <p className="text-xs text-muted-foreground">
                The platform couldn&apos;t fetch the list of installed plugins.
                This is usually transient — try reloading.
              </p>
            </div>
          </div>

          {reason && (
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
                Details
              </div>
              <code className="text-[11px] text-foreground break-all block leading-relaxed">
                {reason}
              </code>
            </div>
          )}

          <button
            onClick={handleReload}
            disabled={reloading}
            className="w-full h-10 rounded-lg bg-primary text-primary-foreground text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {reloading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Reloading…
              </>
            ) : (
              <>
                <RotateCw className="w-4 h-4" />
                Reload
              </>
            )}
          </button>

          <p className="text-[11px] text-muted-foreground text-center">
            If this keeps happening, the API may be down or the server may
            need to be restarted.
          </p>
        </div>
      </div>
    </div>
  );
}
