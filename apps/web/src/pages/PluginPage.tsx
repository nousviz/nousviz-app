import { useParams, NavLink, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect, useCallback, useRef } from "react";
import { Package, GitBranch, Globe, CheckCircle2, Database, Share2, Trash2, Lock } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import { cn } from "@/lib/utils";
import { useBootCoordinator } from "@/components/layout/BootCoordinator";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import DashboardRenderer from "@/widgets/DashboardRenderer";
import PluginAlerts from "@/widgets/PluginAlerts";
import PluginModulesTab from "@/components/plugins/PluginModulesTab";
import PluginActions, { type PluginAction } from "@/components/plugins/PluginActions";
import SetupChecklist, { type SetupChecklistData } from "@/components/plugins/SetupChecklist";
import SyncStatusCard from "@/components/plugins/SyncStatusCard";
import FileInput from "@/components/plugins/fields/FileInput";
import PortInput from "@/components/plugins/fields/PortInput";
import CronInput from "@/components/plugins/fields/CronInput";
import UrlInput from "@/components/plugins/fields/UrlInput";



// ── Embed button ─────────────────────────────────────────────────────
// ── Plugin Alerts ────────────────────────────────────────────────────

function PluginAlertsTab({ pluginId, tables }: { pluginId: string; tables: string[] }) {
  return <PluginAlerts pluginId={pluginId} tables={tables} />;
}

// ── Plugin overview (static manifest info) ───────────────────────────

interface PluginManifest {
  display_name: string;
  description?: string;
  version: string;
  license?: string;
  category?: string;
  tags?: string[];
  publisher?: { name: string; verified?: boolean; website?: string };
  homepage?: string;
  repository?: string;
  requires?: Record<string, boolean | string>;
  databases?: { postgres?: { tables: string[] } };
  depends_on?: { plugin: string; display_name?: string; reason?: string }[];
  dashboards?: { name: string; label: string }[];
  navigation?: { label: string; href?: string; path?: string; icon?: string; position?: string }[];
  settings?: { name: string; label: string; type: string }[];
  // P204 (v0.9.0): populated by core's plugin detail endpoint when the
  // plugin's api/routes.py failed to load at API startup.
  load_status?: {
    routes_registered: boolean;
    stage?: string;
    failure_reason?: string;
  };
}

