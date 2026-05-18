/**
 * ForgotPasswordModal — pre-auth password reset request.
 *
 * B251 (v0.9.10.0.3): rendered from AuthGate's login form via the
 * "Forgot password?" link. Collects email, calls
 * POST /api/auth/forgot-password, shows generic success message
 * regardless of whether the email exists (enumeration resistance —
 * matches the backend's response shape).
 *
 * NOT a step-up modal — this is the public unauthenticated flow.
 * (StepUpModal is the in-app re-auth for sensitive actions.)
 */

import { useEffect, useRef, useState } from "react";
import { Mail, X } from "lucide-react";

interface ForgotPasswordModalProps {
  open: boolean;
  /** Pre-fill the email from the login form, if available. */
  defaultEmail?: string;
  onClose: () => void;
}

export default function ForgotPasswordModal({ open, defaultEmail, onClose }: ForgotPasswordModalProps) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setEmail(defaultEmail || "");
      setSubmitting(false);
      setDone(false);
      setError(null);
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open, defaultEmail]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (r.ok) {
        setDone(true);
      } else if (r.status === 429) {
        setError("Too many reset requests for this email. Try again later.");
      } else {
        // Server returns generic 200 even on bad input — anything else
        // is unexpected.
        setError("Could not send reset email. Try again.");
      }
    } catch {
      setError("Network error. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="forgot-title"
    >
      <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-sm mx-4 overflow-hidden">
        <header className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-muted-foreground" />
            <h2 id="forgot-title" className="font-display text-sm text-foreground">
              Reset your password
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        {done ? (
          <div className="px-5 py-5 space-y-3">
            <p className="text-sm text-foreground">
              If an account exists with that email, a reset link has been sent.
            </p>
            <p className="text-xs text-muted-foreground">
              The link expires in 1 hour. Check your spam folder if you don&apos;t see it.
            </p>
            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={onClose}
                className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90"
              >
                Got it
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={submit} className="px-5 py-4 space-y-3">
            <p className="text-xs text-muted-foreground">
              Enter the email associated with your account. We&apos;ll send a one-hour reset link.
            </p>

            <input
              ref={inputRef}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={submitting}
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
              autoComplete="email"
            />

            {error && (
              <p className="text-xs text-rose-400">{error}</p>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="h-8 px-3 text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!email || submitting}
                className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 hover:bg-primary/90"
              >
                {submitting ? "Sending…" : "Send reset link"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
