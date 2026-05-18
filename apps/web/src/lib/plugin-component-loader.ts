/**
 * Plugin frontend component loader (B151 / v0.9.4).
 *
 * Walks installed plugins via /api/plugins, finds those with
 * `frontend.components` declared AND `frontend.trusted = true`, and
 * dynamically imports each component bundle. Imported defaults are
 * registered into the plugin-components.ts runtime registry so
 * DashboardRenderer can resolve `type: custom, component: "Foo"` against
 * them just like a built-in.
 *
 * Failures are isolated per-component: a broken bundle for plugin A
 * doesn't prevent plugin B's components from loading. Each failure logs
 * to the browser console with enough context to debug.
 *
 * Trust model:
 *   - Plugin's bundled JS runs with FULL host privileges (same session
 *     token, same DOM, same fetch). This is intentional for self-hosted
 *     pre-1.0 deployments. Operators consent explicitly via the install
 *     flow before the runtime registration happens.
 *   - Untrusted plugins (no `_trust_frontend = true`) are filtered out
 *     by the BACKEND before we ever see their components in the response,
 *     and the widget-serve endpoint refuses to serve their .js files.
 *     This loader is a second line of defense, not the only one.
 */

import React from "react";
import * as ReactJSXRuntime from "react/jsx-runtime";
import type { ComponentType } from "react";
import { apiFetch } from "@/lib/api";
import {
  formatRelativeTime,
  formatAbsoluteTime,
  formatNumber,
  formatBytes,
  cn,
} from "@/lib/utils";
import {
  registerPluginComponent,
  notifyPluginLoaderCompleted,
  type CustomWidgetProps,
} from "@/widgets/plugin-components";

/**
 * B151.1 (v0.9.4.1): expose a stable host SDK to plugin widgets via
 * `window.NousViz.widgets`. Plugin authors import nothing from us at
 * build time (their bundle has zero `@nousviz/*` deps), so we publish
 * the surface as a global at runtime.
 *
 * The shape is pinned in `nousviz_widget_types.d.ts` at the repo root —
 * plugin authors `///<reference />` it for typing, and the host's
 * implementation here must match.
 */
function publishHostSDK(): void {
  const w = window as unknown as {
    NousViz?: {
      widgets?: Record<string, unknown>;
      React?: typeof React;
      ReactJSXRuntime?: typeof ReactJSXRuntime;
    };
  };
  if (!w.NousViz) w.NousViz = {};
  if (!w.NousViz.widgets) {
    w.NousViz.widgets = {
      // API
      apiFetch,
      // Formatters (host's utils, exposed verbatim)
      formatRelativeTime,
      formatAbsoluteTime,
      formatNumber,
      formatBytes,
      // Tailwind class merge utility (most plugin widgets want this)
      cn,
    };
  }
  // B156 (v0.9.4.7): publish the host's React copy so the React shim at
  // /api/widget-runtime/react.js can re-export it. Plugin widgets built
  // with `--alias:react=/api/widget-runtime/react.js` then resolve their
  // `import { useState } from "react"` to the SAME React the host uses,
  // so hooks share the singleton ReactCurrentDispatcher and the
  // dual-instance bug (Cannot read properties of null) goes away.
  if (!w.NousViz.React) {
    w.NousViz.React = React;
  }
  if (!w.NousViz.ReactJSXRuntime) {
    w.NousViz.ReactJSXRuntime = ReactJSXRuntime;
  }
}

interface FrontendComponentDecl {
  name: string;
  path: string;
  filename?: string;
  exists_on_disk?: boolean;
}

interface PluginListEntry {
  id: string;
  name?: string;
  display_name?: string;
  frontend?: {
    components: FrontendComponentDecl[];
    trusted: boolean;
    needs_consent?: boolean;
  };
}

interface PluginListResponse {
  plugins: PluginListEntry[];
}

/**
 * Load and register every trusted plugin's frontend components.
 * Idempotent — calling twice re-registers the same components, no harm.
 *
 * Call once at app boot, before the router renders, so DashboardRenderer
 * can resolve plugin-shipped components on first paint.
 */
export async function loadPluginFrontendComponents(): Promise<void> {
  // B151.1: publish host SDK BEFORE any plugin widget executes. Plugin
  // bundles read `window.NousViz.widgets.apiFetch(...)` at first render —
  // it has to exist when their module evaluates.
  publishHostSDK();

  let plugins: PluginListEntry[] = [];
  try {
    const res = await apiFetch("/api/plugins");
    if (!res.ok) {
      // Not authenticated yet, or API down — silently skip; we'll
      // re-attempt on next page load. Don't block the host app.
      // v0.10.0.5.1: still notify completion so the dashboard renderer
      // can transition from "Loading widget…" placeholder to
      // "Unknown component" error if a widget is missing.
      notifyPluginLoaderCompleted();
      return;
    }
    const data = (await res.json()) as PluginListResponse;
    plugins = Array.isArray(data?.plugins) ? data.plugins : [];
  } catch {
    notifyPluginLoaderCompleted();
    return;
  }

  // Fan out: each plugin's components load in parallel; failures are
  // isolated to that one component.
  const tasks: Promise<void>[] = [];
  for (const plugin of plugins) {
    const fe = plugin.frontend;
    if (!fe || !fe.trusted || !fe.components?.length) continue;
    for (const comp of fe.components) {
      if (!comp.name || !comp.path) continue;
      // Backend's exists_on_disk is the truth-source for whether the
      // bundle is actually there; skip if not.
      if (comp.exists_on_disk === false) {
        // eslint-disable-next-line no-console
        console.warn(
          `[plugin-component-loader] ${plugin.id}/${comp.name}: bundle missing on disk (${comp.path})`,
        );
        continue;
      }
      tasks.push(registerOne(plugin.id, comp));
    }
  }

  await Promise.allSettled(tasks);
  // v0.10.0.5.1: every trusted plugin's components are now registered.
  // Signal the dashboard renderer it can stop showing "Loading widget…"
  // and start surfacing real "Unknown component" errors for misses.
  notifyPluginLoaderCompleted();
}

