/**
 * ImpersonationBanner — sticky bar across the top of the app when the
 * session is impersonating another user.
 *
 * B236 (v0.9.10.0): replaces v0.9.8.4's PreviewBanner. That earlier
 * component showed the actor's frontend-only "view as" preview; this one
 * reflects real server-side impersonation. The actor and target are
 * BOTH shown explicitly (Option B identity) so there's never ambiguity
 * about who's accountable for what.
 *
 * Reads from useCurrentUser():
 *   user (actor) + user.acting_as (target, when impersonating)
 *
 * "Exit" calls POST /api/auth/impersonate/exit, clears the impersonation
 * token, redirects to login (the actor's original session is intact and
 * they can re-login normally — we don't auto-restore it because the
 * server has no way to surface the actor's old token).
 */

import { useEffect, useState } from "react";
import { LogOut, AlertCircle } from "lucide-react";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { apiFetch } from "@/lib/api";

export default function ImpersonationBanner() {
  const { user, impersonating } = useCurrentUser();
  const [exiting, setExiting] = useState(false);
  const [now, setNow] = useState(Date.now());

  // Tick every 10 seconds for the "X minutes remaining" countdown.
  useEffect(() => {
    if (!impersonating) return;
    const id = setInterval(() => setNow(Date.now()), 10_000);
    return () => clearInterval(id);
  }, [impersonating]);

  if (!impersonating || !user || !user.acting_as) return null;

  const target = user.acting_as;
  const actorLabel = user.name || user.email;
  const targetLabel = target.name || target.email;
  // The session's expires_at isn't in the /me response. Display a
  // generic "10-minute window" notice; precise countdown wired in
  // a follow-up if operators need it.

  async function exit() {
    if (exiting) return;
    setExiting(true);
    try {
      await apiFetch("/api/auth/impersonate/exit", { method: "POST" });
    } catch {
      // Best-effort — if the call fails, the next /api/auth/me will
      // still attempt to resolve the actor (the lazy-clear in the
      // middleware will catch any past acting_as_until). Worst case
      // operator clicks Exit again. We deliberately do NOT clear the
      // localStorage token — the actor's session is still valid and
      // we want them returned to their actor identity, not logged out.
    }
    // B254 (v0.9.10.0.5): no token swap. Reload to root so /api/auth/me
    // is re-fetched cleanly; the actor's existing token continues to
    // work and they're back as themselves with no re-login.
    window.location.href = "/";
  }

  // Suppress unused-warning on `now` — the variable triggers the re-render.
  void now;

  return (
    <div className="sticky top-0 z-[55] bg-amber-500/95 text-amber-950 border-b border-amber-700 backdrop-blur-sm">
      <div className="px-4 py-2 flex items-center justify-between gap-4 text-sm">
        <div className="flex items-center gap-2 min-w-0">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <p className="truncate">
            <span className="font-medium">You are {actorLabel}</span>
            <span className="opacity-80">, acting as </span>
            <span className="font-medium">{targetLabel}</span>
            <span className="opacity-80"> ({target.role}).</span>
            <span className="ml-2 text-xs opacity-70">
              Permissions reflect the impersonated user.
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={exit}
          disabled={exiting}
          className="inline-flex items-center gap-1.5 h-7 px-3 rounded bg-amber-950 text-amber-50 text-xs font-medium hover:bg-amber-950/90 disabled:opacity-50 shrink-0"
        >
          <LogOut className="w-3.5 h-3.5" />
          {exiting ? "Exiting…" : "Exit"}
        </button>
      </div>
    </div>
  );
}