function PluginAboutTab({ manifest }: { manifest: PluginManifest }) {
  const pgTables = manifest.databases?.postgres?.tables ?? [];

  return (
    <div className="max-w-[760px] space-y-5">
      {/* Hero */}
      <div className="bg-card rounded-lg border border-border p-6">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <Package className="w-6 h-6 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-display text-xl text-foreground">{manifest.display_name}</h2>
              {manifest.publisher?.verified && (
                <span className="flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3" /> Verified
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground font-mono-deck mt-1">
              v{manifest.version}
              {manifest.publisher?.name && <> · {manifest.publisher.name}</>}
              {manifest.license && <> · {manifest.license}</>}
              {manifest.category && <> · <span className="capitalize">{manifest.category}</span></>}
            </p>
            {manifest.description && (
              <p className="text-sm text-muted-foreground font-body mt-3 leading-relaxed">
                {manifest.description}
              </p>
            )}
            {manifest.tags && manifest.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {manifest.tags.map(tag => (
                  <span key={tag} className="text-[10px] font-mono-deck px-2 py-0.5 rounded-full bg-secondary text-muted-foreground">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Requirements */}
        {manifest.requires && Object.keys(manifest.requires).length > 0 && (
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-3">Requirements</h3>
            <div className="space-y-2">
              {Object.entries(manifest.requires).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="font-mono-deck text-foreground capitalize">{key}</span>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full font-mono-deck",
                    val === true ? "bg-green-500/10 text-green-400" : "bg-secondary text-muted-foreground"
                  )}>{String(val)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data tables */}
        {pgTables.length > 0 && (
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
              <Database className="w-3.5 h-3.5" /> Data tables
            </h3>
            <div className="space-y-1.5">
              {pgTables.map(t => (
                <div key={t} className="flex items-center justify-between text-sm">
                  <span className="font-mono-deck text-foreground">{t}</span>
                  <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded">postgres</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dependencies */}
        {manifest.depends_on && manifest.depends_on.length > 0 && (
          <div className="bg-card rounded-lg border border-border border-orange-500/20 bg-orange-500/5 p-5">
            <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
              <GitBranch className="w-3.5 h-3.5" /> Depends on
            </h3>
            <div className="space-y-2">
              {manifest.depends_on.map(dep => (
                <div key={dep.plugin} className="text-sm">
                  <span className="text-foreground font-display">{dep.display_name || dep.plugin}</span>
                  {dep.reason && <p className="text-xs text-muted-foreground mt-0.5">{dep.reason}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Publisher */}
        {manifest.publisher && (
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-xs font-display text-muted-foreground uppercase tracking-wider mb-3">Publisher</h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-foreground font-display">{manifest.publisher.name}</span>
                {manifest.publisher.verified && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />}
              </div>
              {manifest.publisher.website && (
                <a href={manifest.publisher.website} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1">
                  <Globe className="w-3 h-3" /> {manifest.publisher.website}
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Links */}
      {(manifest.homepage || manifest.repository) && (
        <div className="flex gap-3">
          {manifest.homepage && (
            <a href={manifest.homepage} target="_blank" rel="noopener noreferrer"
              className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
              <Globe className="w-3.5 h-3.5" /> Homepage
            </a>
          )}
          {manifest.repository && (
            <a href={manifest.repository} target="_blank" rel="noopener noreferrer"
              className="h-9 px-4 rounded-md bg-secondary hover:bg-secondary/80 text-sm text-foreground flex items-center gap-2 transition-colors">
              <GitBranch className="w-3.5 h-3.5" /> Repository
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ── Settings ─────────────────────────────────────────────────────────

interface SettingField {
  name: string;
  label: string;
  type: "text" | "number" | "toggle" | "select" | "password" | "file" | "port" | "cron" | "url";
  default?: unknown;
  description?: string;
  options?: string[];
  required?: boolean;
  // P120 new field-type configs
  accept?: string;        // file: browser picker filter
  format_hint?: string;   // file: 'pem' | 'json'
  scheme?: string;        // url: 'https' | 'mysql'
  // B162 (v0.9.4.11): manifest-declared secrecy. Used by the connection
  // renderer to decide whether to mask the value (type=password) or show
  // it in plaintext (type=text). Backend's _field_is_secret reads the
  // same flag from plugin.yaml.
  secret?: boolean;
}

function PluginSettingsTab({ pluginId }: { pluginId: string }) {
  // v1.0.2: the entire Settings tab is admin-only — all its data fetches
  // (`/api/plugins/{slug}/settings`, `/api/plugins/{slug}/sync-schedule`,
  // `/api/plugins/{slug}/connections`) require plugins.configure. A viewer
  // navigating here by URL would generate a wave of 403s in the console
  // (which is exactly what surfaced in the v1.0.1 post-mortem reports).
  // Bail before any of those fetches fire, and show a clear "you don't
  // have access" message instead of an empty form.
  const { hasPermission, loading: userLoading } = useCurrentUser();
  const canConfigure = hasPermission("plugins.configure");

  const [fields, setFields] = useState<SettingField[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [isUtility, setIsUtility] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [actions, setActions] = useState<PluginAction[]>([]);
  const [actionsTick, setActionsTick] = useState(0); // bump to trigger refetch
  const [checklist, setChecklist] = useState<SetupChecklistData | undefined>(undefined);
  const [shares, setShares] = useState<{ share_id: string; title: string; page_path: string; has_password: boolean; created_at: string; expires_at: string | null; access_count: number; revoked: boolean; expired: boolean }[]>([]);

  const loadShares = useCallback(() => {
    apiFetch("/api/shares").then(r => r.json()).then(d => {
      const prefix = `/plugin/${pluginId}/`;
      setShares((d.links || []).filter((s: any) => s.page_path?.startsWith(prefix) && !s.revoked));
    }).catch(() => {});
  }, [pluginId]);

  useEffect(() => { loadShares(); }, [loadShares]);

  async function revokeShare(shareId: string) {
    if (!confirm("Revoke this shared link? It will stop working immediately.")) return;
    await apiFetch(`/api/shares/${shareId}`, { method: "DELETE" });
    loadShares();
  }

  // Track which field names are connection fields vs settings fields
  const [connectionFieldNames, setConnectionFieldNames] = useState<Set<string>>(new Set());

  useEffect(() => {
    // v1.0.2: skip the entire load chain for non-configure roles. Each of
    // the calls below (`/connections`, `/settings`) requires plugins.configure
    // and would 403 — generating the console noise that misdirected the
    // v1.0.1 triage. The page renders a permission-denied screen instead
    // (see early return below), so there's nothing to populate.
    if (userLoading) return; // wait for permissions to load before deciding
    if (!canConfigure) return;
    let cancelled = false;
    apiFetch(`/api/plugins/${pluginId}`)
      .then(r => r.json())
      .then(manifest => {
        if (cancelled) return;
        const utility = manifest.type === "utility";
        setIsUtility(utility);
        setActions(Array.isArray(manifest.actions) ? manifest.actions : []);
        setChecklist(manifest.setup_checklist && typeof manifest.setup_checklist === "object" ? manifest.setup_checklist : undefined);
        const hasConnections = Array.isArray(manifest.connections) && manifest.connections.length > 0;

        // Load settings fields
        const settingsFields: SettingField[] = manifest.settings || [];
        const allFields: SettingField[] = [...settingsFields];
        const allValues: Record<string, unknown> = {};
        settingsFields.forEach(f => { if (f.default !== undefined) allValues[f.name] = f.default; });

        // Load connection fields if declared (any plugin type, not just utility)
        const connPromise = hasConnections
          ? apiFetch(`/api/plugins/${pluginId}/connections`).then(r => r.json()).then(data => {
              if (cancelled) return;
              const allConns = data.connections || [];
              const connNames = new Set<string>();
              for (const conn of allConns) {
                const fields: SettingField[] = (conn.fields || []).map((f: any) => ({
                  ...f,
                  // Tag with module source if present
                  ...(conn._module ? { _module: conn._module, _module_label: conn._module_label || conn._module } : {}),
                }));
                fields.forEach((f: SettingField) => connNames.add(f.name));
                allFields.push(...fields);
                Object.assign(allValues, conn.values || {});
              }
              setConnectionFieldNames(connNames);
            }).catch(() => {})
          : Promise.resolve();

        // Load saved settings from DB
        const settingsPromise = (!utility || settingsFields.length > 0)
          ? apiFetch(`/api/plugins/${pluginId}/settings`).then(r => r.json()).then(data => {
              if (cancelled) return;
              (data.settings || []).forEach((s: { key: string; value: unknown }) => { allValues[s.key] = s.value; });
            }).catch(() => {})
          : Promise.resolve();

        Promise.all([connPromise, settingsPromise]).then(() => {
          if (cancelled) return;
          setFields(allFields);
          setValues(allValues);
        });
      })
      .catch(() => {});

    return () => { cancelled = true; };
  }, [pluginId, actionsTick, userLoading, canConfigure]);

  async function save() {
    setSaving(true);
    setResult(null);
    try {
      // Split values into settings vs connection fields
      const connValues: Record<string, unknown> = {};
      const settingsValues: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(values)) {
        if (connectionFieldNames.has(key)) {
          connValues[key] = val;
        } else {
          settingsValues[key] = val;
        }
      }

      // Save connection fields if any
      if (Object.keys(connValues).length > 0) {
        const connRes = await apiFetch(`/api/plugins/${pluginId}/connections`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(connValues),
        });
        if (!connRes.ok) {
          const err = await connRes.json().catch(() => ({ detail: connRes.statusText }));
          throw new Error(err.detail || "Failed to save credentials.");
        }
        const data = await connRes.json().catch(() => ({} as { health?: { ok: boolean; version?: string; error?: string } }));
        if (data.health?.ok) {
          setResult({ ok: true, message: `Saved · ${data.health.version || "connected"}` });
        } else if (data.health) {
          setResult({ ok: false, message: `Saved, but health check failed: ${data.health.error || "unknown"}` });
        }
      }

      // Save settings fields if any
      if (Object.keys(settingsValues).length > 0) {
        const settingsRes = await apiFetch(`/api/plugins/${pluginId}/settings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ settings: Object.entries(settingsValues).map(([key, value]) => ({ key, value })) }),
        });
        if (!settingsRes.ok) {
          const err = await settingsRes.json().catch(() => ({ detail: settingsRes.statusText }));
          throw new Error(err.detail || "Failed to save settings.");
        }
      }

      if (!result) setResult({ ok: true, message: "Settings saved." });
    } catch (e) {
      setResult({ ok: false, message: e instanceof Error ? e.message : "Failed to save." });
    } finally {
      setSaving(false);
    }
  }


  // v1.0.2: viewer/analyst landed on /plugin/{slug}/settings — render a
  // permission-denied card instead of an empty/broken form. Done AFTER the
  // hooks above so we don't violate the rules-of-hooks order; renders
  // before any of the admin-only data has been requested or used.
  if (!userLoading && !canConfigure) {
    return (
      <div className="max-w-[600px]">
        <div className="bg-card border border-border rounded-xl p-6 space-y-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-muted-foreground" />
            <h2 className="font-display text-sm text-foreground">Settings are admin-only</h2>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Editing plugin settings (credentials, sync schedule, connections)
            requires the <code className="bg-secondary px-1 rounded">plugins.configure</code>{" "}
            permission, which is granted to <strong>admin</strong> and{" "}
            <strong>superadmin</strong> roles. Your role doesn&apos;t hold it.
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            If you need to change something here, ask an admin on your team.
          </p>
        </div>
      </div>
    );
  }

  // Split fields into settings vs credentials
  const settingsFields = fields.filter(f => !connectionFieldNames.has(f.name));
  const credentialFields = fields.filter(f => connectionFieldNames.has(f.name));

  return (
    <div className="max-w-[600px] space-y-4">
      {/* P121: plugin-declared setup checklist (top of Settings tab) */}
      <SetupChecklist pluginId={pluginId} checklist={checklist} />

      {/* Modules are on their own tab now — see PluginModulesTab */}

      {/* Credentials — grouped by source (plugin-level vs module-level) */}
      {(() => {
        const coreCreds = credentialFields.filter((f: any) => !f._module);
        const modCredGroups = new Map<string, { label: string; fields: typeof credentialFields }>();
        credentialFields.forEach((f: any) => {
          if (!f._module) return;
          if (!modCredGroups.has(f._module)) {
            modCredGroups.set(f._module, { label: f._module_label || f._module, fields: [] });
          }
          modCredGroups.get(f._module)!.fields.push(f);
        });

        function renderCredField(field: SettingField) {
          const raw = values[field.name];
          const strVal = String(raw ?? "");
          const setVal = (next: unknown) => setValues(v => ({ ...v, [field.name]: next }));
          return (
            <div key={field.name} className="space-y-1">
              <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider">{field.label}</label>
              {field.description && <p className="text-xs text-muted-foreground">{field.description}</p>}
              {field.type === "file" ? (
                <FileInput name={field.name} value={strVal} onChange={setVal} accept={field.accept} format_hint={field.format_hint} required={field.required} />
              ) : field.type === "port" ? (
                <PortInput name={field.name} value={typeof raw === "number" ? raw : strVal} onChange={setVal} required={field.required} />
              ) : field.type === "cron" ? (
                <CronInput name={field.name} value={strVal} onChange={setVal} required={field.required} />
              ) : field.type === "url" ? (
                <UrlInput name={field.name} value={strVal} onChange={setVal} scheme={field.scheme} required={field.required} />
              ) : (
                // B162 (v0.9.4.11): only mask when the manifest declares
                // the field secret. Connection blocks mix structural fields
                // (host, port, db_name) with actual secrets (password,
                // api_key); rendering everything as password hid the
                // values operators need to verify they entered correctly.
                <input type={field.secret ? "password" : "text"} value={strVal}
                  onChange={e => setVal(e.target.value)}
                  placeholder={field.required ? "Required" : "Optional"}
                  className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56" />
              )}
            </div>
          );
        }

        if (credentialFields.length === 0) return null;

        return (
          <>
            {coreCreds.length > 0 && (
              <div className="bg-card rounded-lg border border-border p-5 space-y-4">
                <h3 className="font-display text-sm text-foreground">Credentials</h3>
                {coreCreds.map(renderCredField)}
                <div className="flex items-center gap-3 pt-2">
                  <button onClick={save} disabled={saving} className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {saving ? "Saving\u2026" : "Save Credentials"}
                  </button>
                  {result && <span className={cn("text-xs font-body", result.ok ? "text-green-400" : "text-red-400")}>{result.message}</span>}
                </div>
                <p className="text-[10px] text-muted-foreground">Credentials are stored AES-256 encrypted. Never saved to disk.</p>
              </div>
            )}
            {[...modCredGroups.entries()].map(([modName, group]) => (
              <div key={modName} className="bg-card rounded-lg border border-border p-5 space-y-4">
                <h3 className="font-display text-sm text-foreground">{group.label} Credentials</h3>
                {group.fields.map(renderCredField)}
                <div className="flex items-center gap-3 pt-2">
                  <button onClick={save} disabled={saving} className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {saving ? "Saving\u2026" : "Save"}
                  </button>
                </div>
                <p className="text-[10px] text-muted-foreground">Encrypted at rest.</p>
              </div>
            ))}
          </>
        );
      })()}

      {/* Settings — grouped by source (core vs module) */}
      {(() => {
        const coreFields = settingsFields.filter((f: any) => !f._module);
        const moduleGroups = new Map<string, { label: string; fields: typeof settingsFields }>();
        settingsFields.forEach((f: any) => {
          if (!f._module) return;
          if (!moduleGroups.has(f._module)) {
            moduleGroups.set(f._module, { label: f._module_label || f._module, fields: [] });
          }
          moduleGroups.get(f._module)!.fields.push(f);
        });

        function renderField(field: SettingField) {
          const raw = values[field.name];
          const strVal = String(raw ?? "");
          const setVal = (next: unknown) => setValues(v => ({ ...v, [field.name]: next }));
          return (
            <div key={field.name} className="space-y-1">
              <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider">{field.label}</label>
              {field.description && <p className="text-xs text-muted-foreground">{field.description}</p>}
              {field.type === "toggle" ? (
                <button onClick={() => setVal(!raw)}
                  className={cn("relative inline-flex h-5 w-9 items-center rounded-full transition-colors", raw ? "bg-primary" : "bg-secondary")}>
                  <span className={cn("inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform", raw ? "translate-x-[18px]" : "translate-x-1")} />
                </button>
              ) : field.type === "select" ? (
                <select value={strVal} onChange={e => setVal(e.target.value)}
                  className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
                  {(field.options || []).map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              ) : field.type === "file" ? (
                <FileInput name={field.name} value={strVal} onChange={setVal} accept={field.accept} format_hint={field.format_hint} required={field.required} />
              ) : field.type === "port" ? (
                <PortInput name={field.name} value={typeof raw === "number" ? raw : strVal} onChange={setVal} required={field.required} />
              ) : field.type === "cron" ? (
                <CronInput name={field.name} value={strVal} onChange={setVal} required={field.required} />
              ) : field.type === "url" ? (
                <UrlInput name={field.name} value={strVal} onChange={setVal} scheme={field.scheme} required={field.required} />
              ) : (
                <input type={field.type === "number" ? "number" : field.type === "password" ? "password" : "text"}
                  value={strVal}
                  onChange={e => setVal(field.type === "number" ? Number(e.target.value) : e.target.value)}
                  className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56" />
              )}
            </div>
          );
        }

        return (
          <>
            {coreFields.length > 0 && (
              <div className="bg-card rounded-lg border border-border p-5 space-y-4">
                <h3 className="font-display text-sm text-foreground">Plugin Settings</h3>
                {coreFields.map(renderField)}
                <div className="flex items-center gap-3 pt-2">
                  <button onClick={save} disabled={saving} className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {saving ? "Saving\u2026" : "Save"}
                  </button>
                  {result && <span className={cn("text-xs font-body", result.ok ? "text-green-400" : "text-red-400")}>{result.message}</span>}
                </div>
              </div>
            )}
            {[...moduleGroups.entries()].map(([modName, group]) => (
              <div key={modName} className="bg-card rounded-lg border border-border p-5 space-y-4">
                <h3 className="font-display text-sm text-foreground">{group.label} Settings</h3>
                {group.fields.map(renderField)}
                <div className="flex items-center gap-3 pt-2">
                  <button onClick={save} disabled={saving} className="h-8 px-4 rounded-md bg-primary text-xs text-white font-body hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {saving ? "Saving\u2026" : "Save"}
                  </button>
                </div>
              </div>
            ))}
          </>
        );
      })()}

      {/* B205 (v0.9.6): unified Sync card \u2014 replaces the old "Last sync" +
          "Sync schedule" blocks. Owns its own polling + state. */}
      <SyncStatusCard pluginId={pluginId} isUtility={isUtility} />

      {/* Shared Links */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-sm text-foreground flex items-center gap-2">
            <Share2 className="w-3.5 h-3.5 text-muted-foreground" />
            Shared Links
          </h3>
          {shares.length > 0 && (
            <span className="text-[10px] font-mono-deck text-muted-foreground">{shares.length} active</span>
          )}
        </div>
        {shares.length > 0 ? (
          <div className="space-y-1.5">
            {shares.map(s => (
              <div key={s.share_id} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/30 text-xs">
                {s.has_password && <span title="Password protected"><Lock className="w-3 h-3 text-muted-foreground shrink-0" /></span>}
                <span className="text-foreground flex-1 truncate">{s.title || s.page_path}</span>
                <span className="text-muted-foreground font-mono-deck shrink-0">{s.access_count} view{s.access_count !== 1 ? "s" : ""}</span>
                {s.expires_at && (
                  <span className={cn("text-muted-foreground font-mono-deck shrink-0", s.expired && "text-red-400")}>
                    {s.expired ? "Expired" : `Expires ${new Date(s.expires_at).toLocaleDateString()}`}
                  </span>
                )}
                <button
                  onClick={() => revokeShare(s.share_id)}
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0"
                  title="Revoke"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No shared links for this plugin.</p>
        )}
      </div>

      {actions.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-3">
          <h3 className="font-display text-sm text-foreground">Plugin Actions</h3>
          <PluginActions
            pluginId={pluginId}
            actions={actions}
            slot="settings_tab_footer"
            onAfterAction={() => setActionsTick((t) => t + 1)}
          />
        </div>
      )}

    </div>
  );
}

// ── Generic plugin page ──────────────────────────────────────────────

// v0.10.0.7.1 (Phase 14 / P14.1): cache key for an individual plugin's
// manifest. Exported so the sidebar can prefetch on hover.
export const pluginQueryKey = (pluginId: string) =>
  ["plugin", pluginId, "manifest"] as const;

type PluginManifestData = PluginManifest & {
  dashboards: { name: string; label: string }[];
  actions?: PluginAction[];
  setup_checklist?: { all_done?: boolean; items?: { done: boolean }[] };
};

function GenericPluginPage({ pluginId }: { pluginId: string }) {
  const queryClient = useQueryClient();

  // B144 (v0.9.2.4): update state
  const [updating, setUpdating] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  // B151 (v0.9.4): frontend-trust state — declared at the top with all
  // other hooks so the React rules-of-hooks invariant holds across the
  // early-return guard below (otherwise: error #310 "more hooks than
  // previous render" once `isLoading` flips from true → false).
  const [trusting, setTrusting] = useState(false);
  const [trustError, setTrustError] = useState<string | null>(null);

  // B225: signal "first page ready" once manifest fetch resolves so the
  // boot splash dismisses to reveal real content (not "Loading plugin…" text).
  const { markBootPageReady } = useBootCoordinator();
  const bootMarkedRef = useRef(false);

  // v0.10.0.7.1 (Phase 14 / P14.1): manifest fetch via the shared cache.
  // - Repeat navigation to the same plugin renders instantly from cache.
  // - Sidebar hover prefetch (Sidebar.tsx) warms the cache before the click.
  // - 15s polling when the setup_checklist is incomplete is now declarative
  //   (refetchInterval) instead of a manual setInterval + setHeaderTick.
  // - Tab focus refetch preserved via refetchOnWindowFocus.
  // - Mutation handlers (handleUpdate, handleTrust, etc.) below call
  //   queryClient.invalidateQueries(pluginQueryKey(pluginId)) to refresh.
  const {
    data: manifest,
    isLoading,
    error,
  } = useApiQuery<PluginManifestData>(
    pluginQueryKey(pluginId),
    `/api/plugins/${pluginId}`,
    {
      refetchInterval: (query) => {
        const data = query.state.data;
        const cl = data?.setup_checklist;
        const incomplete =
          !!cl?.items?.length &&
          !(cl.all_done ?? cl.items.every((i) => i.done));
        return incomplete ? 15_000 : false;
      },
      // B149 — refetch on tab focus (override the global default for this query)
      refetchOnWindowFocus: true,
      // A 404 means the plugin doesn't exist; don't retry.
      retry: false,
    },
  );

  const notFound = !!error;

  // Equivalent of the old setHeaderTick(t => t+1) pattern for handlers
  // below that need to force a refresh after a mutation.
  const refetchManifest = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: pluginQueryKey(pluginId) });
  }, [queryClient, pluginId]);

  // B225: mark the boot page ready once the manifest first lands
  // (or the fetch errors out). Mirrors the .finally() callback semantics
  // of the pre-v0.10.0.7.1 implementation.
  useEffect(() => {
    if (!bootMarkedRef.current && (manifest !== undefined || notFound)) {
      bootMarkedRef.current = true;
      markBootPageReady();
    }
  }, [manifest, notFound, markBootPageReady]);

  if (isLoading) return <div className="text-center py-20 text-muted-foreground text-sm">Loading plugin…</div>;
  if (notFound || !manifest) return (
    <div className="text-center py-20">
      <h2 className="font-display text-xl text-foreground mb-2">Plugin not found</h2>
      <p className="text-sm text-muted-foreground">"{pluginId}" is not installed or has no manifest.</p>
    </div>
  );

  const dashboards = manifest.dashboards || [];
  const navItems = manifest.navigation || [];
  const hasSettings = (manifest.settings || []).length > 0;
  const isUtility = (manifest as PluginManifest & { type?: string }).type === "utility";

  // Build tab list from navigation entries — extract the tab slug from href
  const tabs = navItems
    .map((n) => {
      const match = (n.href || n.path || "").match(/\/plugin\/[^/]+\/(.+)/);
      return match ? { slug: match[1], label: n.label } : null;
    })
    .filter(Boolean) as { slug: string; label: string }[];

  // Utility plugins get About + Settings tabs automatically — they don't
  // ship dashboards, so the About page renders manifest info (version,
  // description, publisher, requires) that operators want to see, and
  // Settings is where credentials/config live. The URL slug stays
  // "overview" for backwards-compatible bookmarking; only the tab label
  // changed in v0.8.3 (P111).
  if (isUtility) {
    if (!tabs.some((t) => t.slug === "overview")) {
      tabs.unshift({ slug: "overview", label: "About" });
    }
    if (!tabs.some((t) => t.slug === "settings")) {
      tabs.push({ slug: "settings", label: "Settings" });
    }
  } else {
    // Regular plugins: auto-add Settings if they declare settings fields or connections
    const hasConnections = Array.isArray((manifest as any).connections) && (manifest as any).connections.length > 0;
    if ((hasSettings || hasConnections) && !tabs.some((t) => t.slug === "settings")) {
      tabs.push({ slug: "settings", label: "Settings" });
    }
  }

  // Auto-add Modules tab if plugin declares modules
  const hasModules = Array.isArray((manifest as any).modules) && (manifest as any).modules.length > 0;
  if (hasModules && !tabs.some((t) => t.slug === "modules")) {
    // Insert before Settings
    const settingsIdx = tabs.findIndex((t) => t.slug === "settings");
    if (settingsIdx >= 0) {
      tabs.splice(settingsIdx, 0, { slug: "modules", label: "Modules" });
    } else {
      tabs.push({ slug: "modules", label: "Modules" });
    }
  }

  // B143 (v0.9.2.3): if the plugin declares a setup_checklist and any item
  // is unsatisfied, default landing tab is Settings — not the first dashboard,
  // which would render empty for an unconfigured data plugin and look broken.
  // Once setup is complete, the checklist auto-collapses and we revert to
  // the first-tab default. Backend resolves predicates into `done` flags +
  // `all_done` (see SetupChecklistData); we just read that.
  const checklistRaw = (manifest as PluginManifest & {
    setup_checklist?: { items?: { done: boolean }[]; all_done?: boolean };
  }).setup_checklist;
  const checklistIncomplete =
    !!checklistRaw &&
    Array.isArray(checklistRaw.items) &&
    checklistRaw.items.length > 0 &&
    !(checklistRaw.all_done ?? checklistRaw.items.every((i) => i.done));

  // Default to the first tab (About for utility plugins, first dashboard
  // for data plugins), or fall back to "overview" URL slug — the Routes
  // block always provides a PluginAboutTab at that path.
  // (Slug "overview" kept for URL backwards-compat; tab label reads "About"
  // after v0.8.3 P111.)
  const firstTab =
    checklistIncomplete && tabs.some((t) => t.slug === "settings")
      ? "settings"
      : tabs[0]?.slug || dashboards[0]?.name || "overview";

  const headerActions = manifest.actions || [];
  const loadStatus = (manifest as PluginManifest).load_status;
  const showLoadBanner = loadStatus && loadStatus.routes_registered === false;

  // B144 (v0.9.2.4): update status
  const updateStatus = (manifest as PluginManifest & {
    update_status?: {
      source_class: string;
      installed_version: string | null;
      latest_version: string | null;
      update_available: boolean;
      last_error: string | null;
    };
  }).update_status;
  const showUpdateBanner = !!updateStatus && updateStatus.update_available;

  // B151 (v0.9.4): frontend trust state
  // B304 (v0.10.0.5): admin_proxy opt-in surfaced for trust banner copy
  const frontend = (manifest as PluginManifest & {
    frontend?: {
      components: { name: string; path: string }[];
      trusted: boolean;
      needs_consent: boolean;
      admin_proxy?: boolean;
    };
  }).frontend;
  const showFrontendConsentBanner = !!frontend && frontend.components.length > 0 && !frontend.trusted;
  const adminProxyOptedIn = !!frontend?.admin_proxy;

  const handleTrustFrontend = async () => {
    if (trusting) return;
    setTrusting(true);
    setTrustError(null);
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/trust-frontend`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setTrustError(data?.detail || `Failed (HTTP ${res.status})`);
      } else {
        // Force a hard reload so the loader picks up the now-trusted components.
        window.location.reload();
      }
    } catch (e: unknown) {
      setTrustError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setTrusting(false);
    }
  };

  const handleUpdate = async () => {
    if (updating) return;
    setUpdating(true);
    setUpdateError(null);
    setUpdateMessage(null);
    try {
      const res = await apiFetch(`/api/plugins/${pluginId}/update`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setUpdateError(data?.detail || `Update failed (HTTP ${res.status})`);
      } else {
        setUpdateMessage(
          `Updated ${pluginId}: ${data.from_version || "?"} → ${data.to_version || "?"}`
        );
        // Refetch manifest so the version + update_status reflect the new state
        refetchManifest();
      }
    } catch (e: unknown) {
      setUpdateError(e instanceof Error ? e.message : "Update request failed");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="max-w-[1400px]">
      {showFrontendConsentBanner && (
        <div className="mb-4 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="font-body text-amber-300 font-medium">
                This plugin includes custom frontend code
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                Components: {frontend?.components.map(c => c.name).join(", ")}
              </div>
              <div className="text-xs text-muted-foreground mt-2">
                Plugin frontend code runs in your browser with the same access as NousViz itself
                (session token, DOM, network). Only trust plugins from sources you've audited or authored.
                You can revoke trust at any time from Settings → Plugins.
              </div>
              {adminProxyOptedIn && (
                <div className="text-xs text-amber-200 mt-2 border-t border-amber-500/20 pt-2">
                  <span className="font-medium">Admin proxy:</span> this plugin issues a session cookie
                  scoped to its admin proxy at <code className="text-[11px]">/api/plugins/{pluginId}/admin/*</code>.
                  The cookie is HttpOnly, Secure, and path-scoped to that prefix only — it cannot
                  be used outside the plugin's admin path.
                </div>
              )}
              {trustError && (
                <div className="text-xs text-destructive mt-2">{trustError}</div>
              )}
            </div>
            <button
              type="button"
              onClick={handleTrustFrontend}
              disabled={trusting}
              className={`shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                trusting
                  ? "bg-muted text-muted-foreground cursor-wait"
                  : "bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40"
              }`}
            >
              {trusting ? "Trusting…" : "Trust this plugin"}
            </button>
          </div>
        </div>
      )}
      {showUpdateBanner && (
        <div className="mb-4 rounded-md border border-blue-500/40 bg-blue-500/10 p-3 text-sm flex items-start justify-between gap-3">
          <div>
            <div className="font-body text-blue-300 font-medium">
              Update available
            </div>
            <div className="font-mono-deck text-xs text-blue-300/80 mt-1">
              v{updateStatus?.installed_version || "?"} → v{updateStatus?.latest_version || "?"}
            </div>
            <div className="text-xs text-muted-foreground mt-2">
              Updating will replace the plugin's code from source. Credentials,
              settings, and synced data are preserved.
            </div>
          </div>
          <button
            type="button"
            onClick={handleUpdate}
            disabled={updating}
            className={`shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              updating
                ? "bg-muted text-muted-foreground cursor-wait"
                : "bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 border border-blue-500/40"
            }`}
          >
            {updating ? "Updating…" : "Update plugin"}
          </button>
        </div>
      )}
      {updateMessage && (
        <div className="mb-4 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          {updateMessage}
        </div>
      )}
      {updateError && (
        <div className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          Update failed: {updateError}
        </div>
      )}
      {showLoadBanner && (
        <div className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <div className="font-body text-destructive font-medium">
            This plugin failed to load.
          </div>
          <div className="font-mono-deck text-xs text-destructive/80 mt-1 break-all">
            {loadStatus?.failure_reason || "Unknown error"}
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            Declared action endpoints will return 404 until this is fixed.
            See <a href="/system/logs" className="underline">/system/logs</a> for the full traceback,
            or contact the plugin author.
          </div>
        </div>
      )}
      {headerActions.length > 0 && (
        <div className="flex justify-end mb-3">
          <PluginActions
            pluginId={pluginId}
            actions={headerActions}
            slot="plugin_page_header"
            onAfterAction={() => refetchManifest()}
          />
        </div>
      )}
      {/* Tab navigation — driven by plugin manifest navigation field */}
      <div className="flex items-center gap-1 mb-6 border-b border-border pb-2 sticky top-[calc(var(--topbar-h)+var(--banner-h,0px))] bg-background z-10 -mx-6 px-6 pt-2 overflow-x-auto scrollbar-hide">
        {tabs.map((t) => (
          <NavLink
            key={t.slug}
            to={`/plugin/${pluginId}/${t.slug}`}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded-md text-xs transition-colors whitespace-nowrap shrink-0 ${isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>

      <Routes>
        {/* Dashboard routes first — if a plugin declares a dashboard for a slug, it takes priority */}
        {dashboards.map((d) => (
          <Route
            key={d.name}
            path={d.name}
            element={<DashboardRenderer pluginId={pluginId} dashboardName={d.name} />}
          />
        ))}
        {/* Fallback About tab — only renders if no plugin-authored dashboard
            named "overview" claims this URL. URL stays /overview for
            backwards-compat; tab label renders as "About" (P111). */}
        {!dashboards.some((d) => d.name === "overview") && (
          <Route path="overview" element={<PluginAboutTab manifest={manifest} />} />
        )}
        <Route path="modules" element={<PluginModulesTab pluginId={pluginId} />} />
        <Route path="settings" element={<PluginSettingsTab pluginId={pluginId} />} />
        <Route path="alerts" element={<PluginAlertsTab pluginId={pluginId} tables={manifest.databases?.postgres?.tables ?? []} />} />
        <Route index element={<Navigate to={firstTab} replace />} />
      </Routes>
    </div>
  );
}

export default function PluginPage() {
  const { pluginId } = useParams();

  if (!pluginId) {
    return <div className="text-center py-20 text-muted-foreground">No plugin selected</div>;
  }

  return <GenericPluginPage pluginId={pluginId} />;
}
