import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { UserPlus, Loader2, ArrowRight, CheckCircle2, XCircle } from "lucide-react";
import SidebarLogo from "@/components/layout/SidebarLogo";

const TOKEN_KEY = "nousviz_auth_token";

export default function AcceptInvitePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";

  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    if (!token) setExpired(true);
  }, [token]);

  const passwordTooShort = password.length > 0 && password.length < 8;
  const passwordsNoMatch = confirmPassword.length > 0 && password !== confirmPassword;
  const canSubmit = name.trim().length > 0 && password.length >= 8 && password === confirmPassword && !loading;

  async function handleAccept() {
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/auth/accept-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_token: token, password, name: name.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 410) setExpired(true);
        else setError(data.detail || "Failed to accept invitation.");
        setLoading(false);
        return;
      }
      localStorage.setItem(TOKEN_KEY, data.token);
      setSuccess(true);
      setTimeout(() => navigate("/"), 1500);
    } catch {
      setError("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  }

  if (expired) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center">
          <SidebarLogo collapsed={false} />
          <div className="bg-card border border-border rounded-xl p-6 mt-8 space-y-3">
            <XCircle className="w-8 h-8 text-red-400 mx-auto" />
            <h2 className="font-display text-base text-foreground">Invitation Expired</h2>
            <p className="text-xs text-muted-foreground">
              This invite link is invalid or has expired. Ask your admin to send a new one.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center">
          <SidebarLogo collapsed={false} />
          <div className="bg-card border border-border rounded-xl p-6 mt-8 space-y-3">
            <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto" />
            <h2 className="font-display text-base text-foreground">Account Created</h2>
            <p className="text-xs text-muted-foreground">Redirecting to NousViz...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center mb-8">
          <SidebarLogo collapsed={false} />
        </div>

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="text-center">
            <UserPlus className="w-5 h-5 text-primary mx-auto mb-2" />
            <h2 className="font-display text-base text-foreground">Accept Invitation</h2>
            <p className="text-xs text-muted-foreground mt-1">Set your name and password to get started.</p>
          </div>

          <div className="space-y-3">
            <div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
                autoFocus
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div>
              <input
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                placeholder="Password"
                autoComplete="new-password"
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              {passwordTooShort && (
                <p className="text-[11px] text-yellow-400 mt-1 ml-1">Must be at least 8 characters</p>
              )}
            </div>
            <div>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setError(""); }}
                onKeyDown={(e) => e.key === "Enter" && canSubmit && handleAccept()}
                placeholder="Confirm password"
                autoComplete="new-password"
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              {passwordsNoMatch && (
                <p className="text-[11px] text-yellow-400 mt-1 ml-1">Passwords don't match</p>
              )}
            </div>
          </div>

          {error && <p className="text-xs text-red-400 text-center">{error}</p>}

          <button
            onClick={handleAccept}
            disabled={!canSubmit}
            className="w-full h-10 rounded-lg bg-primary text-primary-foreground text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Create Account <ArrowRight className="w-4 h-4" /></>}
          </button>
        </div>
      </div>
    </div>
  );
}
