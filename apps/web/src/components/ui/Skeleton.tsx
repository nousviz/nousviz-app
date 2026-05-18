import { cn } from "@/lib/utils";

/**
 * Skeleton — a pulsing placeholder that mirrors the SHAPE of the final
 * content. Replaces bare "Loading..." text so pages don't visibly snap
 * from empty → populated.
 *
 * Use as a direct block (height + width via classNames) or nest inside
 * a layout component to mirror the final structure. Width defaults to
 * full-bleed so callers usually only need to set a height.
 *
 * Example — mimic a 16-row table:
 *   {[...Array(16)].map((_, i) =>
 *     <Skeleton key={i} className="h-8 w-full" />)}
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-secondary/60",
        "h-4 w-full",
        className,
      )}
    />
  );
}
