/**
 * SetupChecklist — declarative plugin setup guide (P121, v0.8.6).
 *
 * Backend resolves `done_if` predicates into `done: boolean` on each item,
 * plus top-level `all_done` and `visible` flags derived from `show_until`.
 * Component only renders what's passed in; it never re-resolves predicates.
 *
 * Dismissal is client-side (localStorage per plugin) so the checklist is
 * a nudge, not a compliance feature.
 */

import { useMemo, useState } from "react";
import { CheckCircle2, Circle, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChecklistItem {
  id: string;
  label: string;
  done: boolean;
}

export interface SetupChecklistData {
  show_until?: "all_done" | "credentials_saved" | "dismissed";
  items: ChecklistItem[];
  all_done?: boolean;
  visible?: boolean;
}

interface Props {
  pluginId: string;
  checklist: SetupChecklistData | undefined;
}

function dismissKey(pluginId: string): string {
  return `nousviz.plugin.${pluginId}.setup_checklist.dismissed`;
}

export default function SetupChecklist({ pluginId, checklist }: Props) {
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(dismissKey(pluginId)) === "1";
    } catch {
      return false;
    }
  });

  const hidden = useMemo(() => {
    if (!checklist || !checklist.items || checklist.items.length === 0) return true;
    if (dismissed) return true;
    // Backend already applied show_until logic into `visible`.
    return checklist.visible === false;
  }, [checklist, dismissed]);

  if (!checklist) return null;

  if (hidden) {
    // Offer a subtle "Show setup guide" restore when dismissed/hidden.
    if (dismissed) {
      return (
        <button
          type="button"
          onClick={() => {
            try {
              localStorage.removeItem(dismissKey(pluginId));
            } catch {
              /* best effort */
            }
            setDismissed(false);
          }}
          className="text-[11px] text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
        >
          Show setup guide
        </button>
      );
    }
    return null;
  }

  const allDone = checklist.all_done ?? checklist.items.every((i) => i.done);

  if (allDone && checklist.show_until === "all_done") {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2.5 flex items-center justify-between">
        <p className="text-xs text-emerald-300 inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5" /> Setup complete
        </p>
        <button
          type="button"
          onClick={() => {
            try {
              localStorage.setItem(dismissKey(pluginId), "1");
            } catch {
              /* best effort */
            }
            setDismissed(true);
          }}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  const doneCount = checklist.items.filter((i) => i.done).length;

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm text-foreground">Setup checklist</h3>
        <span className="text-[11px] font-mono-deck text-muted-foreground">
          {doneCount} of {checklist.items.length} complete
        </span>
      </div>
      <ul className="space-y-1.5">
        {checklist.items.map((item) => (
          <li
            key={item.id}
            className={cn(
              "text-xs inline-flex items-center gap-2 w-full",
              item.done ? "text-muted-foreground line-through" : "text-foreground",
            )}
          >
            {item.done ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : (
              <Circle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            )}
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
