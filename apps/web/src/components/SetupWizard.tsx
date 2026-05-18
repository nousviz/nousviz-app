/**
 * SetupWizard — post-install configuration guide.
 *
 * Shown on first browser visit. Reads live state from /api/health to show
 * what is already working and what still needs attention. Does NOT write
 * files or create databases — setup.sh handles that before the app starts.
 *
 * The wizard's job is to:
 *   1. Confirm what's connected (Postgres, encryption key, auth)
 *   2. Surface anything insecure or missing
 *   3. Show exactly which .env variable to change and what value to use
 *   4. Set the instance name (localStorage + document.title)
 *
 * Persists completion in localStorage under "nousviz:setup_complete".
 */

import { useState, useEffect } from "react";
import {
  CheckCircle2, AlertTriangle, XCircle, ChevronRight, ChevronLeft,
  Database, Key, Shield, Rocket, X, Eye, EyeOff, Globe, Lock,
} from "lucide-react";
import SslSetupModal from "@/components/SslSetupModal";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";

export const SETUP_KEY         = "nousviz:setup_complete";
export const INSTANCE_NAME_KEY = "nousviz:instance_name";

export function applyInstanceName(name: string) {
  const trimmed = name.trim() || "NousViz";
  document.title = `${trimmed} — Data Intelligence Platform`;
  localStorage.setItem(INSTANCE_NAME_KEY, trimmed);
}

// ── Types ─────────────────────────────────────────────────────────────

interface HealthData {
  status: string;
  version: string;
  services: {
    postgres?: { status: string; version?: string; tables?: number };
  };
  stats: {
    active_alerts: number;
    fusions: number;
    migrations: number;
  };
}

interface ConfigData {
  encryption_key_set: boolean;
  auth_required: boolean;
  superadmin_exists: boolean;
  postgres_password_is_default: boolean;
}

interface CheckItem {
  id: string;
  label: string;
  status: "ok" | "warn" | "error" | "unknown";
  detail: string;
  fix?: string; // env var name
}

// ── Shared ────────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: CheckItem["status"] }) {
  if (status === "ok")      return <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />;
  if (status === "warn")    return <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0" />;
  if (status === "error")   return <XCircle className="w-4 h-4 text-red-400 shrink-0" />;
  return <div className="w-4 h-4 rounded-full border-2 border-border shrink-0 animate-pulse" />;
}

// ── Steps ─────────────────────────────────────────────────────────────

function StepWelcome({ health, checks }: { health: HealthData | null; checks: CheckItem[] }) {
  const loading    = health === null;
  const issueCount = checks.filter(c => c.status === "warn" || c.status === "error").length;
  const allOk      = issueCount === 0 && !loading;

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-4">
        <div className={cn(
          "h-12 w-12 rounded-xl flex items-center justify-center shrink-0",
          loading ? "bg-secondary" : allOk ? "bg-green-500/10" : "bg-primary/10"
        )}>
          <Rocket className={cn("w-6 h-6", loading ? "text-muted-foreground animate-pulse" : allOk ? "text-green-400" : "text-primary")} />
        </div>
        <div>
          <h2 className="font-display text-lg text-foreground">
            {loading ? "Checking your instance…" : allOk ? "You're all set" : "Welcome to NousViz"}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {loading
              ? "Connecting to the API to check what's configured."
              : allOk
                ? "Everything looks good. You can skip through the rest or check the steps below."
                : `${issueCount} thing${issueCount !== 1 ? "s" : ""} need${issueCount === 1 ? "s" : ""} your attention before you go live.`}
          </p>
        </div>
      </div>

      {/* Live status summary */}
      <div className="space-y-2">
        {checks.map(c => (
          <div key={c.id} className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-secondary/30 border border-border">
            <StatusIcon status={c.status} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground">{c.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{c.detail}</p>
            </div>
          </div>
        ))}
      </div>

      {health === null && (
        <p className="text-xs text-muted-foreground text-center">
          Checking live status…
        </p>
      )}
    </div>
  );
}

