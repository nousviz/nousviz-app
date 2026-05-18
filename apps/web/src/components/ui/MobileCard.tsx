/**
 * B288.1 (v0.9.11.26.1) — `<MobileCard>` shell for the mobile-card
 * fallback to wide tables.
 *
 * Used by consumers that wrap their <DataTable> in `hidden sm:block`
 * and add a sibling `block sm:hidden` rendering each row as a stacked
 * card. The card lays out:
 *
 *   ┌──────────────────────────────────────────┐
 *   │  TITLE                              BADGE │
 *   ├──────────────────────────────────────────┤
 *   │  key:  value                              │
 *   │  key:  value                              │
 *   │  …                                        │
 *   ├──────────────────────────────────────────┤
 *   │  [action] [action] [action]               │
 *   └──────────────────────────────────────────┘
 *
 * Operator feedback on B288: sticky-left + sticky-right cells with a
 * forced minWidth on phones left ~40px of viewport for middle columns
 * (unreadable). Cards eliminate horizontal scroll entirely on phones.
 */

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface Props {
  /** Top-of-card title row. Usually the data the desktop table puts
   *  in the sticky-left first column. */
  title: ReactNode;
  /** Optional small element rendered to the right of the title (e.g.
   *  status pill, slack badge). */
  badge?: ReactNode;
  /** Body — a list of key/value pairs. The card adds vertical spacing
   *  between children. */
  children?: ReactNode;
  /** Action buttons row at the bottom. Wraps if the buttons exceed
   *  the card width (multi-button rows on narrow phones). */
  actions?: ReactNode;
  className?: string;
}

export function MobileCard({ title, badge, children, actions, className }: Props) {
  return (
    <div
      className={cn(
        "bg-card border border-border rounded-lg p-3 space-y-2.5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">{title}</div>
        {badge && <div className="shrink-0">{badge}</div>}
      </div>
      {children && <div className="space-y-1.5 text-xs">{children}</div>}
      {actions && (
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border/50">
          {actions}
        </div>
      )}
    </div>
  );
}

/**
 * Convenience for the most common card-body shape: a labeled key/value
 * row. Renders as a two-column row with the label muted on the left
 * and the value on the right.
 *
 * Use direct JSX inside `<MobileCard>` for anything fancier.
 */
interface RowProps {
  label: ReactNode;
  /** Right-aligned value. Use ReactNode so consumers can pass pills /
   *  formatted numbers / etc. */
  children: ReactNode;
  /** Optional className for the value cell (e.g. for monospace + colored
   *  numerics). */
  valueClassName?: string;
}

export function MobileCardRow({ label, children, valueClassName }: RowProps) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">
        {label}
      </span>
      <span className={cn("text-right min-w-0", valueClassName)}>
        {children}
      </span>
    </div>
  );
}
