import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Download, Key, Check, Copy, AlertTriangle, CheckCircle2, ArrowLeft, Globe, Lock, RefreshCw, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import RestrictedUsersGrantBanner from "@/components/plugins/RestrictedUsersGrantBanner";

type Method = "public" | "private-ssh" | "private-https";

export default function InstallPluginPage() {
  const [method, setMethod] = useState<Method | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [pluginId, setPluginId] = useState("");
  const [pluginIdEditing, setPluginIdEditing] = useState(false);

  // Key state
  const [keyStatus, setKeyStatus] = useState<{ has_key: boolean; key_name?: string; match?: "repo" | "host" } | null>(null);
  const [keyChecking, setKeyChecking] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [newPublicKey, setNewPublicKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [keyAdded, setKeyAdded] = useState(false);

  // Connection test
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  // Install state
  const [installing, setInstalling] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  // Auto-derive plugin ID from URL.
  // Backend requires: ^[a-z0-9][a-z0-9_-]{0,63}$ — so we normalize
  // the repo-name slug to match (lowercase, strip `plugin-` prefix
  // case-insensitively). The operator can still override via
  // pluginIdEditing if the manifest's `name:` differs.
  useEffect(() => {
    if (!repoUrl || pluginIdEditing) return;
    const match = repoUrl.match(/[/:]([^/]+?)(?:\.git)?$/);
    if (match) {
      let slug = match[1].toLowerCase();
      if (slug.startsWith("plugin-")) slug = slug.slice(7);
      setPluginId(slug);
    }
  }, [repoUrl, pluginIdEditing]);

  // Auto-check for deploy key when SSH URL changes (debounced)
  const checkTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (method !== "private-ssh" || !repoUrl.trim()) return;
    setKeyStatus(null);
    setTestResult(null);
    setNewPublicKey("");
    setKeyAdded(false);

    clearTimeout(checkTimer.current);
    checkTimer.current = setTimeout(() => {
      setKeyChecking(true);
      apiFetch(`/api/settings/deploy-keys/check?repo_url=${encodeURIComponent(repoUrl.trim())}`)
        .then((r) => r.json())
        .then((d) => setKeyStatus(d))
        .catch(() => setKeyStatus({ has_key: false }))
        .finally(() => setKeyChecking(false));
    }, 500);

    return () => clearTimeout(checkTimer.current);
  }, [repoUrl, method]);

  function urlPlaceholder(): string {
    if (method === "private-ssh") return "git@github.com:your-org/plugin-name.git";
    return "https://github.com/your-org/plugin-name.git";
  }

  async function testConnection() {
    if (!repoUrl.trim() || !pluginId.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      // Use the install endpoint with a dry_run flag — or probe via a test endpoint
      // For now, attempt the probe clone that the install does
      const res = await apiFetch(`/api/plugins/${pluginId.trim()}/install/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repoUrl.trim() }),
      });
      const d = await res.json();
      if (res.ok) {
        setTestResult({ ok: true, message: d.message || `Connected — ${d.display_name} v${d.version}` });
      } else {
        setTestResult({ ok: false, message: d.detail || "Connection failed" });
      }
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : "Connection test failed" });
    }
    setTesting(false);
  }

  async function generateKey() {
    setGenerating(true);
    const host = repoUrl.startsWith("git@")
      ? (repoUrl.split("@")[1]?.split(":")[0] || "github.com")
      : (() => { try { return new URL(repoUrl).hostname; } catch { return "github.com"; } })();
    try {
      const res = await apiFetch("/api/settings/deploy-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `${pluginId || "plugin"} (${host})`, host, repo_url: repoUrl.trim() }),
      });
      if (res.ok) {
        const d = await res.json();
        setNewPublicKey(d.public_key);
        setKeyStatus({ has_key: true, key_name: d.name, match: "repo" });
      }
    } catch (e) {
      console.error("Key generation failed:", e);
    }
    setGenerating(false);
  }

  async function install() {
    if (!repoUrl.trim() || !pluginId.trim()) return;
    setInstalling(true);
    setResult(null);
    try {
      const body: Record<string, string> = {};
      if (method !== "public") body.repository_url = repoUrl.trim();
      const res = await apiFetch(`/api/plugins/${pluginId.trim()}/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Install failed");
      setResult({ ok: true, message: "Plugin installed successfully!" });
      window.dispatchEvent(new CustomEvent("nousviz:plugins-changed"));
    } catch (e: unknown) {
      setResult({ ok: false, message: e instanceof Error ? e.message : "Install failed" });
    }
    setInstalling(false);
  }

  const readyToInstall = repoUrl.trim() && pluginId.trim() && (
    method === "public" ||
    method === "private-https" ||
    (method === "private-ssh" && (keyStatus?.has_key || (newPublicKey && keyAdded)))
  );

  // Determine SSH key state for display
  const keyIsRepoScoped = keyStatus?.has_key && keyStatus.match === "repo";
  const keyIsHostOnly = keyStatus?.has_key && keyStatus.match === "host";

  return (
    <div className="max-w-[700px] space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/marketplace" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="font-display text-lg text-foreground">Install Plugin</h1>
          <p className="text-sm text-muted-foreground font-body">Install a plugin from a Git repository.</p>
        </div>
      </div>

      {/* Method selector */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h3 className="font-display text-sm text-foreground">How would you like to install?</h3>
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
          {([
            { id: "public" as Method, icon: Globe, label: "Public Repository", desc: "Open-source plugin on GitHub/GitLab" },
            { id: "private-ssh" as Method, icon: Lock, label: "Private (SSH Key)", desc: "Uses a deploy key for authentication" },
            { id: "private-https" as Method, icon: Key, label: "Private (Token)", desc: "Uses a GitHub personal access token" },
          ]).map(opt => (
            <button key={opt.id} onClick={() => { setMethod(opt.id); setKeyStatus(null); setNewPublicKey(""); setKeyAdded(false); setResult(null); setTestResult(null); }}
              className={cn(
                "p-4 rounded-lg border text-left transition-all",
                method === opt.id ? "border-primary bg-primary/5 ring-1 ring-primary/20" : "border-border hover:border-primary/30"
              )}>
              <opt.icon className={cn("w-5 h-5 mb-2", method === opt.id ? "text-primary" : "text-muted-foreground")} />
              <p className="text-sm font-medium text-foreground">{opt.label}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{opt.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Repository URL */}
      {method && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-4">
          <h3 className="font-display text-sm text-foreground">Repository</h3>

          {method === "private-https" && (
            <div className="bg-secondary/30 rounded-md p-3 text-[11px] text-muted-foreground space-y-1">
              <p>Requires a GitHub token configured in <Link to="/settings/security" className="text-primary hover:underline">Settings → Security → Git Access Token</Link>.</p>
              <p>The token is injected automatically when cloning from GitHub HTTPS URLs.</p>
            </div>
          )}

          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Repository URL</label>
            <input
              value={repoUrl}
              onChange={e => { setRepoUrl(e.target.value); setResult(null); }}
              placeholder={urlPlaceholder()}
              autoComplete="off"
              className="w-full h-10 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono-deck"
            />
          </div>

          {pluginId && !pluginIdEditing && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Plugin ID:</span>
              <span className="text-foreground font-medium">{pluginId}</span>
              <button onClick={() => setPluginIdEditing(true)} className="text-primary hover:underline text-[10px]">edit</button>
            </div>
          )}
          {pluginIdEditing && (
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Plugin ID (override)</label>
              <div className="flex items-center gap-2">
                <input value={pluginId} onChange={e => setPluginId(e.target.value)} autoComplete="off"
                  className="w-full sm:w-64 h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
                <button onClick={() => setPluginIdEditing(false)} className="text-xs text-primary hover:underline">done</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SSH key setup */}
      {method === "private-ssh" && repoUrl && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-4">
          <h3 className="font-display text-sm text-foreground">SSH Authentication</h3>

          {/* Checking state */}
          {keyChecking && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Checking for deploy key…
            </div>
          )}

          {/* Key found — repo-scoped (best case) */}
          {keyIsRepoScoped && !newPublicKey && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 px-3 py-2 rounded-md bg-green-500/5 border border-green-500/20 text-xs">
                <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
                <span className="text-green-400">Deploy key found for this repo: <strong>{keyStatus?.key_name}</strong></span>
              </div>
              {/* Test button */}
              <button onClick={testConnection} disabled={testing}
                className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50">
                {testing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Key className="w-3 h-3" />}
                {testing ? "Testing…" : "Test Connection"}
              </button>
            </div>
          )}

          {/* Key found — host-level only (may not work) */}
          {keyIsHostOnly && !newPublicKey && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-md bg-yellow-500/5 border border-yellow-500/20 text-xs">
                <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0" />
                <div>
                  <p className="text-yellow-400">A deploy key exists for <strong>{keyStatus?.key_name}</strong>, but it's scoped to a different repo.</p>
                  <p className="text-muted-foreground mt-1">Test the connection to check if it works, or generate a new key for this specific repo.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={testConnection} disabled={testing}
                  className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50">
                  {testing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Key className="w-3 h-3" />}
                  {testing ? "Testing…" : "Test Connection"}
                </button>
                <button onClick={generateKey} disabled={generating}
                  className="h-8 px-3 rounded-md bg-primary text-xs text-white hover:bg-primary/90 transition-colors flex items-center gap-1.5 disabled:opacity-50">
                  <Key className="w-3 h-3" />
                  {generating ? "Generating…" : "Generate New Key for This Repo"}
                </button>
              </div>
            </div>
          )}

          {/* No key found */}
          {keyStatus && !keyStatus.has_key && !newPublicKey && !keyChecking && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 px-3 py-2 rounded-md bg-yellow-500/5 border border-yellow-500/20 text-xs">
                <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0" />
                <span className="text-yellow-400">No deploy key found. Generate one to authenticate with this repository.</span>
              </div>
              <button onClick={generateKey} disabled={generating}
                className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-2">
                <Key className="w-3.5 h-3.5" /> {generating ? "Generating…" : "Generate SSH Key"}
              </button>
            </div>
          )}

          {/* Test result + inline install */}
          {testResult && (
            <div className={cn("rounded-md text-xs",
              testResult.ok ? "bg-green-500/5 border border-green-500/20" : "bg-red-500/5 border border-red-500/20"
            )}>
              <div className="flex items-center gap-3 px-3 py-2">
                {testResult.ok ? <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
                <span className={testResult.ok ? "text-green-400" : "text-red-400"}>{testResult.message}</span>
              </div>
              {testResult.ok && !result?.ok && (
                <div className="px-3 pb-3">
                  <button onClick={install} disabled={installing}
                    className="h-10 w-full rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
                    <Download className="w-4 h-4" /> {installing ? "Installing…" : `Install ${testResult.message.split(" — ")[1] || pluginId}`}
                  </button>
                </div>
              )}
              {result && (
                <div className={cn("mx-3 mb-3 flex items-start gap-3 px-3 py-3 rounded-md",
                  result.ok ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                )}>
                  {result.ok ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                  <div>
                    <p>{result.message}</p>
                    {result.ok && (
                      <div className="mt-1 flex items-center gap-3">
                        <Link to={`/plugin/${pluginId}`} className="text-primary hover:underline">Go to plugin →</Link>
                        <Link to="/docs/plugin-sync-scheduling" className="text-primary/80 hover:underline text-xs">Set up scheduling</Link>
                      </div>
                    )}
                    {result.ok && pluginId && (
                      <RestrictedUsersGrantBanner pluginSlug={pluginId.trim()} />
                    )}
                    {!result.ok && result.message.includes("tag") && <p className="text-muted-foreground mt-1">Ensure the repo has a Git tag matching the version (e.g. v1.0.0).</p>}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Newly generated key */}
          {newPublicKey && (
            <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-4 space-y-3">
              <p className="text-xs text-green-400 font-medium">SSH key generated. Add it to your repository:</p>
              <ol className="text-xs text-muted-foreground space-y-1.5 list-decimal list-inside">
                <li>Copy the public key below</li>
                <li>Go to your repository → <strong className="text-foreground">Settings → Deploy keys → Add deploy key</strong></li>
                <li>Paste the key, name it anything, save (read-only is fine)</li>
              </ol>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-background px-2 py-1.5 rounded text-[11px] font-mono-deck text-foreground truncate select-all">{newPublicKey}</code>
                <button onClick={() => { navigator.clipboard.writeText(newPublicKey); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                  className="shrink-0 h-7 px-2.5 rounded bg-secondary text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-1">
                  {copied ? <><Check className="w-3 h-3 text-green-400" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
                </button>
              </div>
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" checked={keyAdded} onChange={e => setKeyAdded(e.target.checked)} className="rounded border-border" />
                I've added this key to my repository
              </label>
              {keyAdded && (
                <button onClick={testConnection} disabled={testing}
                  className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground hover:bg-secondary/80 transition-colors flex items-center gap-1.5 disabled:opacity-50">
                  {testing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                  {testing ? "Verifying…" : "Verify Connection"}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Install — for public and HTTPS methods (SSH has inline install after test) */}
      {method && method !== "private-ssh" && repoUrl && readyToInstall && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-4">
          <button onClick={install} disabled={installing}
            className="h-10 w-full rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            <Download className="w-4 h-4" /> {installing ? "Installing…" : "Install Plugin"}
          </button>
          <p className="text-[10px] text-muted-foreground text-center">
            Repo must have a Git tag matching the version in plugin.yaml (e.g. v1.0.0).
          </p>
          {result && (
            <div className={cn("flex items-start gap-3 px-3 py-3 rounded-md text-xs",
              result.ok ? "bg-green-500/5 border border-green-500/20 text-green-400" : "bg-red-500/5 border border-red-500/20 text-red-400"
            )}>
              {result.ok ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
              <div>
                <p>{result.message}</p>
                {result.ok && (
                  <div className="mt-1 flex items-center gap-3">
                    <Link to={`/plugin/${pluginId}`} className="text-primary hover:underline">Go to plugin →</Link>
                    <Link to="/docs/plugin-sync-scheduling" className="text-primary/80 hover:underline text-xs">Set up scheduling</Link>
                  </div>
                )}
                {result.ok && pluginId && (
                  <RestrictedUsersGrantBanner pluginSlug={pluginId.trim()} />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <p className="text-[10px] text-muted-foreground text-center">
        Need help? Read the <Link to="/docs/private-plugins" className="text-primary hover:underline">Private Plugins Guide</Link>.
      </p>
    </div>
  );
}
