import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { apiFetch } from "@/lib/api";

const API_BASE = "/api";

/**
 * Tracks page views and provides a function to log custom events.
 * Automatically fires a page_view event on every route change.
 */
export function useActivityTracking() {
  const location = useLocation();
  const lastPath = useRef("");

  // Track page views on route change
  useEffect(() => {
    if (location.pathname === lastPath.current) return;
    lastPath.current = location.pathname;

    const pluginMatch = location.pathname.match(/^\/plugin\/([^/]+)/);
    const pluginId = pluginMatch?.[1] || undefined;

    apiFetch(`${API_BASE}/activity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "page_view",
        category: "navigation",
        page_path: location.pathname,
        plugin_id: pluginId,
      }),
    }).catch(() => {});
  }, [location.pathname]);
}

/**
 * Log a custom activity event.
 */
export function logActivity(
  action: string,
  detail: Record<string, unknown> = {},
  extra?: {
    category?: string;
    page_path?: string;
    plugin_id?: string;
    duration_ms?: number;
  }
) {
  apiFetch(`${API_BASE}/activity`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      category: extra?.category || "general",
      page_path: extra?.page_path || window.location.pathname,
      plugin_id: extra?.plugin_id,
      detail,
      duration_ms: extra?.duration_ms,
    }),
  }).catch(() => {});
}
