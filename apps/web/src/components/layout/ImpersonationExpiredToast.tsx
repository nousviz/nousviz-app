/**
 * ImpersonationExpiredToast — auto-dismissing toast that fires when an
 * impersonation auto-expired (acting_as_until passed and the server's
 * lazy-clear flipped the flag).
 *
 * B254 (v0.9.10.0.5). Mounted alongside the ImpersonationBanner in
 * AppLayout. Reads `recentlyExpiredImpersonationLabel` from
 * useCurrentUser; calls `dismissExpiredImpersonation()` after 6 seconds
 * or when the user clicks dismiss.
 */

import { useEffect } from "react";
import { Clock, X } from "lucide-react";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export default function ImpersonationExpiredToast() {
  const { recentlyExpiredImpersonationLabel: label, dismissExpiredImpersonation: dismiss } =
    useCurrentUser();

  useEffect(() => {
    if (!label) return;
    const t = setTimeout(dismiss, 6000);
    return () => clearTimeout(t);
  }, [label, dismiss]);

  if (!label) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-4 right-4 z-[70] flex items-center gap-2 px-3 py-2 rounded-md bg-amber-500/95 text-amber-950 border border-amber-700 shadow-lg max-w-sm"
    >
      <Clock className="w-4 h-4 shrink-0" />
      <p className="text-xs flex-1">
        Impersonation expired. Returned from impersonating{" "}
        <span className="font-medium">{label}</span>.
      </p>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss"
        className="text-amber-950/70 hover:text-amber-950 shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
