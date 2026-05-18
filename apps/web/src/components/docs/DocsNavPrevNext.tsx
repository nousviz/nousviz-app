/**
 * DocsNavPrevNext — walks the flat section-ordered doc list (P116 v0.8.5).
 *
 * Rendered at the bottom of each doc. First doc shows only "next",
 * last shows only "prev". Each card shows the target doc's title.
 */

import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DocEntry } from "./DocsNav";

interface DocsNavPrevNextProps {
  docs: DocEntry[];   // the FLAT, section-ordered, available-only list
  currentSlug: string;
}

export default function DocsNavPrevNext({ docs, currentSlug }: DocsNavPrevNextProps) {
  const idx = docs.findIndex(d => d.slug === currentSlug);
  if (idx < 0) return null;
  const prev = idx > 0 ? docs[idx - 1] : null;
  const next = idx < docs.length - 1 ? docs[idx + 1] : null;

  if (!prev && !next) return null;

  return (
    <nav
      aria-label="Doc navigation"
      className="mt-16 pt-8 border-t border-border grid grid-cols-2 gap-4 max-w-[72ch]"
    >
      {prev ? (
        <Link
          to={`/docs/${prev.slug}`}
          className={cn(
            "group rounded-lg border border-border p-4 hover:border-primary/40 hover:bg-secondary/40 transition-colors",
          )}
        >
          <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
            <ArrowLeft className="w-3 h-3" />
            Previous
          </span>
          <span className="text-sm text-foreground group-hover:text-primary transition-colors">
            {prev.title}
          </span>
        </Link>
      ) : (
        <div />
      )}

      {next ? (
        <Link
          to={`/docs/${next.slug}`}
          className={cn(
            "group rounded-lg border border-border p-4 text-right hover:border-primary/40 hover:bg-secondary/40 transition-colors",
          )}
        >
          <span className="flex items-center justify-end gap-1 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
            Next
            <ArrowRight className="w-3 h-3" />
          </span>
          <span className="text-sm text-foreground group-hover:text-primary transition-colors">
            {next.title}
          </span>
        </Link>
      ) : (
        <div />
      )}
    </nav>
  );
}