function StepInstance({ name, setName }: { name: string; setName: (s: string) => void }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-lg text-foreground">Name your instance</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Shown in the browser tab and any share links. Stored in your browser only — no server config needed.
        </p>
      </div>
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1.5">Instance name</label>
        <input
          autoFocus
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="e.g. Acme Analytics"
          className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <p className="text-[11px] text-muted-foreground mt-1.5">
          Preview: <span className="text-foreground">{(name.trim() || "NousViz")} — Data Intelligence Platform</span>
        </p>
      </div>
    </div>
  );
}

function StepDatabase({ check }: { check: CheckItem }) {
  const ok = check.status === "ok";

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center shrink-0", ok ? "bg-green-500/10" : "bg-red-500/10")}>
          <Database className={cn("w-5 h-5", ok ? "text-green-400" : "text-red-400")} />
        </div>
        <div>
          <h2 className="font-display text-lg text-foreground">PostgreSQL</h2>
          <p className="text-sm text-muted-foreground mt-0.5">{check.detail}</p>
        </div>
      </div>

      {ok ? (
        <div className="rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3 text-sm text-green-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> Database is connected and migrations are applied.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
            Cannot connect to Postgres. The API won't work without a database.
          </div>
          <div className="rounded-lg border border-border p-4 space-y-3 text-sm">
            <p className="font-medium text-foreground">To fix this:</p>
            <ol className="space-y-2 text-muted-foreground list-decimal list-inside">
              <li>
                Make sure Postgres is running and reachable — any Postgres works:{" "}
                <span className="text-foreground">local install, RDS, Supabase, Neon, etc.</span>
              </li>
              <li>
                Check <span className="font-mono-deck bg-secondary px-1.5 py-0.5 rounded text-xs text-foreground">.env</span> has the correct{" "}
                <span className="font-mono-deck text-xs">POSTGRES_HOST</span>,{" "}
                <span className="font-mono-deck text-xs">POSTGRES_DB</span>,{" "}
                <span className="font-mono-deck text-xs">POSTGRES_USER</span>,{" "}
                <span className="font-mono-deck text-xs">POSTGRES_PASSWORD</span>
              </li>
              <li>
                Run migrations:{" "}
                <span className="font-mono-deck bg-secondary px-1.5 py-0.5 rounded text-xs text-foreground">./scripts/setup.sh</span>
              </li>
              <li>Restart the API, then reload this page</li>
            </ol>
          </div>
          <p className="text-xs text-muted-foreground">
            Run <span className="font-mono-deck bg-secondary px-1 rounded">./scripts/setup.sh</span> to install and start Postgres automatically.
          </p>
        </div>
      )}
    </div>
  );
}

