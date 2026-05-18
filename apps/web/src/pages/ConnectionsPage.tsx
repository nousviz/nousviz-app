import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, AlertCircle, RefreshCw, Database, Server, Settings, Plus, Trash2, Star, Play, Zap, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { cn, formatStatus, formatRelativeTime } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface Connection {
  id: string;
  name: string;
  type: string;
  config: Record<string, string>;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

interface ServiceStatus {
  name: string;
  status: string;
  version?: string;
  tables?: number;
}

interface WebhookEndpoint {
  id: string;
  name: string;
  direction: string;
  is_active: boolean;
  event_count: number;
  last_event_at: string | null;
}

const TYPE_LABELS: Record<string, string> = { postgres: "PostgreSQL", mysql: "MySQL", clickhouse: "ClickHouse" };
const TYPE_ICONS: Record<string, string> = { postgres: "bg-blue-500/10 text-blue-400", mysql: "bg-orange-500/10 text-orange-400", clickhouse: "bg-yellow-500/10 text-yellow-400" };
const TYPE_FIELDS: Record<string, { name: string; label: string; type: string; default?: string }[]> = {
  postgres: [
    { name: "host", label: "Host", type: "text", default: "localhost" },
    { name: "port", label: "Port", type: "text", default: "5432" },
    { name: "user", label: "Username", type: "text" },
    { name: "password", label: "Password", type: "password" },
    { name: "database", label: "Database", type: "text" },
  ],
  mysql: [
    { name: "host", label: "Host", type: "text", default: "localhost" },
    { name: "port", label: "Port", type: "text", default: "3306" },
    { name: "user", label: "Username", type: "text" },
    { name: "password", label: "Password", type: "password" },
    { name: "database", label: "Database", type: "text" },
  ],
  clickhouse: [
    { name: "host", label: "Host", type: "text", default: "localhost" },
    { name: "port", label: "HTTP Port", type: "text", default: "8123" },
    { name: "user", label: "Username", type: "text", default: "default" },
    { name: "password", label: "Password", type: "password" },
    { name: "database", label: "Database", type: "text", default: "default" },
  ],
};

export default function ConnectionsPage() {
  useMarkBootReadyOnMount();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [services, setServices] = useState<Record<string, ServiceStatus>>({});
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState<string | null>(null);
  const [createName, setCreateName] = useState("");
  const [createConfig, setCreateConfig] = useState<Record<string, string>>({});
  const [createDefault, setCreateDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; detail: string } | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiFetch("/api/connections").then(r => r.ok ? r.json() : { connections: [] }),
      fetch("/api/health", { cache: "no-store" }).then(r => r.ok ? r.json() : { services: {} }),
      apiFetch("/api/plugins/webhooks/endpoints").then(r => r.ok ? r.json() : { endpoints: [] }).catch(() => ({ endpoints: [] })),
    ]).then(([c, h, w]) => {
      setConnections(c.connections || []);
      setServices(h.services || {});
      setWebhooks(w.endpoints || []);
      setLoading(false);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate() {
    if (!showCreate || !createName.trim()) return;
    setSaving(true);
    const res = await apiFetch("/api/connections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: createName.trim(), type: showCreate, config: createConfig, is_default: createDefault }),
    });
    setSaving(false);
    if (res.ok) {
      setShowCreate(null);
      setCreateName("");
      setCreateConfig({});
      setCreateDefault(false);
      load();
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this connection?")) return;
    await apiFetch(`/api/connections/${id}`, { method: "DELETE" });
    load();
  }

  async function handleToggleDefault(id: string, current: boolean) {
    await apiFetch(`/api/connections/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_default: !current }),
    });
    load();
  }

  async function handleTest(id: string) {
    setTestResult(null);
    const res = await apiFetch(`/api/connections/${id}/test`, { method: "POST" });
    const d = await res.json();
    setTestResult({ id, ok: d.ok, detail: d.ok ? d.detail : d.error });
    setTimeout(() => setTestResult(null), 8000);
  }

  const operatorConnections = connections.filter(c => !c.name.startsWith("plugin:"));
  const pluginConnections = connections.filter(c => c.name.startsWith("plugin:"));

  const grouped: Record<string, Connection[]> = {};
  for (const c of operatorConnections) {
    (grouped[c.type] = grouped[c.type] || []).push(c);
  }

  const pgStatus = services.postgres;
  const utilityServices = Object.entries(services).filter(([key]) => key !== "postgres");

  return (
    <div className="max-w-[1000px] space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground font-body">Database connections, services, and integrations.</p>
        <button onClick={load} disabled={loading}
          className="h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground flex items-center gap-2 disabled:opacity-50">
          <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Core PostgreSQL */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <Database className="w-5 h-5 text-blue-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-display text-sm text-foreground">PostgreSQL</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">Core</span>
              {pgStatus?.status === "connected" ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-400" />
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {pgStatus?.version?.replace("PostgreSQL ", "") || "Checking..."} {pgStatus?.tables ? `· ${pgStatus.tables} tables` : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Utility services */}
      {utilityServices.map(([name, svc]) => (
        <div key={name} className="bg-card rounded-lg border border-border p-5">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center">
              <Server className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                {/* B165 D5: utility name → /plugin/<slug> (the slug IS the service name for utility plugins) */}
                <Link to={`/plugin/${name}`} className="font-display text-sm text-foreground capitalize hover:text-primary transition-colors">
                  {name}
                </Link>
                {svc.status === "connected" ? <CheckCircle2 className="w-4 h-4 text-green-400" /> : <AlertCircle className="w-4 h-4 text-yellow-400" />}
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full", svc.status === "connected" ? "bg-green-500/10 text-green-400" : "bg-yellow-500/10 text-yellow-400")}>
                  {formatStatus(svc.status)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Utility plugin{svc.version ? ` · ${svc.version}` : ""}</p>
            </div>
            {/* B165 D3 (scoped to utility services where the plugin slug is known —
                see ticket "D3 limitation" for why named connections don't get this yet) */}
            <Link to={`/datasets?plugin=${name}`} className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors shrink-0">
              <Database className="w-3 h-3" /> Datasets
            </Link>
            <Link to={`/plugin/${name}/settings`} className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors shrink-0">
              <Settings className="w-3 h-3" /> Configure
            </Link>
          </div>
        </div>
      ))}

      {/* Your Connections (operator-defined) */}
      {/* Connection types are gated by which drivers are installed:
          postgres is always available (core service); mysql/clickhouse only
          if their utility plugin shows up in /api/health.services. */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-sm text-foreground">Your Connections</h3>
          <div className="flex items-center gap-2">
            {(["postgres", "mysql", "clickhouse"] as const)
              .filter(t => t === "postgres" || services[t])
              .map(t => (
                <button key={t} onClick={() => setShowCreate(showCreate === t ? null : t)}
                  className={cn("h-8 px-3 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors",
                    showCreate === t ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
                  )}>
                  <Plus className="w-3 h-3" /> {TYPE_LABELS[t]}
                </button>
              ))}
          </div>
        </div>

        {showCreate && (
          <div className="bg-secondary/30 rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs font-display text-foreground">New {TYPE_LABELS[showCreate]} Connection</span>
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Connection Name</label>
              <input value={createName} onChange={e => setCreateName(e.target.value)} placeholder={`e.g. ${TYPE_LABELS[showCreate]} Production`}
                autoComplete="off" autoFocus
                className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
            </div>
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2">
              {(TYPE_FIELDS[showCreate] || []).map(f => (
                <div key={f.name}>
                  <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">{f.label}</label>
                  <input
                    type={f.type === "password" ? "password" : "text"}
                    value={createConfig[f.name] || ""}
                    onChange={e => setCreateConfig(c => ({ ...c, [f.name]: e.target.value }))}
                    placeholder={f.default || ""}
                    autoComplete="off"
                    className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" checked={createDefault} onChange={e => setCreateDefault(e.target.checked)} className="rounded border-border" />
                Set as default for {TYPE_LABELS[showCreate]}
              </label>
              <button onClick={handleCreate} disabled={saving || !createName.trim()}
                className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50">
                {saving ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        )}

        {Object.entries(grouped).map(([type, conns]) => (
          <div key={type} className="space-y-1.5">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">{TYPE_LABELS[type] || type}</p>
            {conns.map(c => (
              <div key={c.id} className="flex items-center gap-3 px-4 py-3 rounded-md bg-card border border-border text-xs hover:border-primary/40 transition-colors">
                <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center shrink-0", TYPE_ICONS[c.type] || "bg-secondary")}>
                  <Database className="w-4 h-4" />
                </div>
                <Link to={`/connections/${c.id}`} className="flex-1 min-w-0 group">
                  <div className="flex items-center gap-2">
                    <span className="text-foreground font-medium group-hover:text-primary transition-colors">{c.name}</span>
                  </div>
                  <p className="text-muted-foreground font-mono-deck truncate">
                    {c.config.host || "localhost"}:{c.config.port || (c.type === "mysql" ? "3306" : c.type === "clickhouse" ? "8123" : "5432")}
                    {c.config.database ? ` / ${c.config.database}` : ""}
                  </p>
                </Link>
                <button onClick={() => handleTest(c.id)} className="text-muted-foreground hover:text-foreground shrink-0 flex items-center gap-1 text-[10px]">
                  <Play className="w-2.5 h-2.5" /> Test
                </button>
                {testResult?.id === c.id && (
                  <span className={cn("text-[10px] shrink-0 max-w-[150px] truncate", testResult.ok ? "text-green-400" : "text-red-400")}>
                    {testResult.detail}
                  </span>
                )}
                <button
                  onClick={() => handleToggleDefault(c.id, c.is_default)}
                  className={cn("shrink-0", c.is_default ? "text-yellow-400 hover:text-muted-foreground" : "text-muted-foreground hover:text-yellow-400")}
                  title={c.is_default ? "Unset as default" : "Set as default"}
                >
                  <Star className={cn("w-3 h-3", c.is_default && "fill-yellow-400")} />
                </button>
                <button onClick={() => handleDelete(c.id)} className="text-muted-foreground hover:text-red-400 shrink-0">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        ))}

        {operatorConnections.length === 0 && !showCreate && (
          <p className="text-xs text-muted-foreground py-2">No external connections yet. Add one to query data from external databases.</p>
        )}
      </div>

      {/* Plugin Connections (read-only synthetic) */}
      {pluginConnections.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm text-foreground">Plugin Connections</h3>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Managed by plugins</span>
          </div>
          <div className="space-y-1.5">
            {pluginConnections.map(c => {
              const slug = c.name.slice("plugin:".length);
              return (
                <div key={c.id} className="flex items-center gap-3 px-4 py-3 rounded-md bg-card border border-border text-xs">
                  <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center shrink-0", TYPE_ICONS[c.type] || "bg-secondary")}>
                    <Database className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-foreground font-medium">{c.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">Plugin</span>
                    </div>
                    <p className="text-muted-foreground font-mono-deck truncate">
                      Credentials managed in plugin settings
                    </p>
                  </div>
                  <Link to={`/plugin/${slug}/settings`} className="h-7 px-2.5 rounded-md bg-secondary text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors shrink-0">
                    <Settings className="w-3 h-3" /> Open plugin →
                  </Link>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Webhook endpoints */}
      {webhooks.length > 0 && (
        <div className="bg-card rounded-lg border border-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-secondary flex items-center justify-center">
                <Zap className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <span className="font-display text-sm text-foreground">Webhooks</span>
                <p className="text-xs text-muted-foreground mt-0.5">{webhooks.length} endpoint{webhooks.length !== 1 ? "s" : ""}</p>
              </div>
            </div>
            <Link to="/plugin/webhooks" className="h-8 px-3 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors shrink-0">
              <Settings className="w-3 h-3" /> Manage
            </Link>
          </div>
          <div className="space-y-1.5">
            {webhooks.map(ep => (
              <div key={ep.id} className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/30 text-xs">
                {ep.direction === "inbound" ? <ArrowDownLeft className="w-3 h-3 text-green-400 shrink-0" /> : <ArrowUpRight className="w-3 h-3 text-blue-400 shrink-0" />}
                <span className="text-foreground font-medium truncate">{ep.name}</span>
                <span className="text-[10px] text-muted-foreground font-mono-deck">{ep.direction}</span>
                <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", ep.is_active ? "bg-green-400" : "bg-muted-foreground/30")} />
                {ep.event_count > 0 && <span className="text-muted-foreground font-mono-deck shrink-0">{ep.event_count} events</span>}
                {ep.last_event_at && <span className="text-muted-foreground font-mono-deck shrink-0">{formatRelativeTime(ep.last_event_at)}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
