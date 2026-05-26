import { useState, useEffect, useCallback, useMemo } from "react";
import { Lock, Loader2, ArrowRight, UserPlus, Mail } from "lucide-react";
import SidebarLogo from "./SidebarLogo";
import BootSplash from "./BootSplash";
import { BootCoordinatorProvider } from "./BootCoordinator";
import LoadErrorScreen from "./LoadErrorScreen";
import { loadPluginFrontendComponents } from "@/lib/plugin-component-loader";
import {
  getPluginLoaderFailedSnapshot,
  getPluginLoaderFailureReason,
  clearPluginLoaderFailure,
} from "@/widgets/plugin-components";
import ForgotPasswordModal from "@/components/auth/ForgotPasswordModal";

const API = "/api/auth";
const TOKEN_KEY = "nousviz_auth_token";

const PUBLIC_PATHS = ["/shared/", "/embed/", "/accept-invite", "/reset-password"];

interface AuthStatus {
  authenticated: boolean;
  auth_required: boolean;
  users_exist: boolean;
  user?: { email: string; role: string; name?: string };
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"checking" | "login" | "register" | "authenticated">("checking");

  // Login form
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  // B251: forgot-password modal
  const [forgotOpen, setForgotOpen] = useState(false);

  const isPublicPath = PUBLIC_PATHS.some(p => window.location.pathname.startsWith(p));

  // B223 (v0.9.7.6): gate route rendering until plugin frontend components
  // have registered. Public paths skip the gate (they don't render plugin
  // dashboards). 5s hard timeout — if the loader hangs, render anyway and
  // let DashboardRenderer fall through to its existing fallback.
  const [pluginsLoaded, setPluginsLoaded] = useState(false);

  // B224 (v0.9.7.7): minimum show time for the branded boot splash so it
  // doesn't flash-and-disappear on warm cache. 400ms is the floor, not an
  // additive delay — if the loader takes 1.5s, the splash shows for 1.5s.
  const [minShowElapsed, setMinShowElapsed] = useState(false);

  // B225 (v0.9.7.8): destination-page readiness signal. The splash carries
  // through the first page's data fetch instead of dismissing prematurely.
  // pageReady starts true for public paths (which don't use the coordinator).
  // firstPaintGate flips false after the splash dismisses for the first
  // time, so subsequent navigations don't re-trigger the splash.
  const [pageReady, setPageReady] = useState(false);
  const [firstPaintGate, setFirstPaintGate] = useState(true);

  const markBootPageReady = useCallback(() => {
    setPageReady(true);
  }, []);

  useEffect(() => {
    if (isPublicPath) { setState("authenticated"); return; }
    checkAuth();
  }, []);

  useEffect(() => {
    if (isPublicPath) { setMinShowElapsed(true); setPageReady(true); return; }
    const t = setTimeout(() => setMinShowElapsed(true), 400);
    return () => clearTimeout(t);
  }, [isPublicPath]);

  // B225: 3s hard timeout on page-ready. If the destination page never
  // signals (hung route, network error), dismiss the splash anyway and
  // let the page's own loading/error UI take over.
  useEffect(() => {
    if (!pluginsLoaded || !firstPaintGate || pageReady) return;
    const t = setTimeout(() => {
      // eslint-disable-next-line no-console
      console.warn("[AuthGate] page-ready timeout (3s); dismissing splash");
      setPageReady(true);
    }, 3000);
    return () => clearTimeout(t);
  }, [pluginsLoaded, pageReady, firstPaintGate]);

  // Once the splash actually dismisses, lock the gate so subsequent
  // navigations don't re-run the splash flow.
  useEffect(() => {
    if (
      state === "authenticated" &&
      pluginsLoaded &&
      minShowElapsed &&
      pageReady &&
      firstPaintGate
    ) {
      setFirstPaintGate(false);
    }
  }, [state, pluginsLoaded, minShowElapsed, pageReady, firstPaintGate]);

  const coordinatorValue = useMemo(
    () => ({ isFirstPaint: firstPaintGate, markBootPageReady }),
    [firstPaintGate, markBootPageReady],
  );

