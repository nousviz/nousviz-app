import { apiFetch } from "@/lib/api";
import { useState, useEffect, useRef } from "react";
import { Database, Key, Globe, Server, Sun, Moon, BarChart3, Pipette, Eye, EyeOff, Rocket, Copy, Check, Trash2, Plus, Shield, Mail, ChevronRight, User, BookOpen, ExternalLink, Wrench } from "lucide-react";
import LogsPanel from "@/components/settings/LogsPanel";
import MaintenancePanel from "@/components/settings/MaintenancePanel";
import SslSetupModal from "@/components/SslSetupModal";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useTheme } from "@/hooks/useTheme";
import type { ColorPalette, CustomColors } from "@/hooks/useTheme";
import { useCompactNumbers } from "@/hooks/useCompactNumbers";
import { cn, formatRelativeTime, formatAbsoluteTime } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import SetupWizard, { SETUP_KEY } from "@/components/SetupWizard";
import { ScrollableTabs } from "@/components/ui/ScrollableTabs";

// ── Palette definitions ──────────────────────────────────────────────

const COLOR_FIELDS: { key: keyof CustomColors; label: string }[] = [
  { key: "background", label: "Background" },
  { key: "card",       label: "Card surface" },
  { key: "sidebar",    label: "Sidebar" },
  { key: "primary",    label: "Primary / accent" },
  { key: "secondary",  label: "Secondary surface" },
  { key: "foreground", label: "Text" },
  { key: "muted",      label: "Muted surface" },
  { key: "border",     label: "Border" },
];

interface PaletteOption {
  id: ColorPalette;
  label: string;
  sub: string;
  swatches: string[];
}

const PALETTES: PaletteOption[] = [
  {
    id: "default-light",
    label: "Default Light",
    sub: "Clean · Blue accent",
    swatches: ["#f8f8f8", "#ffffff", "#3f9fff"],
  },
  {
    id: "default-dark",
    label: "Default Dark",
    sub: "Clean · Blue accent",
    swatches: ["#0a0a0f", "#111117", "#3f9fff"],
  },
  {
    id: "sovereign",
    label: "Sovereign",
    sub: "Deep space · Powder blue",
    swatches: ["#131316", "#1f1f22", "#a3c9ff"],
  },
  {
    id: "nord",
    label: "Nord",
    sub: "Arctic steel · Muted blue",
    swatches: ["#2e3440", "#3b4252", "#88c0d0"],
  },
  {
    id: "custom",
    label: "Custom",
    sub: "Your own colors",
    swatches: [],
  },
];

// ── Section card (always visible) ────────────────────────────────────

function Section({ icon: Icon, label, children }: {
  icon: React.ElementType;
  label: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card rounded-lg border border-border p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
        <h3 className="font-display text-sm text-foreground">{label}</h3>
      </div>
      {children}
    </div>
  );
}

