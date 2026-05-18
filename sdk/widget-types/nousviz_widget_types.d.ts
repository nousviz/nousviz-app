/**
 * NousViz plugin widget — TypeScript declarations (v0.9.4.1).
 *
 * Plugin authors copy this file into their plugin repo (or
 * `///<reference path="..." />` it from a known path) to get types for
 * the host SDK and the CustomWidgetProps shape.
 *
 * Host SDK is exposed via `window.NousViz.widgets` — published at
 * runtime by NousViz core before any plugin widget mounts. Plugin
 * bundles do NOT have a build-time dependency on a NousViz npm package;
 * they read the global at runtime.
 *
 * Build pattern (recommended). Use --alias for `react` and
 * `react/jsx-runtime` so your widget imports the host's React at
 * runtime. Don't bundle React (the bundle-it advice from v0.9.4.5 was
 * wrong; it caused the dual-instance hooks bug B156). See sdk/README.md
 * → "Build" for full details.
 *
 *   esbuild widget/MyWidget.tsx \
 *     --bundle \
 *     --format=esm \
 *     --jsx=automatic \
 *     --target=es2020 \
 *     --alias:react=/api/widget-runtime/react.js \
 *     --alias:react/jsx-runtime=/api/widget-runtime/react-jsx-runtime.js \
 *     --external:/api/widget-runtime/react.js \
 *     --external:/api/widget-runtime/react-jsx-runtime.js \
 *     --outfile=widget/dist/MyWidget.js
 *
 * Both --alias AND --external are required. --alias rewrites "react" →
 * the URL, --external prevents esbuild from trying to resolve that URL
 * on disk (it has no on-disk file; the browser fetches it at runtime).
 *
 * Then in your widget:
 *
 *   /// <reference path="./nousviz_widget_types.d.ts" />
 *   import { useEffect, useState } from "react";
 *
 *   export default function MyWidget({ pluginId, config }: CustomWidgetProps) {
 *     const [data, setData] = useState<unknown>(null);
 *     useEffect(() => {
 *       window.NousViz.widgets
 *         .apiFetch(`/api/plugins/${pluginId}/some-endpoint`)
 *         .then(r => r.json())
 *         .then(setData);
 *     }, [pluginId]);
 *     return <div>{JSON.stringify(data)}</div>;
 *   }
 */

/**
 * Props passed to every plugin-shipped widget rendered via
 * `type: custom, component: <Name>` in dashboard YAML.
 */
declare interface CustomWidgetProps {
  /** Plugin slug (matches `name:` in plugin.yaml) */
  pluginId: string;
  /** Slug of the dashboard rendering this widget */
  dashboardName: string;
  /** Anything the dashboard YAML's `props:` block declared */
  config: Record<string, unknown>;
}

/**
 * Host SDK exposed via window.NousViz.widgets.
 *
 * Publish contract: NousViz core sets these on `window.NousViz.widgets`
 * before dynamically importing any plugin's widget bundle. Plugin code
 * can rely on them being defined at module evaluation time.
 *
 * Stability: NousViz follows semver on this surface starting v0.9.4.1.
 * Adding new helpers is non-breaking; removing or changing a signature
 * requires a major bump.
 */
declare interface NousVizWidgetsSDK {
  /**
   * Authenticated fetch wrapper. Adds the operator's session token
   * automatically. Use this instead of bare `fetch()` for any call to
   * NousViz API endpoints.
   *
   *   const r = await window.NousViz.widgets.apiFetch(
   *     `/api/plugins/${pluginId}/data`,
   *     { method: "POST", body: JSON.stringify({ filter: "active" }) }
   *   );
   *   const data = await r.json();
   */
  apiFetch: (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => Promise<Response>;

  /**
   * Format an ISO timestamp as a relative-time string ("2 hours ago",
   * "in 5 minutes"). Returns "—" for null/invalid input.
   */
  formatRelativeTime: (iso: string | null | undefined) => string;

  /**
   * Format an ISO timestamp as an absolute-time string suitable for
   * `title` attributes ("2026-04-25, 14:00:00 UTC").
   */
  formatAbsoluteTime: (iso: string | null | undefined) => string;

  /**
   * Format a number with thousands separators ("1,234,567").
   */
  formatNumber: (n: number) => string;

  /**
   * Format a byte count as a human-readable size ("1.4 MB").
   */
  formatBytes: (bytes: number) => string;

  /**
   * Tailwind class-name merger. Concatenates conditional class strings
   * and de-duplicates conflicting Tailwind utilities, e.g.:
   *
   *   cn("px-4", isLarge && "px-6")  // → "px-6" if isLarge, else "px-4"
   *
   * Wraps clsx + tailwind-merge under the hood. Plugin authors don't
   * need to depend on either.
   */
  cn: (...inputs: Array<string | number | boolean | null | undefined | Record<string, unknown> | unknown[]>) => string;
}

declare interface Window {
  NousViz: {
    widgets: NousVizWidgetsSDK;
  };
}