  // v1.0.2: track whether the plugin loader hit a terminal failure (vs.
  // legitimately completed with zero components). Drives the LoadErrorScreen
  // render below. `loaderAttempt` lets the user retry from the error screen
  // without a full window.location.reload() — bumping it re-runs the effect.
  const [loaderFailed, setLoaderFailed] = useState(false);
  const [loaderFailureReason, setLoaderFailureReason] = useState<string | null>(null);
  const [loaderAttempt, setLoaderAttempt] = useState(0);

  useEffect(() => {
    if (state !== "authenticated") return;
    if (isPublicPath) { setPluginsLoaded(true); return; }
    let cancelled = false;
    // v0.10.0.5.1: bumped 5s → 15s. With 17+ installed plugins on prod, the
    // /api/plugins fetch + per-plugin frontend-block walk routinely exceeded
    // 5s on cold-cache, causing the loader to time out mid-registration and
    // leaving dashboard widgets unresolvable. 15s gives headroom; the
    // WidgetRenderer "Loading widget…" placeholder (also v0.10.0.5.1)
    // makes the wait operator-friendly.
    //
    // v1.0.2: on timeout, also check whether the loader reported terminal
    // failure (via notifyPluginLoaderFailed) — if so, render LoadErrorScreen
    // instead of dumping the user into a half-functional dashboard.
    const timeout = setTimeout(() => {
      if (cancelled) return;
      if (getPluginLoaderFailedSnapshot()) {
        setLoaderFailureReason(getPluginLoaderFailureReason());
        setLoaderFailed(true);
        return; // don't set pluginsLoaded — error screen replaces the dashboard
      }
      // eslint-disable-next-line no-console
      console.warn("[AuthGate] plugin loader timeout (15s); rendering anyway");
      setPluginsLoaded(true);
    }, 15000);
    loadPluginFrontendComponents().finally(() => {
      if (cancelled) return;
      clearTimeout(timeout);
      if (getPluginLoaderFailedSnapshot()) {
        setLoaderFailureReason(getPluginLoaderFailureReason());
        setLoaderFailed(true);
        return;
      }
      setLoaderFailed(false);
      setLoaderFailureReason(null);
      setPluginsLoaded(true);
    });
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [state, isPublicPath, loaderAttempt]);

  // v1.0.2: handler the LoadErrorScreen calls when the user clicks Reload.
  // Cheaper + smoother than window.location.reload() — clears the loader's
  // failure state, resets local state, bumps `loaderAttempt` to re-run the
  // effect. If it fails again, the screen comes back; if it works, the
  // dashboard mounts normally.
  const handleLoaderRetry = useCallback(async () => {
    clearPluginLoaderFailure();
    setLoaderFailed(false);
    setLoaderFailureReason(null);
    setPluginsLoaded(false);
    setLoaderAttempt((n) => n + 1);
  }, []);

  async function checkAuth() {
    try {
      const res = await fetch(`${API}/status`, { cache: "no-store" });
      const status: AuthStatus = await res.json();

      if (!status.auth_required) {
        setState("authenticated");
        return;
      }

      // Check for existing valid token
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        const verifyRes = await fetch(`${API}/verify?token=${encodeURIComponent(token)}`);
        const verify = await verifyRes.json();
        if (verify.valid) {
          setState("authenticated");
          return;
        }
        localStorage.removeItem(TOKEN_KEY);
      }

      // No users exist yet → registration (first-user bootstrap)
      if (!status.users_exist) {
        setState("register");
        return;
      }

      setState("login");
    } catch {
      setState("login");
    }
  }

