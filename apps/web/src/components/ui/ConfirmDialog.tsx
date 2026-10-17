/**
 * B331: a small confirmation dialog for destructive actions, in the style
 * of the delete-subscription dialog in Settings → Maintenance. Escape and
 * the backdrop cancel; the confirm button shows a busy state while the
 * action runs.
 */
import { useEffect, type ReactNode } from "react";
import { AlertTriangle, Trash2 } from "lucide-react";

export function ConfirmDialog({ open, title, message, confirmLabel = "Delete", busy = false, onConfirm, onCancel }: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy) onCancel(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
         onClick={() => { if (!busy) onCancel(); }}>
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title"
           className="bg-card border border-border rounded-lg p-5 max-w-md w-full space-y-3"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 id="confirm-dialog-title" className="text-sm font-display text-foreground">{title}</h3>
            <div className="text-xs text-muted-foreground mt-1">{message}</div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 pt-2">
          <button onClick={onCancel} disabled={busy}
                  className="h-8 px-3 rounded-md text-xs text-muted-foreground hover:text-foreground disabled:opacity-50">
            Cancel
          </button>
          <button onClick={onConfirm} disabled={busy} autoFocus
                  className="h-8 px-3 rounded-md bg-red-500 text-white text-xs hover:bg-red-600 disabled:opacity-50 flex items-center gap-1.5">
            <Trash2 className="w-3 h-3" />
            {busy ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
