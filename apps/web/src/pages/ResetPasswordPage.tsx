/**
 * ResetPasswordPage — public page that consumes a forgot-password
 * email link.
 *
 * B251 (v0.9.10.0.3). URL: /reset-password?token=<raw>. Mounted
 * outside AuthGate so unauthenticated users can reach it.
 *
 * On submit, POSTs to /api/auth/reset-password. On success, redirects
 * to / (root) — the AuthGate will then show the login form. We don't
 * try to auto-log-in because the API kills all sessions for the user
 * on a successful reset (security: prevents hijacker-with-stolen-token
 * surviving the reset).
 */

import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Lock, CheckCircle2, AlertCircle } from "lucide-react";

interface ApiErrorDetail {
  error?: "token_invalid" | "token_expired" | "token_used";
  message?: string;
}

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  // No-token guard: if the URL is bare /reset-password, point users back.
  useEffect(() => {
    if (!token) {
      setError(
        "This page needs a valid reset token. Open the link from your password reset email, or request a new one."
      );
    }
  }, [token]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || submitting) return;

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (r.ok) {
        setDone(true);
        // Redirect to root after a beat so the success message is visible.
        setTimeout(() => navigate("/"), 2500);
        return;
      }
      const data = await r.json().catch(() => ({}));
      const detail = data?.detail as ApiErrorDetail | string | undefined;
      const message =
        typeof detail === "string"
          ? detail
          : detail?.message || "Reset failed. Try again.";
      setError(message);
    } catch {
      setError("Network error. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <Lock className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <h1 className="font-display text-lg text-foreground">
            Set a new password
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            NousViz password reset
          </p>
        </div>

        {done ? (
          <div className="bg-card rounded-lg border border-border p-5 space-y-3 text-center">
            <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto" />
            <p className="text-sm text-foreground">
              Password reset. Redirecting you to log in&hellip;
            </p>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="text-xs text-primary hover:underline"
            >
              Go now
            </button>
          </div>
        ) : (
          <form
            onSubmit={submit}
            className="bg-card rounded-lg border border-border p-5 space-y-4"
          >
            {!token && (
              <div className="flex items-start gap-2 text-xs text-amber-400">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>
                  This page needs a reset token in the URL. Open the link from
                  your password reset email.
                </span>
              </div>
            )}

            <div>
              <label className="block text-xs text-muted-foreground mb-1">
                New password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError(null);
                }}
                disabled={!token || submitting}
                placeholder="At least 8 characters"
                className="w-full h-10 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                autoComplete="new-password"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs text-muted-foreground mb-1">
                Confirm new password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => {
                  setConfirm(e.target.value);
                  setError(null);
                }}
                disabled={!token || submitting}
                placeholder="Re-enter password"
                className="w-full h-10 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                autoComplete="new-password"
              />
            </div>

            {error && (
              <p className="text-xs text-rose-400">{error}</p>
            )}

            <button
              type="submit"
              disabled={!token || !password || !confirm || submitting}
              className="w-full h-10 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 hover:bg-primary/90"
            >
              {submitting ? "Resetting…" : "Reset password"}
            </button>

            <p className="text-[10px] text-muted-foreground text-center pt-1">
              The link expires 1 hour after it was issued. If yours has
              expired, request a new one from the login page.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
