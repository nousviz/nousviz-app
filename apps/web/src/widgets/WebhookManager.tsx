import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Plus, Trash2, Copy, Check, Zap, ArrowUpRight, ArrowDownLeft, Play, Settings, X } from "lucide-react";
import type { CustomWidgetProps } from "./plugin-components";

type ChannelType = "generic" | "slack" | "discord" | "teams";

interface SlackChannelConfig {
  mention_user_ids?: string[];
  mention_on_severities?: string[];
  channel_override?: string;
}

interface Endpoint {
  id: string;
  name: string;
  slug: string | null;
  direction: string;
  url: string | null;
  has_secret: boolean;
  is_active: boolean;
  event_count: number;
  last_event_at: string | null;
  created_at: string;
  ingestion_url?: string;
  secret?: string;
  // B283 (v0.9.11.24): typed channel + per-channel config.
  channel_type?: ChannelType;
  channel_config?: SlackChannelConfig | Record<string, unknown>;
}

interface WebhookEvent {
  id: string;
  payload: Record<string, unknown>;
  source_ip: string;
  received_at: string;
}

export default function WebhookManager(_props: CustomWidgetProps) {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState<"inbound" | "outbound" | null>(null);
  const [createName, setCreateName] = useState("");
  const [createUrl, setCreateUrl] = useState("");
  const [createSecret, setCreateSecret] = useState(false);
  const [creating, setCreating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; message: string } | null>(null);
  // B283 (v0.9.11.24): inline channel-type editor state. `null` = closed; otherwise the endpoint id being edited.
  const [editingChannelId, setEditingChannelId] = useState<string | null>(null);
  const [editChannelType, setEditChannelType] = useState<ChannelType>("generic");
  const [editMentionIds, setEditMentionIds] = useState<string>("");  // comma-separated input
  const [editMentionSeverities, setEditMentionSeverities] = useState<Set<string>>(new Set(["critical", "error"]));
  const [editChannelOverride, setEditChannelOverride] = useState<string>("");
  const [editError, setEditError] = useState<string | null>(null);
  const [savingChannel, setSavingChannel] = useState(false);

  const load = useCallback(() => {
    apiFetch("/api/plugins/webhooks/endpoints")
      .then(r => r.json())
      .then(d => { setEndpoints(d.endpoints || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate() {
    if (!createName.trim()) return;
    if (showCreate === "outbound" && !createUrl.trim()) return;
    setCreating(true);
    const res = await apiFetch("/api/plugins/webhooks/endpoints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: createName.trim(),
        direction: showCreate,
        url: showCreate === "outbound" ? createUrl.trim() : undefined,
        generate_secret: createSecret,
      }),
    });
    setCreating(false);
    if (res.ok) {
      const data = await res.json();
      setEndpoints(prev => [data, ...prev]);
      setCreateName("");
      setCreateUrl("");
      setCreateSecret(false);
      setShowCreate(null);
      if (data.ingestion_url) {
        setCopiedId(data.id);
        navigator.clipboard.writeText(data.ingestion_url);
        setTimeout(() => setCopiedId(null), 3000);
      }
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this webhook? This cannot be undone.")) return;
    await apiFetch(`/api/plugins/webhooks/endpoints/${id}`, { method: "DELETE" });
    setEndpoints(prev => prev.filter(e => e.id !== id));
    if (expandedId === id) setExpandedId(null);
  }

  async function handleToggle(id: string, active: boolean) {
    await apiFetch(`/api/plugins/webhooks/endpoints/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !active }),
    });
    setEndpoints(prev => prev.map(e => e.id === id ? { ...e, is_active: !active } : e));
  }

  async function handleTest(id: string) {
    setTestResult(null);
    const res = await apiFetch(`/api/plugins/webhooks/endpoints/${id}/test`, { method: "POST" });
    const d = await res.json();
    setTestResult({ id, ok: d.ok, message: d.ok ? `Sent (${d.status})` : d.error || "Failed" });
    setTimeout(() => setTestResult(null), 5000);
  }

  async function loadEvents(id: string) {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    const res = await apiFetch(`/api/plugins/webhooks/events/${id}`);
    const d = await res.json();
    setEvents(d.events || []);
  }

  function copyUrl(url: string, id: string) {
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  // ── B283: channel-type editor handlers ─────────────────────────────

  function openChannelEditor(ep: Endpoint) {
    setEditingChannelId(ep.id);
    setEditError(null);
    setEditChannelType((ep.channel_type as ChannelType) || "generic");
    const cfg = (ep.channel_config || {}) as SlackChannelConfig;
    setEditMentionIds((cfg.mention_user_ids || []).join(", "));
    setEditMentionSeverities(new Set(cfg.mention_on_severities || ["critical", "error"]));
    setEditChannelOverride(cfg.channel_override || "");
  }

  function closeChannelEditor() {
    setEditingChannelId(null);
    setEditError(null);
  }

  async function saveChannelConfig(id: string) {
    setSavingChannel(true);
    setEditError(null);
    try {
      let channel_config: SlackChannelConfig = {};
      if (editChannelType === "slack") {
        const ids = editMentionIds
          .split(/[\s,]+/)
          .map((s) => s.trim())
          .filter(Boolean);
        if (ids.length > 0) channel_config.mention_user_ids = ids;
        if (editMentionSeverities.size > 0) {
          channel_config.mention_on_severities = Array.from(editMentionSeverities);
        }
        const override = editChannelOverride.trim();
        if (override) channel_config.channel_override = override;
      }
      const res = await apiFetch(`/api/plugins/webhooks/endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_type: editChannelType,
          channel_config,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({} as { detail?: string }));
        setEditError(`Save failed (${res.status}): ${err.detail ?? "unknown"}`);
        return;
      }
      // Optimistically update local state.
      setEndpoints((prev) =>
        prev.map((e) =>
          e.id === id
            ? { ...e, channel_type: editChannelType, channel_config }
            : e,
        ),
      );
      closeChannelEditor();
    } catch (e) {
      setEditError(`Save error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSavingChannel(false);
    }
  }

  function toggleMentionSeverity(s: string) {
    setEditMentionSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }

  const inbound = endpoints.filter(e => e.direction === "inbound");
  const outbound = endpoints.filter(e => e.direction === "outbound");

  if (loading) return <p className="text-sm text-muted-foreground py-4">Loading...</p>;

  return (
    <div className="space-y-8">
      {/* Inbound */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowDownLeft className="w-4 h-4 text-green-400" />
            <h3 className="font-display text-sm text-foreground">Inbound Webhooks</h3>
            <span className="text-[10px] text-muted-foreground font-mono-deck">{inbound.length} endpoint{inbound.length !== 1 ? "s" : ""}</span>
          </div>
          <button
            onClick={() => setShowCreate(showCreate === "inbound" ? null : "inbound")}
            className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
        </div>
        <p className="text-xs text-muted-foreground">Receive data from external services. Each endpoint generates a unique URL — external services POST JSON here.</p>

        {showCreate === "inbound" && (
          <div className="bg-secondary/30 rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Name</label>
                <input
                  value={createName}
                  onChange={e => setCreateName(e.target.value)}
                  placeholder="e.g. GitHub Events"
                  autoComplete="off"
                  autoFocus
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <label className="flex items-center gap-2 h-9 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" checked={createSecret} onChange={e => setCreateSecret(e.target.checked)} className="rounded border-border" />
                Signing secret
              </label>
              <button onClick={handleCreate} disabled={creating || !createName.trim()} className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50">
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        )}

        {inbound.length > 0 ? (
          <div className="space-y-1.5">
            {inbound.map(ep => {
              const fullUrl = `${window.location.origin}/api/webhooks/in/${ep.slug}`;
              return (
              <div key={ep.id}>
                <div className="rounded-md bg-card border border-border px-3 py-2.5 space-y-2">
                  <div className="flex items-center gap-2 text-xs">
                    <Zap className={cn("w-3.5 h-3.5 shrink-0", ep.is_active ? "text-green-400" : "text-muted-foreground")} />
                    <span className="text-foreground font-medium">{ep.name}</span>
                    <span className="text-muted-foreground font-mono-deck shrink-0">{ep.event_count} event{ep.event_count !== 1 ? "s" : ""}</span>
                    {ep.last_event_at && <span className="text-muted-foreground font-mono-deck shrink-0">{formatRelativeTime(ep.last_event_at)}</span>}
                    <span className="flex-1" />
                    <button onClick={() => loadEvents(ep.id)} className="text-muted-foreground hover:text-foreground shrink-0 text-[10px]">
                      {expandedId === ep.id ? "Hide" : "Events"}
                    </button>
                    <button onClick={() => handleToggle(ep.id, ep.is_active)} className={cn("shrink-0 text-[10px]", ep.is_active ? "text-green-400" : "text-muted-foreground")}>
                      {ep.is_active ? "Active" : "Paused"}
                    </button>
                  <button onClick={() => handleDelete(ep.id)} className="text-muted-foreground hover:text-red-400 shrink-0">
                    <Trash2 className="w-3 h-3" />
                  </button>
                  </div>
                  <div className="flex items-center gap-2 bg-secondary/30 rounded px-2.5 py-1.5">
                    <code className="flex-1 text-[11px] font-mono-deck text-foreground truncate select-all">{fullUrl}</code>
                    <button onClick={() => copyUrl(fullUrl, ep.id)} className="shrink-0 h-6 px-2 rounded bg-secondary text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
                      {copiedId === ep.id ? <><Check className="w-3 h-3 text-green-400" /> Copied</> : <><Copy className="w-3 h-3" /> Copy URL</>}
                    </button>
                  </div>
                </div>
                {expandedId === ep.id && (
                  <div className="ml-6 mt-1 space-y-1 max-h-48 overflow-y-auto">
                    {events.length > 0 ? events.map(ev => (
                      <div key={ev.id} className="px-3 py-2 rounded bg-secondary/20 text-[11px] font-mono-deck">
                        <div className="flex items-center justify-between text-muted-foreground mb-1">
                          <span>{ev.source_ip}</span>
                          <span>{formatRelativeTime(ev.received_at)}</span>
                        </div>
                        <pre className="text-foreground whitespace-pre-wrap break-all max-h-24 overflow-y-auto">{JSON.stringify(ev.payload, null, 2)}</pre>
                      </div>
                    )) : (
                      <p className="text-[11px] text-muted-foreground px-3 py-2">No events yet.</p>
                    )}
                  </div>
                )}
              </div>
            );
            })}
          </div>
        ) : !showCreate && (
          <p className="text-xs text-muted-foreground py-2">No inbound webhooks. Create one to start receiving data.</p>
        )}
      </div>

      {/* Outbound */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowUpRight className="w-4 h-4 text-blue-400" />
            <h3 className="font-display text-sm text-foreground">Outbound Webhooks</h3>
            <span className="text-[10px] text-muted-foreground font-mono-deck">{outbound.length} endpoint{outbound.length !== 1 ? "s" : ""}</span>
          </div>
          <button
            onClick={() => setShowCreate(showCreate === "outbound" ? null : "outbound")}
            className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
        </div>
        <p className="text-xs text-muted-foreground">Send alert notifications to external services. Select these as notification channels when creating alerts.</p>

        {showCreate === "outbound" && (
          <div className="bg-secondary/30 rounded-lg border border-border p-4 space-y-3">
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Name</label>
                <input
                  value={createName}
                  onChange={e => setCreateName(e.target.value)}
                  placeholder="e.g. Slack Ops"
                  autoComplete="off"
                  autoFocus
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Destination URL</label>
                <input
                  value={createUrl}
                  onChange={e => setCreateUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  autoComplete="off"
                  className="w-full h-9 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" checked={createSecret} onChange={e => setCreateSecret(e.target.checked)} className="rounded border-border" />
                Include signing secret (HMAC-SHA256)
              </label>
              <button onClick={handleCreate} disabled={creating || !createName.trim() || !createUrl.trim()} className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50">
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        )}

        {outbound.length > 0 ? (
          <div className="space-y-1.5">
            {outbound.map(ep => {
              const channelType = (ep.channel_type as ChannelType) || "generic";
              const isEditing = editingChannelId === ep.id;
              return (
              <div key={ep.id}>
                <div className="flex items-center gap-2 px-3 py-2.5 rounded-md bg-card border border-border text-xs">
                  <Zap className={cn("w-3.5 h-3.5 shrink-0", ep.is_active ? "text-blue-400" : "text-muted-foreground")} />
                  <span className="text-foreground font-medium truncate">{ep.name}</span>
                  <button
                    onClick={() => (isEditing ? closeChannelEditor() : openChannelEditor(ep))}
                    className={cn(
                      "shrink-0 text-[10px] font-mono-deck px-1.5 py-0.5 rounded border flex items-center gap-1",
                      channelType === "slack"
                        ? "border-purple-500/30 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20"
                        : "border-border bg-secondary/40 text-muted-foreground hover:text-foreground",
                    )}
                    title="Channel type — click to configure"
                  >
                    {channelType === "slack" ? "slack" : channelType}
                    <Settings className="w-2.5 h-2.5" />
                  </button>
                  <span className="text-[10px] font-mono-deck text-muted-foreground truncate max-w-[200px]">{ep.url}</span>
                  <button onClick={() => handleTest(ep.id)} className="text-muted-foreground hover:text-foreground shrink-0 flex items-center gap-1 text-[10px]">
                    <Play className="w-2.5 h-2.5" /> Test
                  </button>
                  {testResult?.id === ep.id && (
                    <span className={cn("text-[10px] shrink-0", testResult.ok ? "text-green-400" : "text-red-400")}>{testResult.message}</span>
                  )}
                  <button onClick={() => handleToggle(ep.id, ep.is_active)} className={cn("shrink-0 text-[10px]", ep.is_active ? "text-green-400" : "text-muted-foreground")}>
                    {ep.is_active ? "Active" : "Paused"}
                  </button>
                  <button onClick={() => handleDelete(ep.id)} className="text-muted-foreground hover:text-red-400 shrink-0">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                {isEditing && (
                  <div className="ml-6 mt-1 mb-2 px-4 py-3 rounded-md bg-secondary/30 border border-border space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[11px] font-display text-foreground">Channel configuration</h4>
                      <button onClick={closeChannelEditor} className="text-muted-foreground hover:text-foreground">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                    <div>
                      <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Channel type</label>
                      <select
                        value={editChannelType}
                        onChange={(e) => setEditChannelType(e.target.value as ChannelType)}
                        className="w-full h-8 px-2 rounded bg-background border border-border text-xs text-foreground"
                      >
                        <option value="generic">Generic webhook (today's flat payload)</option>
                        <option value="slack">Slack (Block Kit formatting)</option>
                        <option value="discord" disabled>Discord — coming in a future release</option>
                        <option value="teams" disabled>Microsoft Teams — coming in a future release</option>
                      </select>
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {editChannelType === "slack"
                          ? "Slack incoming webhooks render Block Kit (severity color bar, structured fields, action button)."
                          : "Generic webhooks receive the flat payload — no behavior change for Discord, Teams, or custom HTTP receivers."}
                      </p>
                    </div>
                    {editChannelType === "slack" && (
                      <div className="space-y-3 pt-2 border-t border-border/50">
                        <div>
                          <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Mention user IDs</label>
                          <input
                            value={editMentionIds}
                            onChange={(e) => setEditMentionIds(e.target.value)}
                            placeholder="U06ABC123, U07XYZ789"
                            className="w-full h-8 px-2 rounded bg-background border border-border text-xs font-mono-deck text-foreground"
                          />
                          <p className="text-[10px] text-muted-foreground mt-1">
                            Slack member IDs (start with U). Find yours: Slack profile menu → "Copy member ID".
                          </p>
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Mention on severities</label>
                          <div className="flex flex-wrap gap-1.5">
                            {["critical", "error", "warning", "timeout"].map((s) => (
                              <label
                                key={s}
                                className={cn(
                                  "text-[10px] font-mono-deck px-1.5 py-0.5 rounded border cursor-pointer flex items-center gap-1",
                                  editMentionSeverities.has(s)
                                    ? "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                                    : "border-border bg-secondary/40 text-muted-foreground",
                                )}
                              >
                                <input
                                  type="checkbox"
                                  checked={editMentionSeverities.has(s)}
                                  onChange={() => toggleMentionSeverity(s)}
                                  className="hidden"
                                />
                                {editMentionSeverities.has(s) && <Check className="w-2.5 h-2.5" />}
                                {s}
                              </label>
                            ))}
                          </div>
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-1 block">Channel override (optional)</label>
                          <input
                            value={editChannelOverride}
                            onChange={(e) => setEditChannelOverride(e.target.value)}
                            placeholder="#data-eng"
                            className="w-full h-8 px-2 rounded bg-background border border-border text-xs font-mono-deck text-foreground"
                          />
                          <p className="text-[10px] text-muted-foreground mt-1">
                            Only honored if the Slack incoming webhook is configured for cross-channel posting.
                          </p>
                        </div>
                      </div>
                    )}
                    {editError && (
                      <div className="bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
                        <p className="text-[11px] text-red-300">{editError}</p>
                      </div>
                    )}
                    <div className="flex items-center justify-end gap-2 pt-1">
                      <button
                        onClick={closeChannelEditor}
                        className="h-7 px-3 rounded text-xs text-muted-foreground hover:text-foreground"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => saveChannelConfig(ep.id)}
                        disabled={savingChannel}
                        className="h-7 px-3 rounded bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50"
                      >
                        {savingChannel ? "Saving…" : "Save"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
              );
            })}
          </div>
        ) : !showCreate && (
          <p className="text-xs text-muted-foreground py-2">No outbound webhooks. Create one, then select it as a notification channel when creating alerts.</p>
        )}
      </div>
    </div>
  );
}
