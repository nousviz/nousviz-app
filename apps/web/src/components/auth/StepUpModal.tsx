/**
 * StepUpModal — re-authentication prompt for sensitive operations.
 *
 * B236 (v0.9.10.0): when an RBAC write or impersonation request returns
 * 401 with `{detail: {error: 'stepup_required', ...}}`, this modal pops up,
 * collects the user's password, calls POST /api/auth/step-up, and on
 * success retries the original request.
 *
 * Wired up via apps/web/src/lib/api.ts — when apiFetch() sees a
 * stepup_required response, it shows this modal and queues the retry.
 *
 * The modal is intentionally simple: password input, submit, error
 * inline. Three failures close the modal; the user can re-trigger it
 * by attempting the operation again.
 */

import { useEffect, useRef, useState } from "react";
import { Lock, X } from "lucide-react";

interface StepUpModalProps {
  open: boolean;
  /** Called when the user successfully steps up. The caller retries the original request. */
  onSuccess: () => void;
  /** Called when the user cancels or three failures occur. */
  onCancel: () => void;
}

export default function StepUpModal({ open, onSuccess, onCancel }: StepUpModalProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus the password field when the modal opens; reset state on close.
  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    } else {
      setPassword("");
      setError(null);
      setAttempts(0);
      setSubmitting(false);
    }
  }, [open]);

  // Esc closes
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!password || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      // Use raw fetch with the token attached directly. apiFetch would
      // try to handle the response's 401 specially and trigger its
      // own stepup-required modal recursion.
      const token = localStorage.getItem("nousviz_auth_token") || "";
      const r = await fetch("/api/auth/step-up", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": token,
        },
        body: JSON.stringify({ password }),
      });
      if (r.ok) {
        onSuccess();
        return;
      }
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      const data = await r.json().catch(() => ({}));
      const detail = typeof data.detail === "string" ? data.detail : "Re-authentication failed.";
      setError(detail);
      setPassword("");
      if (newAttempts >= 3) {
        // Give up — close the modal.
        setTimeout(onCancel, 1500);
      }
    } catch {
      setError("Network error. Try again.");
      setSubmitting(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="stepup-title"
    >
      <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-sm mx-4 overflow-hidden">
        <header className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-muted-foreground" />
            <h2 id="stepup-title" className="font-display text-sm text-foreground">
              Confirm your password
            </h2>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Cancel"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <form onSubmit={submit} className="px-5 py-4 space-y-3">
          <p className="text-xs text-muted-foreground">
            This action requires re-authentication. Confirm your password to continue.
          </p>

          <input
            ref={inputRef}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            disabled={submitting}
            className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
            autoComplete="current-password"
          />

          {error && (
            <p className="text-xs text-rose-400">
              {error} {attempts > 0 && attempts < 3 && `(${3 - attempts} attempt${3 - attempts === 1 ? "" : "s"} remaining)`}
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onCancel}
              className="h-8 px-3 text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!password || submitting}
              className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 hover:bg-primary/90"
            >
              {submitting ? "Verifying…" : "Confirm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
