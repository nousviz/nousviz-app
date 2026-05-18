/**
 * B288 (v0.9.11.26) — `<ScrollableTabs>` mobile-friendly tab strip.
 *
 * Horizontally-scrollable tab strip with a right-edge gradient fade
 * hint so operators see "scroll for more" on phones. Pairs with an
 * optional sibling action button (Wizard / Refresh) that:
 *   - on `<sm`: stacks below the strip, full-width
 *   - on `sm+`: sits to the right of the strip, shrunk to content
 *
 * Replaces inline tab implementations at:
 *   - apps/web/src/pages/SettingsPage.tsx (tab strip ~1242, Wizard button ~1261)
 *   - apps/web/src/components/system/SystemTabBar.tsx
 */

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export interface Tab {
  id: string;
  label: ReactNode;
  /** Optional icon (lucide-react component, already rendered). */
  icon?: ReactNode;
}

interface Props {
  tabs: Tab[];
  current: string;
  onChange: (id: string) => void;
  /** Optional sibling action button. Stacks below the strip on `<sm`. */
  action?: ReactNode;
  className?: string;
  /** Optional ARIA label for the tab list. */
  ariaLabel?: string;
}

export function ScrollableTabs({
  tabs,
  current,
  onChange,
  action,
  className,
  ariaLabel,
}: Props) {
  return (
    <div
      className={cn(
        "space-y-2 sm:space-y-0 sm:flex sm:items-stretch sm:gap-3",
        className,
      )}
    >
      <div className="relative flex-1 min-w-0">
        <div className="overflow-x-auto scrollbar-hide">
          <div
            role="tablist"
            aria-label={ariaLabel}
            className="flex gap-1 min-w-max border-b border-border"
          >
            {tabs.map((t) => {
              const active = current === t.id;
              return (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => onChange(t.id)}
                  className={cn(
                    "shrink-0 px-3 py-2 text-xs font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5",
                    active
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t.icon}
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>
        {/* Right-edge gradient fade — visible only when content overflows.
            Uses pointer-events-none so it doesn't block the tab buttons
            beneath it. */}
        <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-background to-transparent" />
      </div>
      {action && <div className="shrink-0 sm:self-center">{action}</div>}
    </div>
  );
}
