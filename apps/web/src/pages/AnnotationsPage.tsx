import { apiFetch } from "@/lib/api";
import { useState, useEffect, useCallback } from "react";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";
import {
  MessageSquareText,
  Plus,
  Pin,
  Calendar,
  Tag,
  X,
  AlertTriangle,
  Info,
  AlertCircle,
  Trash2,
  Archive,
  Database,
  Plug,
  Globe,
  RotateCcw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  listAnnotations,
  createAnnotation,
  updateAnnotation,
  deleteAnnotation,
  type Annotation,
  type AnnotationCreate,
} from "@/lib/annotations";

// ── Constants ────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: "note", label: "Note", icon: MessageSquareText },
  { value: "incident", label: "Incident", icon: AlertTriangle },
  { value: "deployment", label: "Deployment", icon: Globe },
  { value: "update", label: "Update", icon: Info },
  { value: "campaign", label: "Campaign", icon: Tag },
  { value: "terms_change", label: "Terms Change", icon: AlertCircle },
];

const SEVERITIES = [
  { value: "info", label: "Info", color: "text-blue-400 bg-blue-500/10" },
  { value: "warning", label: "Warning", color: "text-orange-400 bg-orange-500/10" },
  { value: "critical", label: "Critical", color: "text-red-400 bg-red-500/10" },
];

// PLUGINS loaded dynamically from API — see useEffect in CreateAnnotationForm

// ── Create Form ──────────────────────────────────────────────────────

