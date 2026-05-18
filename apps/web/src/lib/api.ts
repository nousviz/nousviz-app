/**
 * NousViz API client
 *
 * All frontend data fetching goes through here.
 * In dev, Vite proxies /api to localhost:8000 (FastAPI).
 *
 * B246 (v0.9.10.5): types are imported from @nousviz/client (the
 * auto-generated SDK). The transport layer (apiFetch + step-up
 * handling) stays here — it has SPA-specific concerns (event bus
 * for the StepUpModal, retry-after-step-up semantics) that don't
 * belong in a generic generated client.
 */

import type {
  QueryResponse,
  PluginEntry,
  HealthResponse,
} from "@nousviz/client";

const API_BASE = "/api";
const TOKEN_KEY = "nousviz_auth_token";

/**
 * B236 (v0.9.10.0): step-up event bus.
 *
 * When apiFetch receives a 401 with `{detail: {error: 'stepup_required'}}`,
 * it dispatches a `nousviz:stepup-required` event with the original
 * request args attached. The globally-mounted StepUpModal listens for
 * this, prompts for re-auth, and on success retries the request via
 * `retryStepUpRequest()`.
 */

interface StepUpPendingRequest {
  input: RequestInfo | URL;
  init?: RequestInit;
  resolve: (res: Response) => void;
  reject: (err: unknown) => void;
}

let pendingRequest: StepUpPendingRequest | null = null;

export type StepUpEvent = CustomEvent<{ pending: boolean }>;

function dispatchStepUpEvent(pending: boolean) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("nousviz:stepup-required", { detail: { pending } }));
  }
}

/**
 * Called by StepUpModal after the user successfully re-authenticates.
 * Retries the pending request (now that the session has step_up_until set).
 */
export function retryStepUpRequest() {
  const pending = pendingRequest;
  pendingRequest = null;
  if (!pending) {
    dispatchStepUpEvent(false);
    return;
  }
  // Re-issue the request fresh — apiFetch will pick up the same token,
  // which now carries a valid step_up_until.
  apiFetch(pending.input, pending.init)
    .then(pending.resolve, pending.reject);
  dispatchStepUpEvent(false);
}

/**
 * Called by StepUpModal if the user cancels (or three failures occur).
 * The pending request resolves with the original 401 so the caller can
 * surface a generic "this requires step-up" error.
 */
export function cancelStepUpRequest() {
  if (pendingRequest) {
    // Synthesize a 401 response shaped like the original.
    const synthetic = new Response(
      JSON.stringify({ detail: { error: "stepup_cancelled", message: "Step-up cancelled by user." } }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    );
    pendingRequest.resolve(synthetic);
    pendingRequest = null;
  }
  dispatchStepUpEvent(false);
}

/**
 * Drop-in replacement for fetch() that automatically attaches the session
 * token to every /api request. Use this instead of raw fetch() for all
 * API calls so auth works when AUTH_REQUIRED=true.
 *
 * Also defaults to `cache: "no-store"` for every request. The API is fully
 * dynamic — nothing should be cached by the browser. Callers can opt back
 * into caching by passing `cache: "default"` explicitly.
 *
 * B236 (v0.9.10.0): when the response is 401 with `stepup_required`,
 * intercept the response and queue the request for retry after the user
 * confirms their password via the StepUpModal.
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem(TOKEN_KEY);
  const merged: RequestInit = {
    cache: "no-store",
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { "X-Session-Token": token } : {}),
    },
  };
  const res = await fetch(input, merged);

  // B236: detect stepup_required and queue retry.
  if (res.status === 401) {
    // Try to peek at the body to see if this is a stepup challenge.
    // Clone so the caller can still consume the body if we don't intercept.
    const cloned = res.clone();
    try {
      const data = await cloned.json();
      const detail = data?.detail;
      if (detail && typeof detail === "object" && detail.error === "stepup_required") {
        // Park the request and signal the modal.
        return new Promise<Response>((resolve, reject) => {
          pendingRequest = { input, init, resolve, reject };
          dispatchStepUpEvent(true);
        });
      }
    } catch {
      // Body wasn't JSON — fall through to normal 401 handling.
    }
  }

  // Session expired — clear stale token and redirect to login.
  // Skip for public endpoints that legitimately return 401 (share access, etc.)
  if (res.status === 401 && token && !window.location.pathname.startsWith("/shared/")) {
    localStorage.removeItem(TOKEN_KEY);
    const returnTo = encodeURIComponent(window.location.pathname);
    window.location.href = `/?return=${returnTo}`;
  }
  return res;
}

/**
 * B246: re-export the generated types under their previous local names so
 * existing call sites (`import { QueryResult } from "@/lib/api"`) keep
 * working. New code should import directly from `@nousviz/client`.
 */
export type QueryResult = QueryResponse;
export type PluginSummary = PluginEntry;
export type HealthStatus = HealthResponse;

// ── Query ────────────────────────────────────────────────────────────

export async function query(sql: string, database?: string, db_engine?: string): Promise<QueryResult> {
  const res = await apiFetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql, database, db_engine }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Query failed");
  }
  return res.json();
}

// ── Plugins ──────────────────────────────────────────────────────────

export async function listPlugins(): Promise<PluginSummary[]> {
  const res = await apiFetch(`${API_BASE}/plugins`);
  const data = await res.json();
  return data.plugins;
}

export async function getPlugin(pluginId: string): Promise<Record<string, unknown>> {
  const res = await apiFetch(`${API_BASE}/plugins/${pluginId}`);
  if (!res.ok) throw new Error(`Plugin '${pluginId}' not found`);
  return res.json();
}

export class NotFoundError extends Error {
  constructor(msg: string) { super(msg); this.name = "NotFoundError"; }
}

export async function getDashboardSpec(
  pluginId: string,
  dashboardName: string
): Promise<Record<string, unknown>> {
  const res = await apiFetch(`${API_BASE}/plugins/${pluginId}/dashboards/${dashboardName}`);
  if (res.status === 404) throw new NotFoundError(`Dashboard '${dashboardName}' not found`);
  if (!res.ok) throw new Error(`Failed to load dashboard spec (${res.status})`);
  return res.json();
}

// ── Health ────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthStatus> {
  const res = await apiFetch(`${API_BASE}/health`);
  return res.json();
}
