import { apiFetch } from "@/lib/api";
/**
 * Annotations API client
 */

const API_BASE = "/api";

export interface Annotation {
  id: string;
  title: string;
  description: string | null;
  source: string;
  category: string;
  severity: string;
  color: string | null;
  plugin_id: string | null;
  dataset: string | null;
  date_start: string;
  date_end: string | null;
  scope_filters: Record<string, string>;
  tags: string[];
  pinned: boolean;
  archived: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreate {
  title: string;
  description?: string;
  source?: string;
  category?: string;
  severity?: string;
  color?: string;
  plugin_id?: string;
  dataset?: string;
  date_start: string;
  date_end?: string;
  scope_filters?: Record<string, string>;
  tags?: string[];
  pinned?: boolean;
}

export async function listAnnotations(filters?: {
  plugin_id?: string;
  dataset?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
  include_archived?: boolean;
}): Promise<Annotation[]> {
  const params = new URLSearchParams();
  if (filters?.plugin_id) params.set("plugin_id", filters.plugin_id);
  if (filters?.dataset) params.set("dataset", filters.dataset);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.date_from) params.set("date_from", filters.date_from);
  if (filters?.date_to) params.set("date_to", filters.date_to);
  if (filters?.include_archived) params.set("include_archived", "true");
  const qs = params.toString();
  const res = await apiFetch(`${API_BASE}/annotations${qs ? `?${qs}` : ""}`);
  const data = await res.json();
  return data.annotations;
}

export async function createAnnotation(annotation: AnnotationCreate): Promise<Annotation> {
  const res = await apiFetch(`${API_BASE}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(annotation),
  });
  if (!res.ok) throw new Error("Failed to create annotation");
  return res.json();
}

export async function updateAnnotation(id: string, updates: Partial<AnnotationCreate> & { archived?: boolean }): Promise<Annotation> {
  const res = await apiFetch(`${API_BASE}/annotations/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update annotation");
  return res.json();
}

export async function deleteAnnotation(id: string, permanent = false): Promise<void> {
  const url = permanent
    ? `${API_BASE}/annotations/${id}?permanent=true`
    : `${API_BASE}/annotations/${id}`;
  const res = await apiFetch(url, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete annotation");
}
