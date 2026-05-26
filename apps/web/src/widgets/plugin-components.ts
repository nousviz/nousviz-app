import { lazy, type ComponentType, type LazyExoticComponent } from "react";

export interface CustomWidgetProps {
  pluginId: string;
  dashboardName: string;
  config: Record<string, unknown>;
}

type ComponentEntry = LazyExoticComponent<ComponentType<CustomWidgetProps>>;

/**
 * Registry of custom widget components that plugins can reference by name
 * in their dashboard YAML via `type: custom, component: "ComponentName"`.
 *
 * Two ways entries land here:
 *   1. Built-in (compile-time) — first-party widgets in this repo
 *   2. Plugin-shipped (runtime, B151 v0.9.4) — `registerPluginComponent(name, loader)`
 *      called by `loadPluginFrontendComponents()` at app boot when the
 *      operator has consented (`plugin_settings._trust_frontend = true`).
 *
 * B223 (v0.9.7.6): registry is observable via `subscribePluginComponents`
 * + `getPluginComponentsSnapshot`. `WidgetRenderer` reads via
 * `useSyncExternalStore` so a late registration (race with navigation,
 * runtime trust) re-resolves without manual reload.
 *
 * To add a new built-in widget:
 *   1. Create the component in widgets/ (must accept CustomWidgetProps)
 *   2. Add one line to BUILTIN below
 */
const BUILTIN: Record<string, ComponentEntry> = {
  WebhookManager: lazy(() => import("@/widgets/WebhookManager")),
};

let entries: Readonly<Record<string, ComponentEntry>> = Object.freeze({ ...BUILTIN });
const listeners = new Set<() => void>();

// v0.10.0.5.1: loader-completion state lets the dashboard distinguish
// "loader still in flight, widget might appear" from "loader done, widget
// genuinely not registered." Without this, WidgetRenderer flashes a red
// "Unknown custom component: X" error on first paint while the loader is
// still walking /api/plugins, even though the widget would render fine a
// few hundred ms later when registerPluginComponent fires. With many
// plugins installed (17+ on prod), this misleading error is the dominant
// surface for operators after a fresh install / Trust.
let pluginLoaderCompleted = false;

// v1.0.2: distinct "the loader actually failed" state — separate from
// "completed with zero components" (which happens legitimately when no
// plugins are trusted). Set by notifyPluginLoaderFailed() when the
// /api/plugins fetch couldn't be salvaged by the loader's retry loop.
// AuthGate reads this to render a recoverable error screen instead of
// dumping the user into a permanently-broken dashboard.
let pluginLoaderFailed = false;
let pluginLoaderFailureReason: string | null = null;

function emit() {
  for (const listener of listeners) listener();
}

export function getPluginComponentsSnapshot(): Readonly<Record<string, ComponentEntry>> {
  return entries;
}

export function subscribePluginComponents(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getRegisteredComponents(): string[] {
  return Object.keys(entries);
}

/**
 * v0.10.0.5.1: signal that `loadPluginFrontendComponents()` has finished
 * walking the manifest list (either all registerPluginComponent calls
 * have fired, OR the loader silently skipped — fetch failed, untrusted
 * operator session, etc.). After this fires, the dashboard renderer
 * is allowed to surface "Unknown component" errors for components not
 * in the registry; before, it shows a neutral "Loading widget…" placeholder.
 */
export function notifyPluginLoaderCompleted(): void {
  if (pluginLoaderCompleted) return;
  pluginLoaderCompleted = true;
  emit();
}

export function getPluginLoaderCompletedSnapshot(): boolean {
  return pluginLoaderCompleted;
}

/**
 * v1.0.2: signal that loadPluginFrontendComponents() exhausted its retry
 * budget without ever getting a usable /api/plugins response. This is
 * DIFFERENT from completing-with-zero-components — that's a legitimate
 * outcome when no plugins are trusted. This is "the host could not even
 * find out what plugins exist." Used by AuthGate to render a recoverable
 * error screen instead of dropping the user into a dashboard with no
 * widget registry.
 *
 * `reason` is a short operator-readable string for the error screen
 * (e.g., "Server returned 503 after 3 retries").
 */
export function notifyPluginLoaderFailed(reason: string): void {
  pluginLoaderFailed = true;
  pluginLoaderFailureReason = reason;
  // Failure implies completion — clear the "still loading" placeholder
  // state too so callers don't double-display.
  pluginLoaderCompleted = true;
  emit();
}

export function getPluginLoaderFailedSnapshot(): boolean {
  return pluginLoaderFailed;
}

export function getPluginLoaderFailureReason(): string | null {
  return pluginLoaderFailureReason;
}

/**
 * Reset failure state. Called by the LoadErrorScreen's reload action so
 * an in-app retry can re-attempt cleanly without a full page reload.
 */
export function clearPluginLoaderFailure(): void {
  pluginLoaderFailed = false;
  pluginLoaderFailureReason = null;
  pluginLoaderCompleted = false;
  emit();
}

/**
 * B151 (v0.9.4): runtime registration for plugin-shipped components.
 *
 * Called from plugin-component-loader.ts after a successful dynamic
 * import. The component is wrapped in lazy() so it integrates with
 * the existing Suspense boundaries that already render BUILTIN
 * components — no special-casing in DashboardRenderer.
 *
 * `loader` is a thunk that returns the dynamically-imported module's
 * default export. Same shape as what `lazy()` expects.
 */
export function registerPluginComponent(
  name: string,
  loader: () => Promise<{ default: ComponentType<CustomWidgetProps> }>,
): void {
  entries = Object.freeze({ ...entries, [name]: lazy(loader) });
  emit();
}

/**
 * Remove a runtime-registered component. Called when an operator
 * revokes a plugin's frontend trust — the component is removed from
 * the registry on the next page load. (In-flight renders continue
 * until the page is reloaded — by design; we don't unmount mid-render.)
 */
export function unregisterPluginComponent(name: string): void {
  // Only unregister if it's NOT a built-in (BUILTIN entries are core code)
  if (name in BUILTIN) return;
  if (!(name in entries)) return;
  const next = { ...entries };
  delete next[name];
  entries = Object.freeze(next);
  emit();
}
