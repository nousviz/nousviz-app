import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import { Plus, LayoutDashboard, Trash2, Pencil, Clock, Layers, Shield, X } from "lucide-react";
import { AccessTab } from "@/components/access/AccessTab";

interface UserDashboard {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  widget_count: number;
  sources: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// v0.10.0.7.3 (Phase 14 / P14.1): exported cache key for cross-page invalidation.
export const DASHBOARDS_LIST_QUERY_KEY = ["dashboards", "list"] as const;

export default function DashboardManagerPage() {
  useMarkBootReadyOnMount();
  const queryClient = useQueryClient();
  const [deleteSlug, setDeleteSlug] = useState<string | null>(null);
  const [accessSlug, setAccessSlug] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data, isLoading } = useApiQuery<{ dashboards: UserDashboard[] }>(
    DASHBOARDS_LIST_QUERY_KEY,
    "/api/dashboards",
  );

  const dashboards: UserDashboard[] = data?.dashboards ?? [];
  const loading = isLoading;

  async function handleDelete(slug: string) {
    try {
      await apiFetch(`/api/dashboards/${slug}`, { method: "DELETE" });
      setDeleteSlug(null);
      queryClient.invalidateQueries({ queryKey: DASHBOARDS_LIST_QUERY_KEY });
    } catch (e) {
      console.error("Delete failed:", e);
    }
  }

  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-foreground">Dashboards</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create custom dashboard views from plugin data, fusions, and custom widgets.
          </p>
        </div>
        <Link
          to="/dashboards/new"
          className="h-9 px-4 rounded-md bg-primary text-sm text-white font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Dashboard
        </Link>
      </div>

      {/* Dashboard grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-5 animate-pulse">
              <div className="h-4 w-32 bg-secondary rounded mb-3" />
              <div className="h-3 w-48 bg-secondary rounded mb-4" />
              <div className="h-3 w-20 bg-secondary rounded" />
            </div>
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="py-20 text-center border border-dashed border-border rounded-lg">
          <LayoutDashboard className="w-10 h-10 text-muted-foreground/40 mx-auto mb-4" />
          <h2 className="font-display text-lg text-foreground mb-2">No dashboards yet</h2>
          <p className="text-sm text-muted-foreground mb-4 max-w-sm mx-auto">
            Create your first dashboard by composing widgets from plugin datasets, fusions, and custom components.
          </p>
          <Link
            to="/dashboards/new"
            className="inline-flex h-9 px-4 rounded-md bg-primary text-sm text-white font-body hover:bg-primary/90 transition-colors items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Dashboard
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map((d) => (
            <div
              key={d.slug}
              className="bg-card rounded-lg border border-border p-5 group hover:border-primary/30 transition-colors cursor-pointer relative"
              onClick={() => navigate(`/dashboards/${d.slug}`)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Layers className="w-4 h-4 text-primary" />
                  </div>
                  <h3 className="font-display text-sm text-foreground">{d.name}</h3>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => { e.stopPropagation(); navigate(`/dashboards/edit/${d.slug}`); }}
                    className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                    title="Edit"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setAccessSlug(d.slug); }}
                    className="p-1.5 rounded hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                    title="Access"
                  >
                    <Shield className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteSlug(d.slug); }}
                    className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              {d.description && (
                <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{d.description}</p>
              )}
              <div className="flex items-center gap-3 text-[10px] font-mono-deck text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Layers className="w-3 h-3" />
                  {d.widget_count} widget{d.widget_count !== 1 ? "s" : ""}
                </span>
                {d.sources.length > 0 && (
                  <span>{d.sources.length} source{d.sources.length !== 1 ? "s" : ""}</span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(d.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Access modal (B248 v0.9.10.7) */}
      {accessSlug && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setAccessSlug(null)}>
          <div className="bg-card border border-border rounded-lg p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-base text-foreground">
                Access — {dashboards.find((d) => d.slug === accessSlug)?.name}
              </h3>
              <button onClick={() => setAccessSlug(null)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <AccessTab
              resourceType="dashboard"
              resourceId={accessSlug}
              permissions={["dashboards.read", "dashboards.write"]}
            />
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {deleteSlug && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDeleteSlug(null)}>
          <div className="bg-card border border-border rounded-lg p-6 max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-base text-foreground mb-2">Delete dashboard?</h3>
            <p className="text-sm text-muted-foreground mb-4">
              This will permanently delete "{dashboards.find((d) => d.slug === deleteSlug)?.name}". This cannot be undone.
            </p>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={() => setDeleteSlug(null)}
                className="h-8 px-3 rounded-md bg-secondary text-xs text-foreground font-body hover:bg-secondary/80 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteSlug)}
                className="h-8 px-3 rounded-md bg-red-500 text-xs text-white font-body hover:bg-red-600 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
