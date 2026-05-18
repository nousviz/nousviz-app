import { apiFetch } from "@/lib/api";
import { useState, useEffect } from "react";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import { Share2, Lock, Trash2, Clock, Eye, ChevronDown, ChevronUp, Shield, X as XIcon } from "lucide-react";
import { AccessTab } from "@/components/access/AccessTab";
import { cn } from "@/lib/utils";

interface ShareLink {
  share_id: string;
  title: string;
  page_path: string;
  notes?: string;
  has_password: boolean;
  created_at: string;
  expires_at: string;
  access_count: number;
  revoked: boolean;
  expired: boolean;
}

interface AccessLogEntry {
  accessed_at: string;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
}

export default function SharesPage() {
  useMarkBootReadyOnMount();
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"active" | "expired" | "all">("active");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [accessLog, setAccessLog] = useState<AccessLogEntry[]>([]);
  const [accessShareId, setAccessShareId] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/api/shares")
      .then(r => r.json())
      .then(d => { setLinks(d.links || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = links.filter(l => {
    if (filter === "active") return !l.expired && !l.revoked;
    if (filter === "expired") return l.expired || l.revoked;
    return true;
  });

  const activeCount = links.filter(l => !l.expired && !l.revoked).length;
  const expiredCount = links.filter(l => l.expired || l.revoked).length;

  const handleRevoke = async (shareId: string, views: number) => {
    const msg = views > 0 ? `Revoke? Viewed ${views} time${views !== 1 ? "s" : ""}.` : "Revoke this link?";
    if (!confirm(msg)) return;
    await apiFetch(`/api/shares/${shareId}`, { method: "DELETE" });
    setLinks(prev => prev.map(l => l.share_id === shareId ? { ...l, revoked: true } : l));
  };

  const handleExpand = async (shareId: string) => {
    if (expanded === shareId) { setExpanded(null); return; }
    setExpanded(shareId);
    try {
      const res = await apiFetch(`/api/shares/${shareId}/log`);
      const data = await res.json();
      setAccessLog(data.log || []);
    } catch { setAccessLog([]); }
  };

  return (
    <div className="max-w-[1000px] space-y-6">
      <p className="text-sm text-muted-foreground font-body">
        Dashboard links shared outside this instance. Active shares bypass authentication.
      </p>

      {/* Filter tabs */}
      <div className="flex items-center gap-1">
        {([
          { id: "active" as const, label: `Active (${activeCount})` },
          { id: "expired" as const, label: `Expired / Revoked (${expiredCount})` },
          { id: "all" as const, label: `All (${links.length})` },
        ]).map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-body transition-colors ${
              filter === f.id ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-secondary/30 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="py-16 text-center border border-dashed border-border rounded-lg">
          <Share2 className="w-8 h-8 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            {filter === "active" ? "No active shared links." : "No shared links found."}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Share a dashboard using the share button on any dashboard page.
          </p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map(link => (
            <div key={link.share_id} className={cn(
              "bg-card rounded-lg border p-4",
              link.revoked ? "border-red-500/20" :
              link.expired ? "border-yellow-500/20" :
              "border-border"
            )}>
              {/* Header row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-muted-foreground" />
                  <span className="font-display text-sm text-foreground">{link.title}</span>
                  {link.has_password && <Lock className="w-3 h-3 text-orange-400" />}
                  {link.revoked && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400">Revoked</span>}
                  {link.expired && !link.revoked && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400">Expired</span>}
                  {!link.expired && !link.revoked && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400">Active</span>}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleExpand(link.share_id)}
                    className="h-8 px-2 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                    {expanded === link.share_id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                  <button
                    onClick={() => setAccessShareId(link.share_id)}
                    className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                    title="Access"
                  >
                    <Shield className="w-3.5 h-3.5" />
                  </button>
                  {!link.revoked && !link.expired && (
                    <button
                      onClick={() => handleRevoke(link.share_id, link.access_count)}
                      className="h-8 w-8 rounded-md bg-red-500/10 hover:bg-red-500/20 flex items-center justify-center text-red-400 transition-colors"
                      title="Revoke"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Metadata row */}
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span className="font-mono-deck">{link.page_path}</span>
                <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {link.access_count} view{link.access_count !== 1 ? "s" : ""}</span>
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> expires {new Date(link.expires_at).toLocaleDateString()}</span>
                <span>created {new Date(link.created_at).toLocaleDateString()}</span>
              </div>

              {link.notes && (
                <p className="text-xs text-muted-foreground mt-1 italic">{link.notes}</p>
              )}

              {/* Expanded: access log */}
              {expanded === link.share_id && (
                <div className="mt-3 border-t border-border pt-3">
                  <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-2">Access Log</p>
                  {accessLog.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No access recorded.</p>
                  ) : (
                    <div className="space-y-1">
                      {accessLog.map((entry, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className={entry.success ? "text-green-400" : "text-red-400"}>
                              {entry.success ? "✓" : "✗"}
                            </span>
                            <span className="font-mono-deck text-foreground">{entry.ip_address || "unknown"}</span>
                          </div>
                          <span className="text-muted-foreground">{new Date(entry.accessed_at).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Share URL for reference */}
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`${window.location.origin}/shared/${link.share_id}`}
                      className="flex-1 h-7 px-2 rounded bg-background border border-border text-[11px] font-mono-deck text-foreground"
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {accessShareId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setAccessShareId(null)}>
          <div className="bg-card border border-border rounded-lg p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-base text-foreground">
                Access — {links.find((l) => l.share_id === accessShareId)?.title ?? accessShareId}
              </h3>
              <button onClick={() => setAccessShareId(null)} className="text-muted-foreground hover:text-foreground">
                <XIcon className="w-4 h-4" />
              </button>
            </div>
            <AccessTab
              resourceType="share"
              resourceId={accessShareId}
              permissions={["shares.read", "shares.write"]}
            />
          </div>
        </div>
      )}
    </div>
  );
}