function Field({ label, desc, children }: { label: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div className="min-w-0">
        <p className="text-sm text-foreground font-body">{label}</p>
        {desc && <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}


function PasswordInput({ placeholder, value, onChange }: { placeholder?: string; value?: string; onChange?: (v: string) => void }) {
  const [show, setShow] = useState(false);
  const controlled = value !== undefined;
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        placeholder={placeholder ?? "••••••••"}
        {...(controlled ? { value, onChange: e => onChange?.(e.target.value) } : {})}
        className="h-8 pl-3 pr-9 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56 font-body"
      />
      <button
        type="button"
        onClick={() => setShow(s => !s)}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}

// ── API Keys section ─────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string | null;
  last_used_at: string | null;
}

function ApiKeysSection() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [revealed, setRevealed] = useState<{ id: string; key: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function load() {
    apiFetch("/api/settings/api-keys")
      .then(r => r.json())
      .then(d => setKeys(Array.isArray(d) ? d : []))
      .catch(() => setKeys([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await apiFetch("/api/settings/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      const data = await res.json();
      if (data.key) {
        setRevealed({ id: data.id, key: data.key });
        setNewName("");
        load();
      }
    } finally {
      setCreating(false);
    }
  }

  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  async function revoke(id: string) {
    if (confirmRevoke !== id) {
      setConfirmRevoke(id);
      return;
    }
    setConfirmRevoke(null);
    await apiFetch(`/api/settings/api-keys/${id}`, { method: "DELETE" });
    setKeys(prev => prev.filter(k => k.id !== id));
    if (revealed?.id === id) setRevealed(null);
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function fmtDate(iso: string | null) {
    if (!iso) return "Never";
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  return (
    <Section icon={Key} label="API Keys" desc="Keys for MCP server and external API access">
      <p className="text-xs text-muted-foreground font-body -mt-1">
        Keys grant full API access. Treat them like passwords — they're stored hashed and shown once.
      </p>

      {/* Revealed key banner */}
      {revealed && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-3 space-y-2">
          <p className="text-xs font-body text-green-400 font-medium">Key created — copy it now. It won't be shown again.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs font-mono-deck text-foreground bg-background rounded px-2 py-1.5 border border-border truncate">
              {revealed.key}
            </code>
            <button
              onClick={() => copy(revealed.key)}
              className="h-7 px-2.5 rounded bg-secondary flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <button onClick={() => setRevealed(null)} className="text-[11px] text-muted-foreground hover:text-foreground transition-colors">Dismiss</button>
        </div>
      )}

      {/* Key list */}
      {loading ? (
        <p className="text-xs text-muted-foreground font-body">Loading…</p>
      ) : keys.length === 0 ? (
        <p className="text-xs text-muted-foreground font-body">No API keys yet.</p>
      ) : (
        <div className="rounded-lg border border-border divide-y divide-border">
          {keys.map(k => (
            <div key={k.id} className="flex items-center justify-between px-4 py-3 gap-4">
              <div className="min-w-0">
                <p className="text-sm text-foreground font-body">{k.name}</p>
                <p className="text-xs font-mono-deck text-muted-foreground mt-0.5">
                  {k.key_prefix}••••••••••••••••
                  <span className="font-body ml-2 text-muted-foreground/60">
                    Created {fmtDate(k.created_at)}
                    {k.last_used_at ? ` · Last used ${fmtDate(k.last_used_at)}` : " · Never used"}
                  </span>
                </p>
              </div>
              <button
                onClick={() => revoke(k.id)}
                onBlur={() => setConfirmRevoke(null)}
                className={cn(
                  "text-xs font-body px-2 py-1 rounded transition-colors shrink-0 flex items-center gap-1",
                  confirmRevoke === k.id
                    ? "bg-red-500/10 text-red-400 border border-red-500/30"
                    : "text-muted-foreground hover:text-red-400"
                )}
                title={confirmRevoke === k.id ? "Click again to confirm" : "Revoke key"}
              >
                <Trash2 className="w-3.5 h-3.5" />
                {confirmRevoke === k.id && <span>Confirm revoke</span>}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create new */}
      <div className="flex items-center gap-2 pt-1">
        <input
          ref={inputRef}
          type="text"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => e.key === "Enter" && create()}
          placeholder="Key name (e.g. MCP Server)"
          className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary flex-1 font-body"
        />
        <button
          onClick={create}
          disabled={creating || !newName.trim()}
          className="h-8 px-3 rounded-md bg-primary text-xs text-white font-body flex items-center gap-1.5 hover:bg-primary/90 transition-colors disabled:opacity-50 shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />{creating ? "Creating…" : "Create"}
        </button>
      </div>
    </Section>
  );
}

// ── Database section ─────────────────────────────────────────────────

interface DbConfig {
  host: string;
  port: string;
  db: string;
  user: string;
  password: string;
}

function DatabaseSection() {
  const [cfg, setCfg] = useState<DbConfig>({ host: "localhost", port: "5432", db: "nousviz", user: "nousviz", password: "" });
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    apiFetch("/api/settings/database")
      .then(r => r.json())
      .then(d => setCfg(prev => ({ ...prev, host: d.host, port: d.port, db: d.db, user: d.user })))
      .catch(() => {});
  }, []);

  async function save() {
    setSaving(true);
    setResult(null);
    try {
      const res = await apiFetch("/api/settings/database", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ host: cfg.host, port: parseInt(cfg.port), db: cfg.db, user: cfg.user, password: cfg.password || undefined }),
      });
      const data = await res.json();
      setResult(data.ok
        ? { ok: true, message: `Connected — ${data.version}` }
        : { ok: false, message: data.error ?? "Connection failed" }
      );
    } catch {
      setResult({ ok: false, message: "Could not reach API" });
    } finally {
      setSaving(false);
    }
  }

  function field(key: keyof DbConfig, label: string, opts?: { type?: string; placeholder?: string }) {
    return (
      <Field label={label}>
        {opts?.type === "password" ? (
          <PasswordInput
            value={cfg[key]}
            onChange={v => { setCfg(p => ({ ...p, [key]: v })); setResult(null); }}
            placeholder={opts.placeholder}
          />
        ) : (
          <input
            type={opts?.type ?? "text"}
            value={cfg[key]}
            onChange={e => { setCfg(p => ({ ...p, [key]: e.target.value })); setResult(null); }}
            placeholder={opts?.placeholder}
            className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56 font-body"
          />
        )}
      </Field>
    );
  }

  return (
    <Section icon={Database} label="Core Database">
      <p className="text-xs text-muted-foreground font-body leading-relaxed">
        PostgreSQL — the core database. It stores users, dashboards, fusions, alerts, plugin settings, and other platform data.
      </p>
      <p className="text-xs text-muted-foreground font-body leading-relaxed">
        Other databases (e.g. ClickHouse) are provided by utility plugins and configured in each utility's own Settings page under <Link to="/plugins" className="text-primary hover:text-primary/80 transition-colors">Installed</Link>.
      </p>
      {field("host", "Host")}
      {field("port", "Port", { type: "number" })}
      {field("db", "Database")}
      {field("user", "User")}
      {field("password", "Password", { type: "password", placeholder: "Leave blank to keep existing" })}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={save}
          disabled={saving}
          className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save & reconnect"}
        </button>
        {result && (
          <span className={cn("text-xs font-body", result.ok ? "text-green-400" : "text-red-400")}>
            {result.ok ? "✓" : "✗"} {result.message}
          </span>
        )}
      </div>
    </Section>
  );
}

// ── Main ─────────────────────────────────────────────────────────────

const INSTANCE_NAME_KEY = "nousviz:instance_name";

function applyInstanceName(name: string) {
  const trimmed = name.trim() || "NousViz";
  document.title = `${trimmed} — Data Intelligence Platform`;
  localStorage.setItem(INSTANCE_NAME_KEY, trimmed);
}

// Settings tab bar — config only. v0.8.3 (P113): Connections removed from
// the tab bar because the sidebar already has a top-level Connections entry;
// duplicating it here was navigation noise. The /settings/connections URL
// still resolves via the render block below so existing bookmarks work.
// v0.8.2 note: Jobs and Logs live under /system (System Status page), not
// here — they're operator observability, not configuration.
const BASE_TABS = [
  { id: "general", label: "General", icon: Server },
  { id: "profile", label: "Profile", icon: User },
  { id: "security", label: "Security", icon: Shield },
  { id: "email", label: "Email", icon: Mail },
  { id: "data", label: "Data", icon: Database },
  { id: "maintenance", label: "Maintenance", icon: Wrench },
] as const;

type SettingsTab = string;

// ── Profile panel ───────────────────────────────────────────────────

function ProfilePanel() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [createdAt, setCreatedAt] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPw, setShowNewPw] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [avatarResult, setAvatarResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [pwResult, setPwResult] = useState<{ ok: boolean; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiFetch("/api/auth/me").then(r => r.ok ? r.json() : null).then(u => {
      if (u) {
        setName(u.name || "");
        setEmail(u.email || "");
        setRole(u.role || "");
        setCreatedAt(u.created_at || "");
        setAvatarUrl(u.avatar_url || null);
      }
    }).catch(() => {});
  }, []);

  async function handleAvatarUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setAvatarResult({ ok: false, message: "Image must be under 2MB." });
      return;
    }
    setUploading(true);
    setAvatarResult(null);
    const form = new FormData();
    form.append("avatar", file);
    const res = await apiFetch("/api/auth/me/avatar", { method: "POST", body: form });
    setUploading(false);
    if (res.ok) {
      const d = await res.json();
      setAvatarUrl(d.avatar_url + "?t=" + Date.now());
      setAvatarResult({ ok: true, message: "Photo saved." });
    } else {
      const d = await res.json().catch(() => ({}));
      setAvatarResult({ ok: false, message: d.detail || "Failed to upload." });
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleRemoveAvatar() {
    setUploading(true);
    const res = await apiFetch("/api/auth/me/avatar", { method: "DELETE" });
    setUploading(false);
    if (res.ok) {
      setAvatarUrl(null);
      setAvatarResult({ ok: true, message: "Photo removed." });
    }
  }

  async function handleSaveName() {
    setSaving(true);
    setResult(null);
    const res = await apiFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    setSaving(false);
    if (res.ok) {
      setResult({ ok: true, message: "Name updated." });
    } else {
      const d = await res.json().catch(() => ({}));
      setResult({ ok: false, message: d.detail || "Failed to update." });
    }
  }

  async function handleChangePassword() {
    setPwResult(null);
    if (newPassword.length < 8) {
      setPwResult({ ok: false, message: "Password must be at least 8 characters." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwResult({ ok: false, message: "Passwords don't match." });
      return;
    }
    setSaving(true);
    const res = await apiFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: newPassword }),
    });
    setSaving(false);
    if (res.ok) {
      setPwResult({ ok: true, message: "Password changed." });
      setNewPassword("");
      setConfirmPassword("");
    } else {
      const d = await res.json().catch(() => ({}));
      setPwResult({ ok: false, message: d.detail || "Failed to change password." });
    }
  }

  const pwTooShort = newPassword.length > 0 && newPassword.length < 8;
  const pwNoMatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  return (
    <div className="space-y-6">
      {/* Avatar */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h4 className="font-display text-sm text-foreground">Profile Picture</h4>
        <div className="flex items-center gap-5">
          <div className="relative group">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="w-16 h-16 rounded-full object-cover border-2 border-border" />
            ) : (
              <span className="w-16 h-16 rounded-full bg-primary/20 text-primary text-xl font-semibold flex items-center justify-center border-2 border-border">
                {(name || email || "?")[0].toUpperCase()}
              </span>
            )}
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {uploading ? "Uploading..." : "Upload Photo"}
              </button>
              {avatarUrl && (
                <button
                  onClick={handleRemoveAvatar}
                  disabled={uploading}
                  className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-red-400 disabled:opacity-50 transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground">JPEG, PNG, WebP, or GIF. Max 2MB. Saves automatically.</p>
            {avatarResult && (
              <p className={cn("text-[11px]", avatarResult.ok ? "text-green-400" : "text-red-400")}>{avatarResult.message}</p>
            )}
            <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={handleAvatarUpload} className="hidden" />
          </div>
        </div>
      </div>

      {/* Account info */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h4 className="font-display text-sm text-foreground">Account</h4>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Email</label>
            <p className="text-sm text-foreground">{email}</p>
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Role</label>
            <span className={cn(
              "inline-block px-2 py-0.5 rounded-full border text-[11px]",
              role === "superadmin" ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
              : role === "admin" ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
              : role === "analyst" ? "bg-green-500/10 text-green-400 border-green-500/30"
              : "bg-secondary text-muted-foreground border-border"
            )}>{role}</span>
          </div>
          {createdAt && (
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Member Since</label>
              <p className="text-sm text-foreground">{new Date(createdAt).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</p>
            </div>
          )}
        </div>
      </div>

      {/* Display name */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h4 className="font-display text-sm text-foreground">Display Name</h4>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Your name"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <button
            onClick={handleSaveName}
            disabled={saving || !name.trim()}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
        {result && (
          <p className={cn("text-xs", result.ok ? "text-green-400" : "text-red-400")}>{result.message}</p>
        )}
      </div>

      {/* Change password */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h4 className="font-display text-sm text-foreground">Change Password</h4>
        <div className="space-y-3 max-w-sm">
          <div className="relative">
            <input
              type={showNewPw ? "text" : "password"}
              value={newPassword}
              onChange={e => { setNewPassword(e.target.value); setPwResult(null); }}
              placeholder="New password"
              autoComplete="new-password"
              className="w-full h-9 px-3 pr-10 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button type="button" onClick={() => setShowNewPw(p => !p)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              {showNewPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          {pwTooShort && <p className="text-[11px] text-yellow-400 ml-1">Must be at least 8 characters</p>}
          <input
            type="password"
            value={confirmPassword}
            onChange={e => { setConfirmPassword(e.target.value); setPwResult(null); }}
            placeholder="Confirm new password"
            autoComplete="new-password"
            className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          {pwNoMatch && <p className="text-[11px] text-yellow-400 ml-1">Passwords don't match</p>}
        </div>
        {pwResult && (
          <p className={cn("text-xs", pwResult.ok ? "text-green-400" : "text-red-400")}>{pwResult.message}</p>
        )}
        <button
          onClick={handleChangePassword}
          disabled={saving || newPassword.length < 8 || newPassword !== confirmPassword}
          className="h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
        >
          Change Password
        </button>
      </div>
    </div>
  );
}

// ── Git token section ────────────────────────────────────────────────

function GitTokenSection() {
  const [tokenSet, setTokenSet] = useState(false);
  const [tokenPreview, setTokenPreview] = useState("");
  const [newToken, setNewToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    apiFetch("/api/settings/git").then(r => r.json()).then(d => {
      setTokenSet(d.github_token_set);
      setTokenPreview(d.github_token_preview || "");
    }).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setResult(null);
    const res = await apiFetch("/api/settings/git", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ github_token: newToken }),
    });
    setSaving(false);
    if (res.ok) {
      setTokenSet(!!newToken);
      setNewToken("");
      setResult({ ok: true, message: "Token saved." });
    } else {
      const d = await res.json().catch(() => ({}));
      setResult({ ok: false, message: d.detail || "Failed to save." });
    }
  }

  return (
    <Section icon={Key} label="Git Access Token" desc="For installing plugins from private repositories">
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">
          {tokenSet
            ? `GitHub token configured (${tokenPreview}). Used automatically when installing from private HTTPS repos.`
            : "No GitHub token configured. Private HTTPS repos will fail to clone. SSH repos use the server's SSH key."}
        </p>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <input
              type="password"
              value={newToken}
              onChange={e => { setNewToken(e.target.value); setResult(null); }}
              placeholder={tokenSet ? "Replace token..." : "ghp_... or github_pat_..."}
              autoComplete="off"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <button onClick={handleSave} disabled={saving || !newToken.trim()}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors shrink-0">
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
        {result && <p className={cn("text-xs", result.ok ? "text-green-400" : "text-red-400")}>{result.message}</p>}
      </div>
    </Section>
  );
}

// ── Deploy Keys section ──────────────────────────────────────────────

interface DeployKey {
  id: string;
  name: string;
  host: string;
  public_key: string;
  fingerprint: string;
  created_at: string;
  // B206 (v0.9.6): repo_url and creator details surfaced in the table.
  repo_url: string | null;
  created_by: { id: string; name: string | null; email: string | null } | null;
}

function DeployKeysSection() {
  const [keys, setKeys] = useState<DeployKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createName, setCreateName] = useState("");
  const [createHost, setCreateHost] = useState("github.com");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<{ public_key: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; detail: string } | null>(null);

  function load() {
    apiFetch("/api/settings/deploy-keys").then(r => r.json()).then(d => {
      setKeys(d.keys || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleCreate() {
    if (!createName.trim()) return;
    setCreating(true);
    const res = await apiFetch("/api/settings/deploy-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: createName.trim(), host: createHost }),
    });
    setCreating(false);
    if (res.ok) {
      const data = await res.json();
      setNewKey(data);
      setCreateName("");
      load();
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this deploy key?")) return;
    await apiFetch(`/api/settings/deploy-keys/${id}`, { method: "DELETE" });
    load();
  }

  async function handleTest(id: string) {
    setTestResult(null);
    const res = await apiFetch(`/api/settings/deploy-keys/${id}/test`, { method: "POST" });
    const d = await res.json();
    setTestResult({ id, ok: d.ok, detail: d.detail || "" });
    setTimeout(() => setTestResult(null), 8000);
  }

  function copyKey(key: string) {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Section icon={Key} label="Deploy Keys (SSH)" desc="For installing plugins from private Git repositories">
      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Generate an SSH key pair, then add the public key as a <strong className="text-foreground">deploy key</strong> on your GitHub/GitLab repository.
          NousViz uses the private key to clone during plugin install.
        </p>

        {/* Generate form */}
        <div className="flex items-end gap-2 flex-wrap">
          <div className="flex-1 min-w-[150px]">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Name</label>
            <input value={createName} onChange={e => setCreateName(e.target.value)} placeholder="e.g. GitHub Deploy" autoComplete="off"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div className="w-40">
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Host</label>
            <select value={createHost} onChange={e => setCreateHost(e.target.value)}
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50">
              <option value="github.com">github.com</option>
              <option value="gitlab.com">gitlab.com</option>
              <option value="bitbucket.org">bitbucket.org</option>
            </select>
          </div>
          <button onClick={handleCreate} disabled={creating || !createName.trim()}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors shrink-0">
            {creating ? "Generating..." : "Generate Key"}
          </button>
        </div>

        {/* Newly generated key — show public key for copying */}
        {newKey && (
          <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3 space-y-2">
            <p className="text-xs text-green-400 font-medium">Key generated! Copy the public key below and add it as a deploy key on your repository.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-background px-2 py-1.5 rounded text-[11px] font-mono-deck text-foreground truncate select-all">{newKey.public_key}</code>
              <button onClick={() => copyKey(newKey.public_key)}
                className="shrink-0 h-7 px-2.5 rounded bg-secondary text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-1">
                {copied ? <><Check className="w-3 h-3 text-green-400" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
              </button>
            </div>
            <button onClick={() => setNewKey(null)} className="text-[10px] text-muted-foreground hover:text-foreground">Dismiss</button>
          </div>
        )}

        {/* Existing keys (B206 v0.9.6: surface repo_url, creator, and
            "host-only — unused" warning for legacy rows.) */}
        {!loading && keys.length > 0 && (
          <div className="space-y-1.5">
            {keys.map(k => {
              const hostOnly = !k.repo_url || k.repo_url.trim() === "";
              const creatorLabel =
                k.created_by?.name ||
                k.created_by?.email ||
                "<unknown>";
              return (
                <div
                  key={k.id}
                  className="px-3 py-2.5 rounded-md bg-secondary/30 text-xs space-y-1.5"
                >
                  {/* Top row: name · host · fingerprint · actions */}
                  <div className="flex items-center gap-2">
                    <span className="text-foreground font-medium">{k.name}</span>
                    <span className="text-muted-foreground font-mono-deck">{k.host}</span>
                    <span className="text-muted-foreground font-mono-deck truncate max-w-[160px]">
                      {k.fingerprint}
                    </span>
                    <span className="flex-1" />
                    <button
                      onClick={() => handleTest(k.id)}
                      className="text-muted-foreground hover:text-foreground text-[10px]"
                    >
                      Test
                    </button>
                    {testResult?.id === k.id && (
                      <span
                        className={cn(
                          "text-[10px]",
                          testResult.ok ? "text-green-400" : "text-red-400"
                        )}
                      >
                        {testResult.ok ? "Connected" : testResult.detail.slice(0, 50)}
                      </span>
                    )}
                    <button
                      onClick={() => copyKey(k.public_key)}
                      className="text-muted-foreground hover:text-foreground text-[10px]"
                    >
                      Copy Key
                    </button>
                    <button
                      onClick={() => handleDelete(k.id)}
                      className="text-muted-foreground hover:text-red-400"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Detail row: repo URL · creator · created */}
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    {hostOnly ? (
                      <span
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/10 text-amber-400"
                        title="This key isn't reachable by the resolver since v0.9.5.9. Add a repo_url to use it, or delete it."
                      >
                        Host-only — unused
                      </span>
                    ) : (
                      <code className="font-mono-deck text-foreground/70 truncate max-w-[280px]">
                        {k.repo_url}
                      </code>
                    )}
                    <span className="flex-1" />
                    <span title={k.created_by?.email ?? undefined}>
                      Created by{" "}
                      <span
                        className={cn(
                          k.created_by ? "text-foreground/80" : "text-muted-foreground italic"
                        )}
                      >
                        {creatorLabel}
                      </span>
                    </span>
                    <span title={k.created_at ? formatAbsoluteTime(k.created_at) : undefined}>
                      {k.created_at ? formatRelativeTime(k.created_at) : "—"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!loading && keys.length === 0 && !newKey && (
          <p className="text-[11px] text-muted-foreground">No deploy keys configured. Generate one to install plugins from private repositories.</p>
        )}
      </div>
    </Section>
  );
}
// B252 (v0.9.11.2): AuthModeSection removed; multi-user is the only auth mode.

// ── Email / SMTP settings panel ─────────��────────────────────────────

function EmailSettingsPanel() {
  const [host, setHost] = useState("");
  const [port, setPort] = useState("587");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [fromName, setFromName] = useState("NousViz");
  const [useTls, setUseTls] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/api/settings/email").then(r => r.json()).then(d => {
      setHost(d.host || "");
      setPort(d.port || "587");
      setUsername(d.username || "");
      setFromAddress(d.from_address || "");
      setFromName(d.from_name || "NousViz");
      setUseTls(d.use_tls === "true" || d.use_tls === true);
      setConfigured(!!d.configured);
    }).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setResult(null);
    const res = await apiFetch("/api/settings/email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        host, port: parseInt(port) || 587, username,
        password: password || null,
        from_address: fromAddress, from_name: fromName, use_tls: useTls,
      }),
    });
    setSaving(false);
    if (res.ok) {
      setConfigured(true);
      setPassword("");
      setResult({ ok: true, message: "SMTP settings saved." });
    } else {
      const d = await res.json().catch(() => ({}));
      setResult({ ok: false, message: d.detail || "Failed to save." });
    }
  }

  async function handleTest() {
    setTesting(true);
    setResult(null);
    const res = await apiFetch("/api/settings/email/test", { method: "POST" });
    const d = await res.json().catch(() => ({}));
    setTesting(false);
    if (d.ok) {
      setResult({ ok: true, message: `Test email sent to ${d.sent_to}.` });
    } else {
      setResult({ ok: false, message: d.error || "Test failed." });
    }
  }

  return (
    <div className="space-y-6">
      {/* Status */}
      <div className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-lg border",
        configured ? "bg-green-500/5 border-green-500/20" : "bg-yellow-500/5 border-yellow-500/20"
      )}>
        <Mail className={cn("w-4 h-4 shrink-0", configured ? "text-green-400" : "text-yellow-400")} />
        <div>
          <p className="text-sm text-foreground font-medium">
            {configured ? "SMTP Configured" : "SMTP Not Configured"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {configured
              ? "Email delivery is active for invites, alerts, and notifications."
              : "Invite links must be copied manually. Configure SMTP to enable email delivery."}
          </p>
        </div>
      </div>

      {/* Config form */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <h4 className="font-display text-sm text-foreground">SMTP Configuration</h4>

        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Host</label>
            <input value={host} onChange={e => setHost(e.target.value)} placeholder="smtp.example.com"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Port</label>
            <input value={port} onChange={e => setPort(e.target.value)} placeholder="587"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} placeholder="apikey or username"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Password</label>
            <div className="relative">
              <input type={showPassword ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)}
                placeholder={configured ? "••••••• (unchanged)" : "SMTP password or API key"}
                className="w-full h-9 px-3 pr-10 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
              <button type="button" onClick={() => setShowPassword(p => !p)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">From Address</label>
            <input value={fromAddress} onChange={e => setFromAddress(e.target.value)} placeholder="noreply@yourdomain.com"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">From Name</label>
            <input value={fromName} onChange={e => setFromName(e.target.value)} placeholder="NousViz"
              className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input type="checkbox" id="smtp-tls" checked={useTls} onChange={e => setUseTls(e.target.checked)}
            className="rounded border-border" />
          <label htmlFor="smtp-tls" className="text-xs text-muted-foreground">Use TLS (STARTTLS on port 587; implicit TLS on port 465)</label>
        </div>

        {result && (
          <div className={cn("px-3 py-2 rounded-md text-xs", result.ok ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400")}>
            {result.message}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button onClick={handleSave} disabled={saving || !host || !fromAddress}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
            {saving ? "Saving..." : "Save"}
          </button>
          <button onClick={handleTest} disabled={testing || !configured}
            className="h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors">
            {testing ? "Sending..." : "Send Test Email"}
          </button>
        </div>
      </div>

      {/* Setup guide — always visible, provider instructions are collapsible */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-3">
        <div>
          <h4 className="font-display text-sm text-foreground">Setup Guide</h4>
          <p className="text-xs text-muted-foreground mt-1">
            Pick a provider below to auto-fill the form above. Follow the steps, then click <strong className="text-foreground">Send Test Email</strong> to verify.
          </p>
        </div>
        {[
          { id: "resend", name: "Resend", free: "3,000/month free", url: "https://resend.com/signup",
            fill: { host: "smtp.resend.com", port: "2587", username: "resend", tls: true },
            steps: [
              <>Sign up at <a href="https://resend.com/signup" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">resend.com</a></>,
              <>Go to <strong className="text-foreground">API Keys</strong> → Create a new key</>,
              <>Paste your API key as the password above, then click <strong className="text-foreground">Save</strong></>,
              <>Click <strong className="text-foreground">Send Test Email</strong> to verify</>,
            ],
            note: "Port 2587 bypasses cloud provider SMTP blocks (DigitalOcean, AWS, etc.). onboarding@resend.dev only delivers to your signup email — verify your domain in Resend → Domains to send to others." },
          { id: "gmail", name: "Gmail / Google Workspace", free: "500/day free",
            fill: { host: "smtp.gmail.com", port: "587", username: "", tls: true },
            steps: [
              <>Enable <strong className="text-foreground">2-Step Verification</strong> on your Google account</>,
              <>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">App Passwords</a> → generate a password for &ldquo;Mail&rdquo;</>,
              <>Enter your Gmail address as the username and paste the App Password above</>,
              <>Click <strong className="text-foreground">Save</strong>, then <strong className="text-foreground">Send Test Email</strong></>,
            ],
            note: "500/day personal, 2,000/day Workspace. No domain verification needed — works immediately." },
          { id: "brevo", name: "Brevo (Sendinblue)", free: "300/day free", url: "https://app.brevo.com/settings/keys/smtp",
            fill: { host: "smtp-relay.brevo.com", port: "587", username: "", tls: true },
            steps: [
              <>Sign up at <a href="https://www.brevo.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">brevo.com</a></>,
              <>Go to <strong className="text-foreground">Settings → SMTP & API</strong> → copy the login and SMTP key</>,
              <>Enter your Brevo login email as the username and the SMTP key as the password above</>,
              <>Click <strong className="text-foreground">Save</strong>, then <strong className="text-foreground">Send Test Email</strong></>,
            ] },
          { id: "ses", name: "Amazon SES", free: "~$0.10/1,000", url: "https://console.aws.amazon.com/ses/home",
            fill: { host: "email-smtp.us-east-1.amazonaws.com", port: "587", username: "", tls: true },
            steps: [
              <>Log into <a href="https://console.aws.amazon.com/ses/home" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">AWS Console → SES</a></>,
              <>Verify your sending domain or email</>,
              <>Go to <strong className="text-foreground">SMTP Settings</strong> → Create SMTP credentials</>,
              <>Enter the SMTP username and password above (update host region if needed)</>,
              <>Click <strong className="text-foreground">Save</strong>, then <strong className="text-foreground">Send Test Email</strong></>,
            ],
            note: "New accounts start in sandbox mode. Request production access to send to unverified addresses." },
          { id: "mailgun", name: "Mailgun", free: "1,000/month free", url: "https://signup.mailgun.com/new/signup",
            fill: { host: "smtp.mailgun.org", port: "587", username: "", tls: true },
            steps: [
              <>Sign up at <a href="https://signup.mailgun.com/new/signup" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">mailgun.com</a></>,
              <>Add and verify your sending domain</>,
              <>Go to <strong className="text-foreground">Sending → Domain settings → SMTP credentials</strong></>,
              <>Enter the SMTP login and password above</>,
              <>Click <strong className="text-foreground">Save</strong>, then <strong className="text-foreground">Send Test Email</strong></>,
            ] },
          { id: "postfix", name: "Self-Hosted (Postfix)", free: "Unlimited · Advanced",
            fill: { host: "localhost", port: "25", username: "", tls: false },
            steps: [
              <><code className="font-mono-deck bg-secondary px-1 rounded">sudo apt-get install -y postfix</code> — choose &ldquo;Internet Site&rdquo;, enter your domain</>,
              <>Add DNS records: SPF (<code className="font-mono-deck bg-secondary px-1 rounded">v=spf1 ip4:&lt;your-ip&gt; -all</code>), DKIM (opendkim), DMARC</>,
              <>Click <strong className="text-foreground">Save</strong>, then <strong className="text-foreground">Send Test Email</strong> — check spam folder</>,
            ],
            note: "Emails from a VPS IP without SPF/DKIM/DMARC are frequently flagged as spam. External providers handle this for you." },
        ].map(provider => {
          const isOpen = expandedProvider === provider.id;
          const isActive = expandedProvider === provider.id;
          function applyProvider() {
            setHost(provider.fill.host);
            setPort(provider.fill.port);
            if (provider.fill.username) setUsername(provider.fill.username);
            setUseTls(provider.fill.tls);
            setExpandedProvider(provider.id);
          }
          return (
            <div key={provider.id} className={cn("rounded-lg border overflow-hidden transition-colors", isActive ? "border-primary/40" : "border-border")}>
              <button
                type="button"
                onClick={applyProvider}
                className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-secondary/20 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <ChevronRight className={cn("w-3 h-3 text-muted-foreground transition-transform", isOpen && "rotate-90")} />
                  <span className="text-xs font-display text-foreground">{provider.name}</span>
                </div>
                <span className="text-[10px] text-green-400 font-mono-deck">{provider.free}</span>
              </button>
              {isOpen && (
                <div className="px-4 py-3 border-t border-border space-y-2 text-xs text-muted-foreground">
                  {provider.steps.map((step, i) => (
                    <p key={i} className="font-body"><strong className="text-foreground">{i + 1}.</strong> {step}</p>
                  ))}
                  {provider.note && (
                    <p className="text-muted-foreground/70 mt-1 font-body">{provider.note}</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  useMarkBootReadyOnMount();
  const { setTheme, palette, setPalette, customColors, setCustomColors } = useTheme();
  const { compact, toggle: toggleCompact } = useCompactNumbers();

  // B252 (v0.9.10.0.2): Users tab removed from Settings — moved to
  // System → Users (route /system/users). The /settings/users route
  // redirects to /system/users for backward compat.
  const SETTINGS_TABS = [...BASE_TABS];
  const { tab: urlTab } = useParams<{ tab?: string }>();
  const navigate = useNavigate();
  const defaultTab = "general";
  const tab: SettingsTab = SETTINGS_TABS.some(t => t.id === urlTab) ? urlTab! : defaultTab;
  const setTab = (id: string) => navigate(`/settings/${id}`, { replace: true });
  const [sslInfo, setSslInfo] = useState<{ enabled: boolean; type: string; domain?: string; expires?: string } | null>(null);
  const [authRequired, setAuthRequired] = useState<boolean | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [showSslSetup, setShowSslSetup] = useState(false);
  const [instanceName, setInstanceName] = useState(
    () => localStorage.getItem(INSTANCE_NAME_KEY) || "NousViz"
  );
  const [instanceNameSaved, setInstanceNameSaved] = useState(false);

  useEffect(() => {
    apiFetch("/api/health")
      .then(r => r.json())
      .then(d => {
        if (d?.ssl) setSslInfo(d.ssl);
      })
      .catch(() => {});
    apiFetch("/api/health/config")
      .then(r => r.json())
      .then(d => setAuthRequired(!!d?.auth_required))
      .catch(() => {});
  }, []);

  function saveInstanceName() {
    applyInstanceName(instanceName);
    setInstanceNameSaved(true);
    setTimeout(() => setInstanceNameSaved(false), 2000);
  }

  return (
    <div className="max-w-[1000px] space-y-6">
      {showWizard && (
        <SetupWizard onClose={() => { setShowWizard(false); localStorage.setItem(SETUP_KEY, "true"); }} />
      )}
      {showSslSetup && (
        <SslSetupModal
          onClose={() => setShowSslSetup(false)}
          onComplete={() => {
            apiFetch("/api/health").then(r => r.json()).then(d => { if (d?.ssl) setSslInfo(d.ssl); }).catch(() => {});
          }}
        />
      )}

      {/* ── Tab navigation ──────────────────────────────────────────── */}
      {/* B288 (v0.9.11.26): ScrollableTabs primitive — Wizard button now
          stacks below the strip on mobile rather than eating ~80px of
          tab-strip width. Right-edge gradient hint shows when more tabs
          exist offscreen. */}
      <ScrollableTabs
        tabs={SETTINGS_TABS.map((t) => ({
          id: t.id,
          label: t.label,
          icon: <t.icon className="w-3.5 h-3.5" />,
        }))}
        current={tab}
        onChange={(id) => setTab(id)}
        ariaLabel="Settings sections"
        action={
          <button
            onClick={() => setShowWizard(true)}
            className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-2 transition-colors w-full sm:w-auto justify-center"
          >
            <Rocket className="w-3.5 h-3.5" /> Wizard
          </button>
        }
      />

      {/* B252 (v0.9.10.0.2): Users tab removed — moved to System → Users.
          The /settings/users route redirects there. */}

      {/* ── Profile ──────────────────────────────────────────────────── */}
      {tab === "profile" && <ProfilePanel />}

      {/* ── General ──────────────────────────────────────────────────── */}
      {tab === "general" && (
        <div className="space-y-4">
          <Section icon={Server} label="Instance">
            <Field label="Instance name" desc="Shown in the browser title and share links">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={instanceName}
                  onChange={e => { setInstanceName(e.target.value); setInstanceNameSaved(false); }}
                  onKeyDown={e => e.key === "Enter" && saveInstanceName()}
                  placeholder="NousViz"
                  className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-44 font-body"
                />
                <button
                  onClick={saveInstanceName}
                  className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
                >
                  {instanceNameSaved ? "Saved" : "Save"}
                </button>
              </div>
            </Field>
            <Field label="Timezone" desc="Used for all date displays and scheduled jobs">
              <select className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56">
                <option>UTC</option>
                <option>Europe/London</option>
                <option>America/New_York</option>
                <option>America/Los_Angeles</option>
                <option>Asia/Tokyo</option>
              </select>
            </Field>
            <Field label="Number format" desc="How large numbers are displayed across the app">
              <button
                onClick={toggleCompact}
                className={cn(
                  "h-8 px-3 rounded-md text-xs font-mono-deck transition-colors border",
                  compact
                    ? "bg-primary/10 text-primary border-primary/30"
                    : "bg-background border-border text-muted-foreground hover:text-foreground"
                )}
              >
                {compact ? "Abbreviated (1.2M, 45K)" : "Full (1,234,567)"}
              </button>
            </Field>
          </Section>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Link
              to="/analytics"
              className="bg-card rounded-lg border border-border p-4 flex items-center gap-3 hover:border-primary/30 transition-colors"
            >
              <BarChart3 className="w-4 h-4 text-blue-400 shrink-0" />
              <div>
                <p className="text-sm text-foreground font-body">Usage Analytics</p>
                <p className="text-xs text-muted-foreground">Time per page, sessions, devices</p>
              </div>
            </Link>
            <Link
              to="/plugins"
              className="bg-card rounded-lg border border-border p-4 flex items-center gap-3 hover:border-primary/30 transition-colors"
            >
              <Globe className="w-4 h-4 text-primary shrink-0" />
              <div>
                <p className="text-sm text-foreground font-body">Plugins</p>
                <p className="text-xs text-muted-foreground">Installed plugins and marketplace</p>
              </div>
            </Link>
          </div>

          {/* Appearance (merged from former standalone tab) */}
          <Section icon={Sun} label="Appearance">
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-foreground font-body">Mode</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Switch between light and dark theme</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setTheme("light")}
                    className={cn(
                      "h-8 px-4 rounded-md text-xs font-body flex items-center gap-2 transition-colors border",
                      palette === "default-light"
                        ? "bg-background text-foreground border-primary shadow-sm"
                        : "border-border text-muted-foreground hover:text-foreground hover:border-border/80"
                    )}
                  >
                    <Sun className="w-3.5 h-3.5" /> Light
                  </button>
                  <button
                    onClick={() => setTheme("dark")}
                    className={cn(
                      "h-8 px-4 rounded-md text-xs font-body flex items-center gap-2 transition-colors border",
                      palette === "default-dark"
                        ? "bg-background text-foreground border-primary shadow-sm"
                        : "border-border text-muted-foreground hover:text-foreground hover:border-border/80"
                    )}
                  >
                    <Moon className="w-3.5 h-3.5" /> Dark
                  </button>
                </div>
              </div>

              <div className="border-t border-border pt-5">
                <p className="text-sm text-foreground font-body mb-1">Color palette</p>
                <p className="text-xs text-muted-foreground mb-4">
                  Choose the visual style for the app and embedded dashboards.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {PALETTES.map(p => (
                    <button
                      key={p.id}
                      onClick={() => setPalette(p.id)}
                      className={cn(
                        "rounded-xl border-2 p-3 text-left transition-all hover:scale-[1.02]",
                        palette === p.id ? "border-primary ring-1 ring-primary/30" : "border-border hover:border-primary/40"
                      )}
                    >
                      <div className="flex gap-1 mb-2.5 h-6 items-center">
                        {p.id === "custom" ? (
                          <Pipette className="w-4 h-4 text-muted-foreground" />
                        ) : (
                          p.swatches.map((color, i) => (
                            <div key={i} className="h-5 w-5 rounded-md border border-white/10" style={{ background: color }} />
                          ))
                        )}
                      </div>
                      <p className="text-xs font-display text-foreground leading-tight">{p.label}</p>
                      <p className="text-[10px] text-muted-foreground font-body mt-0.5 leading-tight">{p.sub}</p>
                    </button>
                  ))}
                </div>

                {palette === "custom" && (
                  <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 max-w-lg">
                    {COLOR_FIELDS.map(({ key, label }) => (
                      <label key={key} className="flex items-center justify-between gap-3">
                        <span className="text-xs text-muted-foreground font-body">{label}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded border border-border shrink-0" style={{ background: customColors[key] }} />
                          <input
                            type="color"
                            value={customColors[key]}
                            onChange={e => setCustomColors({ ...customColors, [key]: e.target.value })}
                            className="w-8 h-6 rounded cursor-pointer bg-transparent border-0 p-0"
                          />
                          <input
                            type="text"
                            value={customColors[key]}
                            onChange={e => {
                              const v = e.target.value;
                              if (/^#[0-9a-fA-F]{0,6}$/.test(v)) setCustomColors({ ...customColors, [key]: v });
                            }}
                            className="w-20 h-6 px-1.5 rounded bg-secondary border border-border text-[10px] font-mono-deck text-foreground"
                            maxLength={7}
                          />
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Section>

          {/* B211 (v0.9.7.0) + B221 (v0.9.7.1): Documentation surface — native API
              reference + raw spec links. SDK reference + meta-doc links
              come in v0.9.7.4 (B217). */}
          <Section icon={BookOpen} label="Documentation">
            <div className="space-y-2 text-sm">
              <Link
                to="/docs/api"
                className="flex items-center gap-2 text-foreground hover:text-primary transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                API Reference (interactive)
              </Link>
              <a
                href="/openapi.json"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                OpenAPI spec (JSON)
              </a>
              <a
                href="/openapi.yaml"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                OpenAPI spec (YAML)
              </a>
            </div>
          </Section>
        </div>
      )}

      {/* ── Security ─────────────────────────────────────────────────── */}
      {tab === "security" && (
        <div className="space-y-4">
          <Section icon={Shield} label="Authentication">
            <Field label="Auth required" desc="Require login to access the dashboard">
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={!!authRequired} readOnly className="rounded opacity-60 cursor-not-allowed" />
                <span className="text-xs text-muted-foreground font-body">{authRequired ? "Enabled" : "Disabled"}</span>
              </div>
            </Field>
            <p className="text-[11px] text-muted-foreground">
              Change via the Setup Wizard or set <code className="font-mono-deck bg-secondary px-1 rounded">AUTH_REQUIRED=true</code> in <code className="font-mono-deck bg-secondary px-1 rounded">.env</code>.
            </p>
          </Section>

          <Section icon={Shield} label="SSL / HTTPS">
            {sslInfo ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Status</span>
                  <span className="text-xs font-mono-deck text-green-400">Enabled</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Type</span>
                  <span className="text-xs font-mono-deck text-foreground">{sslInfo.type === "letsencrypt" ? "Let's Encrypt" : "Self-signed"}</span>
                </div>
                {sslInfo.domain && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Domain</span>
                    <span className="text-xs font-mono-deck text-foreground">{sslInfo.domain}</span>
                  </div>
                )}
                {sslInfo.expires && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Expires</span>
                    <span className="text-xs font-mono-deck text-foreground">{sslInfo.expires}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground font-body">
                  HTTPS is not configured. Secure your connection with a free certificate.
                </p>
                <button
                  onClick={() => setShowSslSetup(true)}
                  className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors"
                >
                  Configure HTTPS
                </button>
              </div>
            )}
          </Section>

          <ApiKeysSection />

          <GitTokenSection />

          <DeployKeysSection />
        </div>
      )}

      {/* ── Email / SMTP ──────────────────────────────────────────────── */}
      {tab === "email" && <EmailSettingsPanel />}

      {/* B165 (v0.9.5): Connections promoted to top-level /connections.
          ConnectionsPanel was deleted; SettingsPage no longer renders it.
          /settings/connections redirects to /connections at the
          React Router level (App.tsx). */}

      {tab === "data" && (
        <div className="space-y-4">
          <DatabaseSection />
        </div>
      )}

      {tab === "logs" && <LogsPanel />}

      {tab === "maintenance" && <MaintenancePanel />}
    </div>
  );
}
