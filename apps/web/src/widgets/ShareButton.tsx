import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Share2, Link2, Lock, Check, X, Copy, Clock, Trash2, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

interface ExistingShare {
  share_id: string;
  title: string;
  page_path: string;
  notes?: string;
  has_password: boolean;
  expires_at: string;
  access_count: number;
  expired: boolean;
  revoked: boolean;
}

interface AccessLogEntry {
  accessed_at: string;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
}

export default function ShareButton() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"loading" | "existing" | "create" | "result">("loading");
  const [existing, setExisting] = useState<ExistingShare[]>([]);
  const [expandedShare, setExpandedShare] = useState<string | null>(null);
  const [accessLog, setAccessLog] = useState<AccessLogEntry[]>([]);
  const [editTitle, setEditTitle] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [password, setPassword] = useState("");
  const [usePassword, setUsePassword] = useState(false);
  const [expireHours, setExpireHours] = useState(168);
  const [result, setResult] = useState<{ url: string; share_id: string; has_password: boolean } | null>(null);
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);

  // Only show on plugin dashboard tabs (not overview/settings/alerts)
  const isPlugin = /^\/plugin\/[^/]+\/[^/]+$/.test(location.pathname);
  const excluded = ["/settings", "/alerts", "/overview"];
  const isShareable = isPlugin && !excluded.some(e => location.pathname.endsWith(e));

  // Load existing shares on mount + when page changes (for badge indicator)
  useEffect(() => {
    if (!isShareable) return;
    apiFetch("/api/shares")
      .then(r => r.json())
      .then(data => {
        const active = (data.links || []).filter(
          (l: ExistingShare) => l.page_path === location.pathname && !l.expired && !l.revoked
        );
        setExisting(active);
      })
      .catch(() => {});
  }, [location.pathname, isShareable]);

  // Set mode when dropdown opens
  useEffect(() => {
    if (!open) return;
    setMode(existing.length > 0 ? "existing" : "create");
  }, [open, existing.length]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await apiFetch("/api/shares", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          page_path: location.pathname,
          title: document.title,
          resource_type: "plugin_dashboard",
          filters: {},
          password: usePassword && password ? password : null,
          expires_hours: expireHours,
        }),
      });
      const data = await res.json();
      setResult(data);
      setMode("result");
    } finally {
      setCreating(false);
    }
  };

  const handleExpand = async (share: ExistingShare) => {
    if (expandedShare === share.share_id) { setExpandedShare(null); return; }
    setExpandedShare(share.share_id);
    setEditTitle(share.title);
    setEditNotes(share.notes || "");
    // Load access log
    try {
      const res = await apiFetch(`/api/shares/${share.share_id}/log`);
      const data = await res.json();
      setAccessLog(data.log || []);
    } catch { setAccessLog([]); }
  };

  const handleSaveEdit = async (shareId: string) => {
    setSaving(true);
    try {
      await apiFetch(`/api/shares/${shareId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: editTitle, notes: editNotes }),
      });
      setExisting(prev => prev.map(s => s.share_id === shareId ? { ...s, title: editTitle, notes: editNotes } : s));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  };

  const handleRevoke = async (shareId: string, accessCount: number) => {
    const msg = accessCount > 0
      ? `Revoke this link? It has been viewed ${accessCount} time${accessCount !== 1 ? "s" : ""}.`
      : "Revoke this link?";
    if (!confirm(msg)) return;
    await apiFetch(`/api/shares/${shareId}`, { method: "DELETE" });
    setExisting(prev => prev.filter(s => s.share_id !== shareId));
    if (existing.length <= 1) setMode("create");
  };

  const handleCopy = (url: string) => {
    const fullUrl = `${window.location.origin}${url}`;
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setOpen(false);
    setResult(null);
    setPassword("");
    setUsePassword(false);
    setCopied(false);
  };

  // Always render for consistent topbar layout — disabled when not shareable
  if (!isShareable) {
    return (
      <button
        disabled
        className="h-9 w-9 rounded-md bg-secondary flex items-center justify-center text-muted-foreground/30 cursor-not-allowed"
        title="Sharing available on dashboard pages"
      >
        <Share2 className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="h-9 w-9 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
        title={existing.length > 0 ? `${existing.length} active share link${existing.length !== 1 ? "s" : ""}` : "Share this page"}
      >
        <Share2 className="h-4 w-4" />
      </button>
      {/* Active shares indicator dot */}
      {existing.length > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-background" />
      )}

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={handleClose} />
          <div className="absolute right-0 top-11 z-50 w-[340px] bg-card border border-border rounded-lg shadow-xl p-4">

            {/* Loading */}
            {mode === "loading" && (
              <div className="py-4 text-center text-xs text-muted-foreground">Checking existing shares…</div>
            )}

            {/* Existing shares */}
            {mode === "existing" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-sm text-foreground flex items-center gap-2">
                    <Link2 className="w-4 h-4 text-primary" />
                    Active Links
                  </h3>
                  <button onClick={handleClose} className="text-muted-foreground hover:text-foreground">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {existing.map(share => (
                    <div key={share.share_id} className="rounded-md border border-border p-2.5 space-y-2">
                      <button
                        onClick={() => handleExpand(share)}
                        className="w-full flex items-center justify-between text-xs hover:text-foreground transition-colors py-0.5"
                      >
                        <div className="flex items-center gap-1.5">
                          {share.has_password && <span title="Password protected — cannot be recovered"><Lock className="w-3 h-3 text-orange-400" /></span>}
                          <span className="text-muted-foreground">
                            {share.access_count} view{share.access_count !== 1 ? "s" : ""}
                          </span>
                          <span className="text-muted-foreground">·</span>
                          <span className="text-muted-foreground">
                            expires {new Date(share.expires_at).toLocaleDateString()}
                          </span>
                        </div>
                        {expandedShare === share.share_id
                          ? <ChevronUp className="w-3 h-3 text-muted-foreground" />
                          : <ChevronDown className="w-3 h-3 text-muted-foreground" />
                        }
                      </button>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="text"
                          readOnly
                          value={`${window.location.origin}/shared/${share.share_id}`}
                          className="flex-1 h-7 px-2 rounded bg-background border border-border text-[11px] font-mono-deck text-foreground"
                        />
                        <button
                          onClick={() => handleCopy(`/shared/${share.share_id}`)}
                          className={cn(
                            "h-7 px-2 rounded text-[11px] flex items-center gap-1 transition-colors",
                            copied ? "bg-green-500/15 text-green-400" : "bg-secondary text-foreground hover:bg-secondary/80"
                          )}
                        >
                          <Copy className="w-3 h-3" />
                          {copied ? "Copied" : "Copy"}
                        </button>
                        <button
                          onClick={() => handleRevoke(share.share_id, share.access_count)}
                          className="h-7 w-7 rounded bg-red-500/10 hover:bg-red-500/20 flex items-center justify-center text-red-400 transition-colors"
                          title="Revoke this link"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>

                      {/* Expanded: edit + access log */}
                      {expandedShare === share.share_id && (
                        <div className="border-t border-border pt-2 space-y-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            placeholder="Title"
                            className="w-full h-7 px-2 rounded bg-background border border-border text-xs text-foreground"
                          />
                          <input
                            type="text"
                            value={editNotes}
                            onChange={e => setEditNotes(e.target.value)}
                            placeholder="Add a note (e.g. For Q2 board review)"
                            className="w-full h-7 px-2 rounded bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground"
                          />
                          <button
                            onClick={() => handleSaveEdit(share.share_id)}
                            disabled={saving || saved}
                            className={cn(
                              "h-7 px-3 rounded text-[11px] transition-colors disabled:opacity-70",
                              saved ? "bg-green-500/15 text-green-400" : "bg-primary text-primary-foreground hover:bg-primary/90"
                            )}
                          >
                            {saving ? "Saving…" : saved ? "Saved ✓" : "Save"}
                          </button>

                          {/* Access log */}
                          {accessLog.length > 0 && (
                            <div className="space-y-1 pt-1">
                              <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Recent access</p>
                              {accessLog.slice(0, 5).map((entry, i) => (
                                <div key={i} className="flex items-center justify-between text-[10px]">
                                  <span className={entry.success ? "text-green-400" : "text-red-400"}>
                                    {entry.success ? "✓" : "✗"} {entry.ip_address || "unknown"}
                                  </span>
                                  <span className="text-muted-foreground">
                                    {new Date(entry.accessed_at).toLocaleString()}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                          {accessLog.length === 0 && (
                            <p className="text-[10px] text-muted-foreground">No access yet</p>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => setMode("create")}
                  className="w-full h-8 rounded-md bg-secondary text-xs text-muted-foreground hover:text-foreground flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Plus className="w-3 h-3" /> Create new link
                </button>
              </div>
            )}

            {/* Create new share */}
            {mode === "create" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-sm text-foreground flex items-center gap-2">
                    <Link2 className="w-4 h-4 text-primary" />
                    Share Link
                  </h3>
                  <button onClick={handleClose} className="text-muted-foreground hover:text-foreground">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {existing.length > 0 && (
                  <button
                    onClick={() => setMode("existing")}
                    className="w-full text-[11px] text-primary hover:underline text-left"
                  >
                    ← Back to {existing.length} existing link{existing.length !== 1 ? "s" : ""}
                  </button>
                )}

                <p className="text-xs text-muted-foreground font-body">
                  Generate a shareable link to this dashboard. Anyone with the link can view it without logging in.
                </p>

                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={usePassword}
                    onChange={(e) => setUsePassword(e.target.checked)}
                    className="rounded"
                  />
                  <Lock className="w-3 h-3 text-muted-foreground" />
                  <span className="text-muted-foreground">Password protect</span>
                </label>

                {usePassword && (
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password..."
                    className="w-full h-8 px-3 rounded-md bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                )}

                <div className="flex items-center gap-2">
                  <Clock className="w-3 h-3 text-muted-foreground" />
                  <select
                    value={expireHours}
                    onChange={(e) => setExpireHours(Number(e.target.value))}
                    className="h-8 px-2 rounded-md bg-background border border-border text-xs text-foreground flex-1"
                  >
                    <option value={24}>Expires in 1 day</option>
                    <option value={168}>Expires in 7 days</option>
                    <option value={720}>Expires in 30 days</option>
                    <option value={8760}>Expires in 1 year</option>
                  </select>
                </div>

                <button
                  onClick={handleCreate}
                  disabled={creating || (usePassword && !password)}
                  className="w-full h-9 rounded-md bg-primary text-primary-foreground text-xs font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Generate Link"}
                </button>
              </div>
            )}

            {/* Result */}
            {mode === "result" && result && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-sm text-foreground flex items-center gap-2">
                    <Check className="w-4 h-4 text-green-400" />
                    Link Created
                  </h3>
                  <button onClick={handleClose} className="text-muted-foreground hover:text-foreground">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}${result.url}`}
                    className="flex-1 h-8 px-2 rounded-md bg-background border border-border text-xs font-mono-deck text-foreground"
                  />
                  <button
                    onClick={() => handleCopy(result.url)}
                    className={cn(
                      "h-8 px-3 rounded-md text-xs flex items-center gap-1 transition-colors",
                      copied ? "bg-green-500/15 text-green-400" : "bg-secondary text-foreground hover:bg-secondary/80"
                    )}
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>

                {result.has_password && (
                  <p className="text-[10px] text-orange-400 flex items-center gap-1">
                    <Lock className="w-2.5 h-2.5" />
                    Password required to access
                  </p>
                )}

                <p className="text-[10px] text-muted-foreground">
                  Anyone with this link can view the dashboard without logging in.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
