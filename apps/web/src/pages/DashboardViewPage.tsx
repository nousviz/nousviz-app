import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import DashboardRenderer, { type DashboardSpec } from "@/widgets/DashboardRenderer";
import { ArrowLeft, Pencil } from "lucide-react";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface UserDashboard {
  name: string;
  slug: string;
  description: string | null;
  widgets: DashboardSpec["widgets"];
  layout: Record<string, unknown>;
}

export default function DashboardViewPage() {
  useMarkBootReadyOnMount();
  const { slug } = useParams();
  const [dashboard, setDashboard] = useState<UserDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    apiFetch(`/api/dashboards/${slug}`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then(setDashboard)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="max-w-[1400px] space-y-4">
        <div className="h-8 w-48 bg-secondary rounded animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse">
              <div className="h-3 w-20 bg-secondary rounded mb-3" />
              <div className="h-7 w-24 bg-secondary rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="text-center py-20">
        <h2 className="font-display text-xl text-foreground mb-2">Dashboard not found</h2>
        <p className="text-sm text-muted-foreground mb-4">{error || "No dashboard at this URL."}</p>
        <Link to="/dashboards" className="text-sm text-primary hover:text-primary/80">
          Back to Dashboards
        </Link>
      </div>
    );
  }

  // Build a DashboardSpec from the saved dashboard and pass it to DashboardRenderer
  const spec: DashboardSpec = {
    name: dashboard.slug,
    label: dashboard.name,
    description: dashboard.description || "",
    db_engine: (dashboard.layout as { db_engine?: string })?.db_engine,
    widgets: dashboard.widgets,
    panels: [],
    filters: [],
  };

  return (
    <div className="max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboards"
            className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="font-display text-lg text-foreground">{dashboard.name}</h1>
            {dashboard.description && (
              <p className="text-xs text-muted-foreground mt-0.5">{dashboard.description}</p>
            )}
          </div>
        </div>
        <Link
          to={`/dashboards/edit/${slug}`}
          className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground font-body hover:bg-secondary/80 transition-colors flex items-center gap-1.5"
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit
        </Link>
      </div>

      {/* Reuse DashboardRenderer with pre-loaded spec */}
      <DashboardRenderer pluginId="" dashboardName="" preloadedSpec={spec} />
    </div>
  );
}
