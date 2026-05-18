/**
 * B288 (v0.9.11.26) — `<DataTable>` mobile-friendly table wrapper.
 *
 * Wraps a `<table>` so wide tables don't fall off the screen on phones.
 * Below `md` the wrapper bleeds to the viewport edges (-mx-4 px-4) so
 * the sticky columns visually anchor against the page edge. On `md+`
 * the layout is identical to a plain table — no desktop regression.
 *
 * Usage convention (consumer-applied per-cell):
 *   - First column gets:
 *       className="sticky left-0 bg-card z-10 shadow-[inset_-1px_0_0_var(--border)]"
 *   - Action column (rightmost) gets:
 *       className="sticky right-0 bg-card z-10 shadow-[inset_1px_0_0_var(--border)]"
 *
 * The shadow inset stand-in for a border keeps the column-edge visible
 * when the table scrolls underneath. Reference impl this generalises:
 * apps/web/src/pages/DatasetDetailPage.tsx:684 (sticky-left was already
 * in use there pre-B288).
 */

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface Props {
  /** Min-width below which horizontal scroll kicks in. Default 640px.
   *  Tune per-table to keep readable column widths. */
  minWidth?: string;
  /** Optional extra classes for the inner `<table>`. */
  className?: string;
  children: ReactNode;
}

export function DataTable({ minWidth = "640px", className, children }: Props) {
  return (
    <div className="overflow-x-auto -mx-4 md:mx-0 px-4 md:px-0">
      <table
        style={{ minWidth }}
        className={cn("w-full text-xs", className)}
      >
        {children}
      </table>
    </div>
  );
}