/**
 * B154 (v0.9.4.6): build a placeholder React component that renders
 * an inline error card instead of crashing the host. Returned from
 * the lazy() loader's resolved value — never throws to the suspense
 * boundary, which would propagate up to the route-level ErrorBoundary
 * and break the whole page.
 */
function makeBrokenBundlePlaceholder(
  pluginId: string,
  componentName: string,
  reason: string,
  remediation: string,
): { default: ComponentType<CustomWidgetProps> } {
  const Placeholder = () =>
    React.createElement(
      "div",
      {
        className:
          "bg-card rounded-lg border border-amber-500/30 p-4 text-xs space-y-1",
      },
      React.createElement(
        "div",
        { className: "text-amber-400 font-medium" },
        `Plugin widget failed to load: ${pluginId}/${componentName}`,
      ),
      React.createElement(
        "div",
        { className: "text-muted-foreground" },
        reason,
      ),
      React.createElement(
        "div",
        { className: "text-muted-foreground text-[11px]" },
        remediation,
      ),
    );
  Placeholder.displayName = `BrokenPluginWidget(${pluginId}/${componentName})`;
  return { default: Placeholder as ComponentType<CustomWidgetProps> };
}

async function registerOne(
  pluginId: string,
  comp: FrontendComponentDecl,
): Promise<void> {
  // The widget-serve endpoint validates trust + path; the URL itself is
  // safe to construct (filename is taken from the manifest, validated by
  // the backend at install).
  const filename = comp.filename ?? comp.path.split("/").pop() ?? "";
  const url = `/api/plugins/${pluginId}/widget/${filename}`;

  try {
    registerPluginComponent(comp.name, async () => {
      // The /* @vite-ignore */ comment tells Vite not to try to resolve
      // this URL at build time — it's a runtime URL served by the API.
      //
      // B154: NEVER throw from this loader. React's lazy() turns thrown
      // errors into rejected promises that the nearest Suspense/Error
      // boundary catches — and the route-level boundary takes out the
      // whole page. Instead, resolve with a placeholder component that
      // renders an inline error message, isolating the failure to this
      // one widget's slot.
      let mod: { default: ComponentType<CustomWidgetProps> };
      try {
        mod = (await import(/* @vite-ignore */ url)) as {
          default: ComponentType<CustomWidgetProps>;
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        // B153/B156: bare-specifier error means the plugin bundle has an
        // unresolved bare import (most commonly "react" / "react/jsx-runtime").
        // The right fix changed twice: v0.9.4.5 said "bundle React in"
        // (broke hooks via dual-instance, B156); v0.9.4.7 ships a
        // host-served React shim and the canonical fix is `--alias:react=...`
        // pointing at /api/widget-runtime/react.js.
        if (/Failed to resolve module specifier|module specifier/i.test(message)) {
          // Try to extract the actual unresolved specifier so the message
          // names the real culprit (B155 follow-up to v0.9.4.6's pattern-only
          // detector). Pattern from V8/Chromium: `Failed to resolve module
          // specifier "X"`. Other engines vary; fall back to a generic message.
          const m = /module specifier ['"]([^'"]+)['"]/.exec(message);
          const unresolved = m ? m[1] : "unknown";
          const isReact = unresolved === "react" || unresolved === "react-dom" || unresolved.startsWith("react/");
          // eslint-disable-next-line no-console
          console.error(
            `[plugin-component-loader] ${pluginId}/${comp.name}: bundle ` +
            `references a bare module specifier "${unresolved}" the host can't resolve.\n` +
            (isReact
              ? `Fix: rebuild with esbuild --alias:react=/api/widget-runtime/react.js ` +
                `--alias:react/jsx-runtime=/api/widget-runtime/react-jsx-runtime.js. ` +
                `Do NOT bundle React (the bundle-it advice from v0.9.4.5 was wrong; ` +
                `it caused the dual-instance hooks bug B156).\n`
              : `Fix: bundle "${unresolved}" into your widget (drop --external:${unresolved} ` +
                `from your build), or — if it's a host-provided runtime — file an issue.\n`) +
            `Original error: ${message}`,
          );
          return makeBrokenBundlePlaceholder(
            pluginId,
            comp.name,
            `Plugin bundle has an unresolved bare import: "${unresolved}".`,
            isReact
              ? "Plugin author: rebuild with --alias:react=/api/widget-runtime/react.js (see sdk/README.md)."
              : `Plugin author: bundle "${unresolved}" into the widget, or contact the host for a runtime alias.`,
          );
        }
        // eslint-disable-next-line no-console
        console.error(
          `[plugin-component-loader] ${pluginId}/${comp.name}: import failed:`,
          err,
        );
        return makeBrokenBundlePlaceholder(
          pluginId,
          comp.name,
          `Failed to load widget bundle: ${message}`,
          "Check the browser console for details. The plugin's other widgets may still work.",
        );
      }
      if (!mod || typeof mod.default !== "function") {
        // eslint-disable-next-line no-console
        console.error(
          `[plugin-component-loader] ${pluginId}/${comp.name}: module loaded but no default export`,
        );
        return makeBrokenBundlePlaceholder(
          pluginId,
          comp.name,
          "Plugin bundle didn't export a default React component.",
          "Plugin author: ensure the file ends with `export default function ...`.",
        );
      }
      return mod;
    });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error(
      `[plugin-component-loader] failed to register ${pluginId}/${comp.name}:`,
      err,
    );
  }
}
