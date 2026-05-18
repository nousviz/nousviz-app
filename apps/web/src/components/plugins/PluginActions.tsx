/**
 * PluginActions — renders declarative actions from a plugin manifest (P119, v0.8.6).
 *
 * The backend resolves `disabled_when` / `visible_when` predicates into
 * `disabled` / `visible` booleans before sending the manifest. Core-side
 * contract: the POST endpoint must be plugin-owned (validated at install)
 * and returns a JSON response with any combination of:
 *   { toast, enqueue_job, navigate, refetch, message, level }
 *
 * No plugin-authored JavaScript runs — actions are data.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as Icons from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

export type ActionSlot =
  | "settings_tab_footer"
  | "plugin_page_header"
  | "dashboard_header";

export interface PluginAction {
  id: string;
  label: string;
  slot: ActionSlot;
  style?: "primary" | "secondary" | "danger";
  endpoint: string; // "METHOD /path"
  confirm?: string | false;
  icon?: string;
  disabled?: boolean; // resolved by backend
  visible?: boolean; // resolved by backend (default true)
  disabled_when?: string;
  visible_when?: string;
}

interface Props {
  pluginId: string;
  actions: PluginAction[] | undefined;
  slot: ActionSlot;
  onAfterAction?: () => void; // for refetching manifest on `refetch: true`
}

interface ActionResponse {
  toast?: string;
  message?: string;
  level?: "info" | "warning" | "error";
  enqueue_job?: string;
  navigate?: string;
  refetch?: boolean;
}

function styleClasses(style?: "primary" | "secondary" | "danger"): string {
  switch (style) {
    case "primary":
      return "bg-primary text-primary-foreground hover:bg-primary/90";
    case "danger":
      return "bg-red-500 text-white hover:bg-red-600";
    default:
      return "bg-secondary text-foreground hover:bg-secondary/80";
  }
}

function resolveIcon(name: string | undefined): React.ComponentType<{ className?: string }> | null {
  if (!name) return null;
  const pascal = name
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
  const IconFn = (Icons as unknown as Record<string, React.ComponentType<{ className?: string }>>)[pascal];
  return typeof IconFn === "function" ? IconFn : null;
}

export default function PluginActions({ pluginId: _pluginId, actions, slot, onAfterAction }: Props) {
  const navigate = useNavigate();
  const [pending, setPending] = useState<string | null>(null);
  const [confirmFor, setConfirmFor] = useState<PluginAction | null>(null);
  const [toast, setToast] = useState<{ level: string; message: string } | null>(null);

  const visibleActions = (actions || []).filter(
    (a) => a.slot === slot && a.visible !== false,
  );
  if (visibleActions.length === 0) return null;

  async function runAction(action: PluginAction) {
    setPending(action.id);
    setToast(null);

    const [methodRaw, pathRaw] = action.endpoint.split(/\s+/, 2);
    const method = (methodRaw || "POST").toUpperCase();
    const path = pathRaw || "";

    try {
      const res = await apiFetch(path, { method });
      let body: ActionResponse = {};
      try {
        body = (await res.json()) as ActionResponse;
      } catch {
        // Empty / non-JSON body is fine.
      }

      if (!res.ok) {
        const msg =
          body.message ||
          body.toast ||
          `Action failed (HTTP ${res.status})`;
        setToast({ level: "error", message: msg });
        return;
      }

      if (body.toast || body.message) {
        setToast({
          level: body.level || "info",
          message: body.toast || body.message || "",
        });
      } else {
        setToast({ level: "info", message: `${action.label} · OK` });
      }

      if (body.refetch && onAfterAction) onAfterAction();
      if (body.navigate) navigate(body.navigate);
      // enqueue_job: the plugin's endpoint already inserted the job_runs row
      // (if it declared `enqueue_job` in its response) — core doesn't
      // re-enqueue. The key is a signal for the frontend to optionally
      // navigate to /system/jobs, which we leave to the plugin's navigate
      // field if it wants that.
    } catch (err) {
      setToast({ level: "error", message: String(err) });
    } finally {
      setPending(null);
      setConfirmFor(null);
    }
  }

  function handleClick(action: PluginAction) {
    if (action.disabled || pending) return;
    if (action.confirm && typeof action.confirm === "string") {
      setConfirmFor(action);
    } else {
      void runAction(action);
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-2 items-center">
        {visibleActions.map((action) => {
          const IconComp = resolveIcon(action.icon);
          const isPending = pending === action.id;
          return (
            <button
              key={action.id}
              type="button"
              disabled={action.disabled || isPending}
              onClick={() => handleClick(action)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                styleClasses(action.style),
                (action.disabled || isPending) && "opacity-50 cursor-not-allowed",
              )}
              title={action.disabled ? "Not available yet" : undefined}
            >
              {isPending ? (
                <Icons.Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : IconComp ? (
                <IconComp className="w-3.5 h-3.5" />
              ) : null}
              {action.label}
            </button>
          );
        })}
      </div>

      {toast && (
        <div
          className={cn(
            "mt-2 text-xs px-3 py-2 rounded-md",
            toast.level === "error"
              ? "bg-red-500/10 text-red-300"
              : toast.level === "warning"
              ? "bg-amber-500/10 text-amber-300"
              : "bg-emerald-500/10 text-emerald-300",
          )}
          role="status"
        >
          {toast.message}
        </div>
      )}

      {confirmFor && (
        <div
          className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
          onClick={() => setConfirmFor(null)}
        >
          <div
            className="bg-card border border-border rounded-lg p-5 max-w-sm w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-sm text-foreground mb-4">{String(confirmFor.confirm)}</p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmFor(null)}
                className="px-3 py-1.5 rounded-md text-xs bg-secondary text-foreground hover:bg-secondary/80"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void runAction(confirmFor)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium",
                  styleClasses(confirmFor.style),
                )}
              >
                {confirmFor.label}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
