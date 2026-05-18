import { apiFetch } from "@/lib/api";
const API_BASE = "/api";

export interface Alert {
  id: string;
  name: string;
  label: string;
  description: string | null;
  plugin_id: string;
  tier: string;
  dataset: string;
  metric: string;
  aggregation: string;
  condition_type: string;
  threshold: number | null;
  compare_to: string;
  check_period: string;
  scope: string;
  group_by: string | null;
  scope_filters: Record<string, string>;
  check_frequency: string;
  frequency_label: string;
  period_label: string;
  cooldown_hours: number;
  min_baseline: number;
  notify_channels: string[];
  enabled: boolean;
  is_template: boolean;
  created_at: string;
  updated_at: string;
  last_triggered: string | null;
  trigger_count: number;
}

export interface SparklineDay {
  date: string;
  count: number;
  score: "useful" | "neutral" | "useless" | null;
}

export interface AlertSparkline {
  alert_id: string;
  alert_label: string;
  check_frequency: string;
  frequency_label: string;
  check_period: string;
  period_label: string;
  cooldown_hours: number;
  days: SparklineDay[];
  total_triggers: number;
  semantic_summary: { useful: number; neutral: number; useless: number };
}

export interface AlertCreate {
  name: string;
  label: string;
  description?: string;
  plugin_id: string;
  tier?: string;
  dataset: string;
  metric: string;
  aggregation?: string;
  condition_type?: string;
  threshold?: number;
  compare_to?: string;
  scope?: string;
  group_by?: string;
  scope_filters?: Record<string, string>;
  check_frequency?: string;
  cooldown_hours?: number;
  min_baseline?: number;
  notify_channels?: string[];
  enabled?: boolean;
  is_template?: boolean;
}

export interface TestResult {
  alert_id: string;
  alert_name: string;
  condition: string;
  threshold: number;
  results: { group: string; current_value: number; baseline: number; change_pct: number }[];
  triggered: { group: string; current_value: number; baseline: number; change_pct: number }[];
  would_fire: boolean;
  sql: string;
  error?: string;
}

export async function listAlerts(pluginId?: string): Promise<Alert[]> {
  const qs = pluginId ? `?plugin_id=${pluginId}` : "";
  const res = await apiFetch(`${API_BASE}/alerts${qs}`);
  const data = await res.json();
  return data.alerts;
}

export async function createAlert(alert: AlertCreate): Promise<Alert> {
  const res = await apiFetch(`${API_BASE}/alerts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(alert),
  });
  if (!res.ok) throw new Error("Failed to create alert");
  return res.json();
}

export async function updateAlert(id: string, updates: Record<string, unknown>): Promise<Alert> {
  const res = await apiFetch(`${API_BASE}/alerts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update alert");
  return res.json();
}

export async function deleteAlert(id: string): Promise<void> {
  await apiFetch(`${API_BASE}/alerts/${id}`, { method: "DELETE" });
}

export async function testAlert(id: string): Promise<TestResult> {
  const res = await apiFetch(`${API_BASE}/alerts/${id}/test`, { method: "POST" });
  return res.json();
}

export async function getAlertSparkline(id: string, days = 30): Promise<AlertSparkline> {
  const res = await apiFetch(`${API_BASE}/alerts/${id}/sparkline?days=${days}`);
  if (!res.ok) throw new Error("Failed to fetch sparkline");
  return res.json();
}