function StepPostgresPassword({
  pgPw,
  setPgPw,
}: {
  pgPw: string;
  setPgPw: (s: string) => void;
}) {
  const [pgPwConfirm, setPgPwConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center shrink-0">
          <Database className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h2 className="font-display text-lg text-foreground">Secure your database</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            The default Postgres password is publicly known. Set a unique one before going live.
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 space-y-3">
        <p className="text-xs text-red-400">
          <span className="font-mono-deck bg-secondary px-1 rounded">POSTGRES_PASSWORD</span> is set to the publicly known default{" "}
          <span className="font-mono-deck bg-secondary px-1 rounded">nousviz_dev</span>.{" "}
          Set a unique password to secure your database.
        </p>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">New Postgres password</label>
          <div className="relative">
            <input
              type={showPw ? "text" : "password"}
              value={pgPw}
              onChange={e => setPgPw(e.target.value)}
              placeholder="Min 8 characters"
              className="w-full h-9 px-3 pr-9 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              onClick={() => setShowPw(v => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          {pgPw.length > 0 && pgPw.length < 8 && (
            <p className="text-[11px] text-yellow-400 mt-1">{8 - pgPw.length} more character{8 - pgPw.length !== 1 ? "s" : ""} needed</p>
          )}
          {pgPw.length >= 8 && (
            <p className="text-[11px] text-green-400 mt-1">✓ Length requirement met</p>
          )}
        </div>

        {pgPw.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Confirm Postgres password</label>
            <input
              type="password"
              value={pgPwConfirm}
              onChange={e => setPgPwConfirm(e.target.value)}
              placeholder="Re-enter password"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            {pgPwConfirm.length > 0 && pgPw !== pgPwConfirm && (
              <p className="text-[11px] text-red-400 mt-1">Passwords do not match</p>
            )}
            {pgPwConfirm.length > 0 && pgPw === pgPwConfirm && pgPw.length >= 8 && (
              <p className="text-[11px] text-green-400 mt-1">✓ Passwords match</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StepSecurity({
  checks,
  config,
  pgPw,
  onSecured,
}: {
  checks: CheckItem[];
  config: ConfigData | null;
  pgPw: string;
  onSecured: () => void;
}) {
  const encCheck  = checks.find(c => c.id === "encryption")!;
  const encOk     = encCheck.status === "ok";
  const alreadyConfigured = config?.superadmin_exists ?? false;

  const isPublic = typeof window !== "undefined"
    && window.location.hostname !== "localhost"
    && window.location.hostname !== "127.0.0.1";

  // ── Encryption key state ──
  const [encGenerated, setEncGenerated] = useState(encOk);
  const [encSaving, setEncSaving] = useState(false);
  const [encErr, setEncErr] = useState<string | null>(null);

  async function generateKey() {
    setEncSaving(true);
    setEncErr(null);
    try {
      const res = await fetch("/api/auth/setup/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ generate_encryption_key: true }),
      });
      const data = await res.json();
      if (!res.ok) { setEncErr(data.detail ?? "Failed to generate key."); return; }
      setEncGenerated(true);
    } catch {
      setEncErr("Network error — please try again.");
    } finally {
      setEncSaving(false);
    }
  }

  // ── Auth state ──
  // B252 (v0.9.11.2): multi-user is the only auth mode. The wizard
  // creates the first superadmin; subsequent users come in via invite.
  const [pw, setPw]           = useState("");
  const [pwConfirm, setPwConfirm] = useState("");
  const [email, setEmail]     = useState("");
  const [name, setName]       = useState("");
  const [authOn, setAuthOn]   = useState(true);
  const [showPw, setShowPw]   = useState(false);
  const [authSaving, setAuthSaving] = useState(false);
  const [authDone, setAuthDone] = useState(alreadyConfigured);
  const [authErr, setAuthErr]   = useState<string | null>(null);

  async function applyAuth() {
    setAuthErr(null);
    if (pw.length < 8) { setAuthErr("Password must be at least 8 characters."); return; }
    if (pw !== pwConfirm) { setAuthErr("Passwords do not match."); return; }
    if (!email.trim()) { setAuthErr("Email is required for the admin account."); return; }
    if (!name.trim()) { setAuthErr("Name is required."); return; }

    setAuthSaving(true);
    try {
      // Step 1: write AUTH_REQUIRED + (optionally) postgres password to .env
      const configRes = await fetch("/api/auth/setup/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auth_required: authOn,
          ...(pgPw ? { postgres_password: pgPw } : {}),
        }),
      });
      const configData = await configRes.json();
      if (!configRes.ok) { setAuthErr(configData.detail ?? "Failed to save config."); return; }

      // Step 2: register the first superadmin
      const regRes = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password: pw, name: name.trim() }),
      });
      const regData = await regRes.json();
      if (!regRes.ok) { setAuthErr(regData.detail ?? "Failed to create admin account."); return; }
      if (regData.token) {
        localStorage.setItem("nousviz_auth_token", regData.token);
      }

      setAuthDone(true);
      onSecured();
    } catch {
      setAuthErr("Network error — please try again.");
    } finally {
      setAuthSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center shrink-0">
          <Shield className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h2 className="font-display text-lg text-foreground">Security</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Protect this instance before sharing the URL.
          </p>
        </div>
      </div>

      {/* Card 1: Encryption key */}
      <div className={cn(
        "rounded-lg border p-4 space-y-3",
        encGenerated ? "border-green-500/20 bg-green-500/5" : "border-yellow-500/20 bg-yellow-500/5"
      )}>
        <div className="flex items-center gap-2">
          <Key className={cn("w-4 h-4 shrink-0", encGenerated ? "text-green-400" : "text-yellow-400")} />
          <span className="text-sm font-medium text-foreground">Credential encryption key</span>
          <StatusIcon status={encGenerated ? "ok" : "warn"} />
        </div>
        {encGenerated ? (
          <p className="text-xs text-green-400">Encryption key is set. Plugin credentials are stored securely.</p>
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              A 256-bit AES key is required to encrypt plugin credentials at rest.
              Click below to generate one automatically.
            </p>
            {encErr && <p className="text-xs text-red-400">{encErr}</p>}
            <button
              onClick={generateKey}
              disabled={encSaving}
              className="h-8 px-4 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-40"
            >
              {encSaving ? "Generating…" : "Generate encryption key"}
            </button>
          </>
        )}
      </div>

      {/* Card 2: Dashboard authentication */}
      <div className={cn(
        "rounded-lg border p-4 space-y-3",
        authDone
          ? "border-green-500/20 bg-green-500/5"
          : isPublic
            ? "border-red-500/20 bg-red-500/5"
            : "border-border bg-secondary/20"
      )}>
        <div className="flex items-center gap-2">
          <Shield className={cn(
            "w-4 h-4 shrink-0",
            authDone ? "text-green-400" : isPublic ? "text-red-400" : "text-muted-foreground"
          )} />
          <span className="text-sm font-medium text-foreground">Dashboard authentication</span>
          <StatusIcon status={authDone ? "ok" : isPublic ? "error" : "warn"} />
        </div>

        {authDone ? (
          <p className="text-xs text-green-400">
            Authentication configured. Close the wizard to continue.
          </p>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              {isPublic
                ? "This instance is publicly accessible. Create your superadmin account now."
                : "Create the first superadmin. Required before any public deployment."}
            </p>

            <div className="space-y-2">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Your name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Admin"
                  autoComplete="name"
                  className="w-full h-9 px-3 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Email</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@yourdomain.com"
                  autoComplete="email"
                  className="w-full h-9 px-3 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={pw}
                  onChange={e => setPw(e.target.value)}
                  placeholder="Min 8 characters"
                  className="w-full h-9 px-3 pr-9 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
              {pw.length > 0 && pw.length < 8 && (
                <p className="text-[11px] text-yellow-400 mt-1">{8 - pw.length} more character{8 - pw.length !== 1 ? "s" : ""} needed</p>
              )}
              {pw.length >= 8 && (
                <p className="text-[11px] text-green-400 mt-1">✓ Length requirement met</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Confirm password</label>
              <input
                type="password"
                value={pwConfirm}
                onChange={e => setPwConfirm(e.target.value)}
                placeholder="Re-enter password"
                className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={authOn}
                onChange={e => setAuthOn(e.target.checked)}
                className="w-4 h-4 rounded border-border accent-primary"
              />
              <span className="text-sm text-foreground">Enable authentication (recommended)</span>
            </label>

            {authErr && <p className="text-xs text-red-400">{authErr}</p>}

            <button
              onClick={applyAuth}
              disabled={authSaving || pw.length < 8}
              className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {authSaving ? "Saving…" : "Enable authentication"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StepAppearance() {
  const { setTheme } = useTheme();
  const [selected, setSelected] = useState<"system" | "dark" | "light">(
    () => (localStorage.getItem("nousviz-theme-mode") as "system" | "dark" | "light") || "system"
  );

  function apply(mode: "system" | "dark" | "light") {
    setSelected(mode);
    localStorage.setItem("nousviz-theme-mode", mode);
    if (mode === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setTheme(prefersDark ? "dark" : "light");
    } else {
      setTheme(mode);
    }
  }

  const options: { id: "system" | "dark" | "light"; label: string; desc: string }[] = [
    { id: "system", label: "Match system", desc: "Automatically follows your OS light/dark preference" },
    { id: "dark", label: "Dark", desc: "Always use dark theme" },
    { id: "light", label: "Light", desc: "Always use light theme" },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-lg text-foreground">Appearance</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Choose your preferred color scheme. You can change this later in Settings.
        </p>
      </div>
      <div className="space-y-2">
        {options.map(opt => (
          <button
            key={opt.id}
            onClick={() => apply(opt.id)}
            className={cn(
              "w-full text-left p-4 rounded-lg border transition-colors",
              selected === opt.id
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/30"
            )}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-foreground">{opt.label}</span>
                <p className="text-xs text-muted-foreground mt-0.5">{opt.desc}</p>
              </div>
              {selected === opt.id && (
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function StepSsl({ onSetup, onSkip }: { onSetup: () => void; onSkip: () => void }) {
  const isLocal = typeof window !== "undefined"
    && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

  if (isLocal) {
    return (
      <div className="space-y-5">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center shrink-0">
            <Lock className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h2 className="font-display text-lg text-foreground">HTTPS</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Not needed for local development. You can configure SSL later when deploying to a server.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center shrink-0">
          <Lock className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h2 className="font-display text-lg text-foreground">Secure your connection</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Encrypt traffic between browsers and your server with HTTPS.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <button
          onClick={onSetup}
          className="w-full text-left p-4 rounded-lg border border-border hover:border-primary/30 transition-colors space-y-1"
        >
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-foreground">Configure HTTPS now</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400">Recommended</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Set up a free Let's Encrypt certificate. Requires a domain name pointed at this server.
          </p>
        </button>

        <button
          onClick={onSkip}
          className="w-full text-center text-xs text-muted-foreground hover:text-foreground py-2 transition-colors"
        >
          Do this later — you can configure SSL anytime in Settings
        </button>
      </div>
    </div>
  );
}

function StepDone({ name, checks }: { name: string; checks: CheckItem[] }) {
  const issues = checks.filter(c => c.status === "warn" || c.status === "error");

  return (
    <div className="space-y-5">
      <div className="text-center py-2">
        <div className="h-14 w-14 rounded-2xl bg-green-500/10 flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="w-7 h-7 text-green-400" />
        </div>
        <h2 className="font-display text-lg text-foreground">
          {issues.length === 0 ? "Ready to go" : "Setup complete"}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {issues.length === 0
            ? `${name.trim() || "NousViz"} is fully configured.`
            : `${issues.length} item${issues.length !== 1 ? "s" : ""} still need${issues.length === 1 ? "s" : ""} attention — you can fix them later in Settings.`}
        </p>
      </div>

      {issues.length > 0 && (
        <div className="space-y-2">
          {issues.map(c => (
            <div key={c.id} className="flex items-start gap-3 px-3 py-2 rounded-lg border border-yellow-500/20 bg-yellow-500/5">
              <StatusIcon status={c.status} />
              <div>
                <p className="text-sm text-foreground">{c.label}</p>
                {c.fix && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Set <span className="font-mono-deck">{c.fix}</span> in <span className="font-mono-deck">.env</span> then restart the API.
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border p-4 space-y-2 text-sm text-muted-foreground">
        <p className="font-medium text-foreground text-xs uppercase tracking-wider">Next steps</p>
        <div className="flex items-center gap-2">
          <ChevronRight className="w-3 h-3 shrink-0" />
          <span>Create your admin account — you'll be prompted on the next page</span>
        </div>
        <div className="flex items-center gap-2">
          <ChevronRight className="w-3 h-3 shrink-0" />
          <span>Configure <a href="/settings" className="text-primary hover:underline">email (SMTP)</a> so invites and alerts can be delivered</span>
        </div>
        <div className="flex items-center gap-2">
          <ChevronRight className="w-3 h-3 shrink-0" />
          <span>Install a plugin from the <a href="/marketplace" className="text-primary hover:underline">Marketplace</a></span>
        </div>
        <div className="flex items-center gap-2">
          <ChevronRight className="w-3 h-3 shrink-0" />
          <span>Create your first <a href="/alerts" className="text-primary hover:underline">alert</a></span>
        </div>
        <div className="flex items-center gap-2">
          <ChevronRight className="w-3 h-3 shrink-0" />
          <span>Read the <a href="/docs" className="text-primary hover:underline">docs</a></span>
        </div>
      </div>
    </div>
  );
}

// ── Wizard shell ──────────────────────────────────────────────────────

export default function SetupWizard(_props: { onClose: () => void }) {
  const [stepIdx, setStepIdx] = useState(0);
  const [health, setHealth]   = useState<HealthData | null>(null);
  const [config, setConfig]   = useState<ConfigData | null>(null);
  const [name, setName]       = useState(
    () => localStorage.getItem(INSTANCE_NAME_KEY) || ""
  );
  const [pgPw, setPgPw]       = useState("");

  useEffect(() => {
    fetch("/api/health", { cache: "no-store" })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setHealth)
      .catch(e => console.error("[SetupWizard] health fetch failed:", e));
    fetch("/api/health/config", { cache: "no-store" })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setConfig)
      .catch(e => console.error("[SetupWizard] config fetch failed:", e));
  }, []);

  const loading = health === null || config === null;
  const pgOk    = health?.services?.postgres?.status === "connected";

  const checks: CheckItem[] = [
    {
      id: "postgres",
      label: "PostgreSQL",
      status: loading ? "unknown" : pgOk ? "ok" : "error",
      detail: loading
        ? "Checking…"
        : pgOk
          ? `Connected · ${health.services.postgres?.tables ?? 0} tables · ${health!.stats.migrations} migrations applied`
          : "Not connected — API cannot function without a database",
    },
    {
      id: "encryption",
      label: "Credential encryption key",
      status: loading ? "unknown" : config!.encryption_key_set ? "ok" : "warn",
      detail: loading
        ? "Checking…"
        : config!.encryption_key_set
          ? "NOUSVIZ_ENCRYPTION_KEY is set."
          : "NOUSVIZ_ENCRYPTION_KEY is not set. Plugin credentials cannot be stored securely until this is configured.",
      fix: "NOUSVIZ_ENCRYPTION_KEY",
    },
    {
      id: "auth",
      label: "Authentication",
      status: loading ? "unknown" : (config!.auth_required && config!.superadmin_exists) ? "ok" : "warn",
      detail: loading
        ? "Checking…"
        : config!.auth_required && config!.superadmin_exists
          ? "Authentication is enabled and a superadmin exists."
          : config!.auth_required && !config!.superadmin_exists
            ? "AUTH_REQUIRED is true but no superadmin exists yet. Complete the Security step below."
            : "Authentication is disabled. Fine for local installs — enable it before any public deployment.",
      fix: "AUTH_REQUIRED",
    },
  ];

  const dbCheck   = checks.find(c => c.id === "postgres")!;
  const secChecks = checks.filter(c => c.id === "encryption" || c.id === "auth");

  // Gate: on a public-IP deploy, the wizard cannot be skipped until the operator
  // sets a password. Once secured (or already configured), the gate lifts.
  const [secured, setSecured] = useState(false);
  const [showSslModal, setShowSslModal] = useState(false);
  const isPublic = typeof window !== "undefined"
    && window.location.hostname !== "localhost"
    && window.location.hostname !== "127.0.0.1";
  const alreadyConfigured = config?.superadmin_exists ?? false;
  const mustSecure = isPublic && !alreadyConfigured && !secured;

  // Build step list once on first config load and freeze it — never let it shrink
  // mid-session (e.g. after applySecure changes postgres_password_is_default to false),
  // which would make stepIdx point past the end of the array and crash.
  // Step order: critical infrastructure first, cosmetic last
  const [STEPS] = useState(() => [
    { id: "welcome",    label: "Status" },
    { id: "database",   label: "Database" },
    // pgIsDefault is false at init (config not yet loaded) — we seed this below via useEffect
    { id: "security",   label: "Security" },
    { id: "ssl",        label: "HTTPS" },
    { id: "instance",   label: "Name" },
    { id: "appearance", label: "Theme" },
    { id: "done",       label: "Done" },
  ]);
  const [stepsReady, setStepsReady] = useState(false);
  useEffect(() => {
    if (config && !stepsReady) {
      if (config.postgres_password_is_default) {
        // Insert DB Password step after Database, before Security
        STEPS.splice(2, 0, { id: "postgres", label: "DB Password" });
      }
      setStepsReady(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);

  const step    = STEPS[stepIdx];
  const isFirst = stepIdx === 0;
  const isLast  = stepIdx === STEPS.length - 1;

  // Next is blocked on the Security step until the form is submitted successfully
  const nextBlocked = mustSecure && step.id === "security";

  // Next is blocked on postgres step if password is partially filled but invalid
  const pgNextBlocked = step.id === "postgres" && pgPw.length > 0 && pgPw.length < 8;

  function finish() {
    if (name.trim()) applyInstanceName(name);
    localStorage.setItem(SETUP_KEY, "true");
    // Full reload so AuthGate re-checks /api/auth/status with the new auth state
    window.location.reload();
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl w-full max-w-[540px] shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="px-6 pt-5 pb-4 border-b border-border shrink-0">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Setup guide · NousViz v{health?.version || "…"}
            </span>
            {/* Hide close button on public deploys until instance is secured */}
            {!mustSecure && (
              <button
                onClick={finish}
                className="text-muted-foreground hover:text-foreground transition-colors"
                title="Skip — finish later in Settings"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          {/* Progress */}
          <div className="flex gap-1">
            {STEPS.map((s, i) => (
              <div
                key={s.id}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  i < stepIdx ? "bg-green-500" : i === stepIdx ? "bg-primary" : "bg-border"
                )}
              />
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground mt-1.5">
            {stepIdx + 1} of {STEPS.length} — {step.label}
            {mustSecure && (
              <span className="ml-2 text-yellow-400">· Set a password to continue</span>
            )}
          </p>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {step.id === "welcome"  && <StepWelcome health={health} checks={checks} />}
          {step.id === "instance" && <StepInstance name={name} setName={setName} />}
          {step.id === "appearance" && <StepAppearance />}
          {step.id === "database" && <StepDatabase check={dbCheck} />}
          {step.id === "postgres" && (
            <StepPostgresPassword
              pgPw={pgPw}
              setPgPw={setPgPw}
            />
          )}
          {step.id === "security" && (
            <StepSecurity
              checks={secChecks}
              config={config}
              pgPw={pgPw}
              onSecured={() => {
                setSecured(true);
                setStepIdx(i => i + 1);
                // Re-fetch config so Done step reflects the new auth state
                fetch("/api/health/config").then(r => r.json()).then(setConfig).catch(() => {});
              }}
            />
          )}
          {step.id === "ssl" && (
            <>
              <StepSsl
                onSetup={() => setShowSslModal(true)}
                onSkip={() => setStepIdx(i => i + 1)}
              />
              {showSslModal && (
                <SslSetupModal
                  onClose={() => setShowSslModal(false)}
                  onComplete={() => { setShowSslModal(false); setStepIdx(i => i + 1); }}
                />
              )}
            </>
          )}
          {step.id === "done"     && <StepDone name={name} checks={checks} />}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex items-center justify-between shrink-0">
          <button
            onClick={() => stepIdx > 0 ? setStepIdx(i => i - 1) : finish()}
            className={cn(
              "h-9 px-4 rounded-lg bg-secondary text-sm text-foreground hover:bg-secondary/80 transition-colors",
              isFirst && "opacity-0 pointer-events-none"
            )}
          >
            <ChevronLeft className="w-4 h-4 inline -mt-0.5 mr-1" />Back
          </button>
          <button
            onClick={isLast ? finish : () => setStepIdx(i => i + 1)}
            disabled={nextBlocked || pgNextBlocked}
            className="h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isLast ? "Finish" : <>Next <ChevronRight className="w-4 h-4" /></>}
          </button>
        </div>
      </div>
    </div>
  );
}
