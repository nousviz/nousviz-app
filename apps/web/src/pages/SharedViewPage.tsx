import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Lock, AlertTriangle, Clock, CheckCircle2 } from "lucide-react";
import DashboardRenderer from "@/widgets/DashboardRenderer";

interface ShareMeta {
  share_id: string;
  title: string;
  page_path: string;
  resource_type: string;
  has_password: boolean;
  expires_at: string | null;
}

interface ShareContent {
  page_path: string;
  title: string;
  filters: Record<string, unknown>;
}

export default function SharedViewPage() {
  const { shareId } = useParams<{ shareId: string }>();
  const [meta, setMeta] = useState<ShareMeta | null>(null);
  const [content, setContent] = useState<ShareContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Fetch metadata (no auth needed)
  useEffect(() => {
    if (!shareId) return;
    fetch(`/api/shares/${shareId}`)
      .then(r => {
        if (r.status === 410) throw new Error("expired");
        if (r.status === 404) throw new Error("not_found");
        if (!r.ok) throw new Error("error");
        return r.json();
      })
      .then(d => { setMeta(d); setLoading(false); })
      .catch(e => {
        if (e.message === "expired") setError("This share link has expired.");
        else if (e.message === "not_found") setError("Share link not found.");
        else setError("Failed to load share link.");
        setLoading(false);
      });
  }, [shareId]);

  // If no password required, access immediately
  useEffect(() => {
    if (meta && !meta.has_password && !content) {
      accessShare();
    }
  }, [meta]);

  async function accessShare(pw?: string) {
    if (!shareId) return;
    setSubmitting(true);
    setPwError(null);
    try {
      const res = await fetch(`/api/shares/${shareId}/access`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: pw || null }),
      });
      if (res.status === 401) {
        const data = await res.json();
        setPwError(data.detail || "Incorrect password");
        setSubmitting(false);
        return;
      }
      if (res.status === 410) {
        setError("This share link has expired.");
        setSubmitting(false);
        return;
      }
      if (!res.ok) throw new Error("access_failed");
      const data = await res.json();
      setContent(data);
      // Title already includes instance name since it's captured from document.title at share creation
      document.title = data.title || "Shared View";
    } catch {
      setError("Failed to access share link.");
    } finally {
      setSubmitting(false);
    }
  }

  // Loading
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-sm text-muted-foreground">Loading...</div>
      </div>
    );
  }

  // Error (expired, not found)
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="max-w-sm text-center space-y-4">
          <AlertTriangle className="w-10 h-10 text-yellow-400 mx-auto" />
          <p className="text-sm text-foreground">{error}</p>
          <a href="/" className="text-xs text-primary hover:underline">Go to NousViz</a>
        </div>
      </div>
    );
  }

  // Password prompt
  if (meta && meta.has_password && !content) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="max-w-sm w-full space-y-5">
          <div className="text-center">
            <Lock className="w-8 h-8 text-primary mx-auto mb-3" />
            <h1 className="font-display text-lg text-foreground">{meta.title}</h1>
            <p className="text-xs text-muted-foreground mt-1">This shared view is password protected.</p>
          </div>
          <div className="space-y-3">
            <input
              autoFocus
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && password && accessShare(password)}
              placeholder="Enter password"
              className="w-full h-10 px-3 rounded-md bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
            {pwError && <p className="text-xs text-red-400">{pwError}</p>}
            <button
              onClick={() => accessShare(password)}
              disabled={!password || submitting}
              className="w-full h-10 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {submitting ? "Verifying..." : "View"}
            </button>
          </div>
          {meta.expires_at && (
            <p className="text-center text-[10px] text-muted-foreground flex items-center justify-center gap-1">
              <Clock className="w-3 h-3" />
              Expires {new Date(meta.expires_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Content loaded — render the shared dashboard
  if (content) {
    // Extract plugin ID and dashboard name from page_path
    // e.g. /plugin/starter-plugin/analytics → pluginId=starter-plugin, dashboardName=analytics
    const pathParts = content.page_path.split("/").filter(Boolean);
    const pluginIdx = pathParts.indexOf("plugin");
    const pluginId = pluginIdx >= 0 ? pathParts[pluginIdx + 1] : null;
    const dashboardName = pluginIdx >= 0 ? pathParts[pluginIdx + 2] : null;

    return (
      <div className="min-h-screen bg-background">
        {/* Shared view header */}
        <div className="border-b border-border px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            <span className="font-display text-sm text-foreground">{content.title}</span>
            <span className="text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">Shared view</span>
          </div>
          {meta?.expires_at && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Expires {new Date(meta.expires_at).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Dashboard content */}
        <div className="p-6 max-w-[1400px] mx-auto">
          {pluginId && dashboardName ? (
            <DashboardRenderer pluginId={pluginId} dashboardName={dashboardName} />
          ) : (
            <div className="py-20 text-center text-sm text-muted-foreground">
              Unable to render this shared content.
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}