  async function handleLogin() {
    setError("");
    setLoading(true);
    try {
      const body = { email, password };
      const res = await fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login failed.");
        setLoading(false);
        return;
      }
      localStorage.setItem(TOKEN_KEY, data.token);
      setState("authenticated");
    } catch {
      setError("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name: name || undefined }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Registration failed.");
        setLoading(false);
        return;
      }
      localStorage.setItem(TOKEN_KEY, data.token);
      setState("authenticated");
    } catch {
      setError("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  }

  // B224 (v0.9.7.7) + B225 (v0.9.7.8): branded boot splash owns the entire
  // boot window — auth verify + plugin loader + min-show-time + first-page
  // ready. Public paths short-circuit (their flags are pre-set to true
  // above). Login/register screens are unaffected.
  //
  // While the splash is up but the user is already authenticated, render
  // children underneath as an invisible overlay so they can mount, fetch,
  // and call markBootPageReady() — otherwise we'd have a chicken-and-egg
  // and the splash would never dismiss.
  const showBootSplash =
    !isPublicPath &&
    firstPaintGate &&
    (state === "checking" ||
      (state === "authenticated" && !pluginsLoaded) ||
      !minShowElapsed ||
      !pageReady);

  // Pre-auth (state === "checking"): show splash only, no children to mount.
  if (showBootSplash && state === "checking") {
    return <BootSplash />;
  }

  // v1.0.2: plugin loader hit a terminal failure (couldn't fetch
  // /api/plugins even after retries). Show a recoverable error screen
  // instead of dumping the user into a dashboard with no widget registry.
  // The reload button calls handleLoaderRetry which re-runs the loader
  // effect — no full page reload needed if it works the second time.
  if (state === "authenticated" && loaderFailed) {
    return (
      <LoadErrorScreen
        reason={loaderFailureReason}
        onReload={handleLoaderRetry}
      />
    );
  }

  // Authenticated: render children directly. While the splash is up, layer
  // it on top via fixed positioning so children can mount underneath and
  // call markBootPageReady() — without that, the splash deadlocks until
  // the 3s timeout. Children are NOT wrapped in a div (avoids breaking
  // any CSS that targets the app's outer structure).
  if (state === "authenticated") {
    return (
      <BootCoordinatorProvider value={coordinatorValue}>
        {children}
        {showBootSplash && (
          <div className="fixed inset-0 z-50 bg-background">
            <BootSplash />
          </div>
        )}
      </BootCoordinatorProvider>
    );
  }

  // Registration form (first-user bootstrap)
  if (state === "register") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-2.5 justify-center mb-8">
            <SidebarLogo collapsed={false} />
          </div>

          <div className="bg-card border border-border rounded-xl p-6 space-y-4">
            <div className="text-center">
              <UserPlus className="w-5 h-5 text-primary mx-auto mb-2" />
              <h2 className="font-display text-base text-foreground">Create Admin Account</h2>
              <p className="text-xs text-muted-foreground mt-1">First user becomes the superadmin.</p>
            </div>

            <div className="space-y-3">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name (optional)"
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(""); }}
                placeholder="Email"
                autoFocus
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <input
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                placeholder="Password (8+ characters)"
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setError(""); }}
                onKeyDown={(e) => e.key === "Enter" && handleRegister()}
                placeholder="Confirm password"
                className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {error && <p className="text-xs text-red-400 text-center">{error}</p>}

            <button
              onClick={handleRegister}
              disabled={loading || !email || password.length < 8 || password !== confirmPassword}
              className="w-full h-10 rounded-lg bg-primary text-primary-foreground text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Create Account <ArrowRight className="w-4 h-4" /></>}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Login form
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <SidebarLogo collapsed={false} />
        </div>

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="text-center">
            <Lock className="w-5 h-5 text-muted-foreground mx-auto mb-2" />
            <h2 className="font-display text-base text-foreground">Sign In</h2>
            <p className="text-xs text-muted-foreground mt-1">Enter your email and password</p>
          </div>

          <div className="space-y-3">
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(""); }}
                placeholder="Email"
                autoFocus
                className="w-full h-10 pl-10 pr-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(""); }}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="Password"
              className="w-full h-10 px-4 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {error && <p className="text-xs text-red-400 text-center">{error}</p>}

          <button
            onClick={handleLogin}
            disabled={loading || !password || !email}
            className="w-full h-10 rounded-lg bg-primary text-primary-foreground text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Sign In <ArrowRight className="w-4 h-4" /></>}
          </button>

          <button
            type="button"
            onClick={() => setForgotOpen(true)}
            className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors text-center"
          >
            Forgot password?
          </button>
        </div>

        <ForgotPasswordModal
          open={forgotOpen}
          defaultEmail={email}
          onClose={() => setForgotOpen(false)}
        />
      </div>
    </div>
  );
}