function CreateAnnotationForm({
  onCreated,
  onCancel,
}: {
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<AnnotationCreate>({
    title: "",
    description: "",
    category: "note",
    severity: "info",
    date_start: new Date().toISOString().slice(0, 10),
    plugin_id: "",
    dataset: "",
    tags: [],
    pinned: false,
  });
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [installedPlugins, setInstalledPlugins] = useState<{ id: string; label: string }[]>([]);
  const [pluginDatasets, setPluginDatasets] = useState<string[]>([]);

  useEffect(() => {
    apiFetch("/api/plugins")
      .then(r => r.json())
      .then(d => {
        const plugins = (d.plugins || []).map((p: { id: string; display_name?: string }) => ({
          id: p.id,
          label: p.display_name || p.id,
        }));
        setInstalledPlugins(plugins);
      })
      .catch((err) => console.error("AnnotationsPage: failed to load installed plugins (form)", err));
  }, []);

  useEffect(() => {
    if (!form.plugin_id) { setPluginDatasets([]); return; }
    fetch(`/api/plugins/${form.plugin_id}`)
      .then(r => r.json())
      .then(d => {
        const datasets = (d.datasets || []).map((ds: { name: string }) => ds.name);
        setPluginDatasets(datasets);
        if (datasets.length > 0) setForm(f => ({ ...f, dataset: datasets[0] }));
        else setForm(f => ({ ...f, dataset: "" }));
      })
      .catch(() => setPluginDatasets([]));
  }, [form.plugin_id]);

  const handleSubmit = async () => {
    if (!form.title || !form.date_start) return;
    setSaving(true);
    // Flush any pending tag that hasn't been added via Enter yet
    const finalTags = tagInput.trim()
      ? [...(form.tags || []), ...(form.tags?.includes(tagInput.trim()) ? [] : [tagInput.trim()])]
      : form.tags || [];
    try {
      await createAnnotation({
        ...form,
        tags: finalTags,
        plugin_id: form.plugin_id || undefined,
        dataset: form.dataset || undefined,
        date_end: form.date_end || undefined,
      });
      onCreated();
    } catch {
      // error handled in UI
    } finally {
      setSaving(false);
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !form.tags?.includes(tagInput.trim())) {
      setForm({ ...form, tags: [...(form.tags || []), tagInput.trim()] });
      setTagInput("");
    }
  };

  return (
    <div className="bg-card rounded-lg border border-border p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm text-foreground">New Annotation</h3>
        <button onClick={onCancel} className="text-muted-foreground hover:text-foreground">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Title */}
      <input
        type="text"
        value={form.title}
        onChange={(e) => setForm({ ...form, title: e.target.value })}
        placeholder="What happened?"
        className="w-full h-10 px-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
      />

      {/* Description */}
      <textarea
        value={form.description || ""}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
        placeholder="Add details (optional)..."
        rows={3}
        className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body resize-none"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Category */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Category</label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        {/* Severity */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Severity</label>
          <select
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Date start */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Date</label>
          <input
            type="date"
            value={form.date_start}
            onChange={(e) => setForm({ ...form, date_start: e.target.value })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          />
        </div>

        {/* Date end (optional) */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">End date (range)</label>
          <input
            type="date"
            value={form.date_end || ""}
            onChange={(e) => setForm({ ...form, date_end: e.target.value || undefined })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Plugin scope */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Plugin scope</label>
          <select
            value={form.plugin_id || ""}
            onChange={(e) => setForm({ ...form, plugin_id: e.target.value })}
            className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground"
          >
            <option value="">Global (all plugins)</option>
            {installedPlugins.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>

        {/* Dataset */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Dataset (optional)</label>
          {pluginDatasets.length > 0 ? (
            <select
              value={form.dataset || ""}
              onChange={(e) => setForm({ ...form, dataset: e.target.value })}
              className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground font-mono-deck"
            >
              <option value="">— none —</option>
              {pluginDatasets.map(ds => (
                <option key={ds} value={ds}>{ds}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={form.dataset || ""}
              onChange={(e) => setForm({ ...form, dataset: e.target.value })}
              placeholder={form.plugin_id ? "No datasets declared" : "Select a plugin first"}
              disabled={!!form.plugin_id && pluginDatasets.length === 0}
              className="w-full h-9 px-2 rounded-md bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground font-mono-deck disabled:opacity-50"
            />
          )}
        </div>
      </div>

      {/* Tags */}
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">Tags</label>
        <div className="flex items-center gap-2 flex-wrap">
          {(form.tags || []).map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary flex items-center gap-1"
            >
              {tag}
              <button onClick={() => setForm({ ...form, tags: form.tags?.filter((t) => t !== tag) })}>
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          ))}
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
              placeholder="Add tag..."
              className="h-7 px-2 rounded bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground w-[100px]"
            />
            {tagInput.trim() && (
              <button
                onClick={addTag}
                className="h-7 px-2 rounded bg-secondary text-xs text-muted-foreground hover:text-foreground border border-border"
              >
                +
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Pin + Submit */}
      <div className="flex items-center justify-between pt-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={form.pinned}
            onChange={(e) => setForm({ ...form, pinned: e.target.checked })}
            className="rounded"
          />
          <Pin className="w-3 h-3" /> Pin to dashboards
        </label>
        <div className="flex items-center gap-2">
          <button onClick={onCancel} className="h-9 px-4 rounded-md text-sm text-muted-foreground hover:text-foreground transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.title || saving}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Create Annotation"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Annotation Card ──────────────────────────────────────────────────

function AnnotationCard({
  annotation,
  onUpdate,
  onDelete,
}: {
  annotation: Annotation;
  onUpdate: () => void;
  onDelete: () => void;
}) {
  const cat = CATEGORIES.find((c) => c.value === annotation.category);
  const sev = SEVERITIES.find((s) => s.value === annotation.severity);
  const CatIcon = cat?.icon || MessageSquareText;

  const handlePin = async () => {
    await updateAnnotation(annotation.id, { pinned: !annotation.pinned });
    onUpdate();
  };

  const handleArchive = async () => {
    await updateAnnotation(annotation.id, { archived: true });
    onUpdate();
  };

  const handleRestore = async () => {
    await updateAnnotation(annotation.id, { archived: false });
    onUpdate();
  };

  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleDelete = async () => {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    // Permanent delete for archived rows; soft-delete (archive) for live rows
    await deleteAnnotation(annotation.id, annotation.archived);
    onDelete();
  };

  return (
    <div
      className={cn(
        "bg-card rounded-lg border p-4",
        annotation.archived ? "border-border opacity-60" : annotation.pinned ? "border-primary/30" : "border-border"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn("h-8 w-8 rounded-md flex items-center justify-center shrink-0 mt-0.5", annotation.archived ? "bg-secondary text-muted-foreground" : sev?.color)}>
          <CatIcon className="w-4 h-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className={cn("font-display text-sm", annotation.archived ? "text-muted-foreground line-through" : "text-foreground")}>{annotation.title}</h3>
            {annotation.archived && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground flex items-center gap-1">
                <Archive className="w-2.5 h-2.5" /> Archived
              </span>
            )}
            {!annotation.archived && annotation.pinned && <Pin className="w-3 h-3 text-primary" />}
            {!annotation.archived && (
              <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full", sev?.color)}>
                {annotation.severity}
              </span>
            )}
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">
              {cat?.label}
            </span>
          </div>

          {annotation.description && (
            <p className="text-xs text-muted-foreground font-body mt-1 line-clamp-2">
              {annotation.description}
            </p>
          )}

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {/* Date */}
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {annotation.date_start}
              {annotation.date_end && annotation.date_end !== annotation.date_start && (
                <> → {annotation.date_end}</>
              )}
            </span>

            {/* Scope */}
            {annotation.plugin_id && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Plug className="w-3 h-3" />
                {annotation.plugin_id}
              </span>
            )}
            {annotation.dataset && (
              <span className="text-xs text-muted-foreground flex items-center gap-1 font-mono-deck">
                <Database className="w-3 h-3" />
                {annotation.dataset}
              </span>
            )}
            {!annotation.plugin_id && !annotation.dataset && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Globe className="w-3 h-3" /> Global
              </span>
            )}

            {/* Tags */}
            {(annotation.tags || []).map((tag) => (
              <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-mono-deck">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {annotation.archived ? (
            <>
              <button
                onClick={handleRestore}
                className="h-7 px-2 rounded flex items-center gap-1 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                title="Restore annotation"
              >
                <RotateCcw className="w-3 h-3" /> Restore
              </button>
              <button
                onClick={handleDelete}
                className={cn(
                  "h-7 px-2 rounded flex items-center gap-1 text-xs transition-colors",
                  confirmDelete
                    ? "bg-red-500/15 text-red-400 hover:bg-red-500/25"
                    : "text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
                )}
                title={confirmDelete ? "Click again to permanently delete" : "Delete permanently"}
                onBlur={() => setConfirmDelete(false)}
              >
                <Trash2 className="w-3 h-3" />
                {confirmDelete ? "Confirm delete" : "Delete"}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handlePin}
                className={cn(
                  "h-7 w-7 rounded flex items-center justify-center transition-colors",
                  annotation.pinned ? "text-primary" : "text-muted-foreground hover:text-foreground"
                )}
                title={annotation.pinned ? "Unpin" : "Pin to dashboards"}
              >
                <Pin className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleArchive}
                className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                title="Archive"
              >
                <Archive className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleDelete}
                className="h-7 w-7 rounded flex items-center justify-center text-muted-foreground hover:text-red-400 transition-colors"
                title="Delete"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────

export default function AnnotationsPage() {
  useMarkBootReadyOnMount();
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filterCategory, setFilterCategory] = useState("");
  const [filterPlugin, setFilterPlugin] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [installedPlugins, setInstalledPlugins] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    apiFetch("/api/plugins")
      .then(r => r.json())
      .then(d => {
        setInstalledPlugins(
          (d.plugins || []).map((p: { id: string; display_name?: string }) => ({
            value: p.id,
            label: p.display_name || p.id,
          }))
        );
      })
      .catch((err) => console.error("AnnotationsPage: failed to load installed plugins (filter)", err));
  }, []);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAnnotations({
        category: filterCategory || undefined,
        plugin_id: filterPlugin || undefined,
        include_archived: showArchived || undefined,
      });
      setAnnotations(data);
    } catch {
      setAnnotations([]);
    } finally {
      setLoading(false);
    }
  }, [filterCategory, filterPlugin, showArchived]);

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="max-w-[1000px] space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground font-body">
            Add context to your data — mark events, incidents, and changes that affect your metrics.
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Add Annotation
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <CreateAnnotationForm
          onCreated={() => { setShowForm(false); fetch(); }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="h-8 px-2 rounded-md bg-secondary border border-border text-xs text-foreground"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <select
          value={filterPlugin}
          onChange={(e) => setFilterPlugin(e.target.value)}
          className="h-8 px-2 rounded-md bg-secondary border border-border text-xs text-foreground"
        >
          <option value="">All plugins</option>
          {installedPlugins.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        <button
          onClick={() => setShowArchived(v => !v)}
          className={cn(
            "h-8 px-3 rounded-md text-xs font-body flex items-center gap-1.5 transition-colors",
            showArchived
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          )}
          title={showArchived ? "Hide archived annotations" : "Show archived annotations"}
        >
          <Archive className="w-3 h-3" />
          {showArchived ? "Hide archived" : "Show archived"}
        </button>
        {annotations.length > 0 && (
          <span className="text-xs text-muted-foreground ml-2">
            {annotations.filter(a => !a.archived).length} annotation{annotations.filter(a => !a.archived).length !== 1 ? "s" : ""}
            {showArchived && annotations.some(a => a.archived) && (
              <span className="ml-1 text-muted-foreground/60">
                · {annotations.filter(a => a.archived).length} archived
              </span>
            )}
          </span>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse">
              <div className="h-4 w-48 bg-secondary rounded mb-2" />
              <div className="h-3 w-32 bg-secondary rounded" />
            </div>
          ))}
        </div>
      ) : annotations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mb-4">
            <MessageSquareText className="w-7 h-7 text-muted-foreground" />
          </div>
          <h3 className="font-display text-lg text-foreground mb-2">No annotations yet</h3>
          <p className="text-sm text-muted-foreground font-body max-w-md mb-6">
            Add your first annotation — mark an algorithm update, campaign launch, or anything
            that gives context to your data.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Create Annotation
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {annotations.map((a) => (
            <AnnotationCard
              key={a.id}
              annotation={a}
              onUpdate={fetch}
              onDelete={fetch}
            />
          ))}
        </div>
      )}
    </div>
  );
}
