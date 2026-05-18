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
