/**
 * DocsToc — sticky table of contents with scroll-spy (P116 v0.8.5).
 *
 * - Desktop (xl+): rendered as a sticky right-rail column
 * - Tablet/mobile: rendered inline above content as collapsible <details>
 *
 * Uses github-slugger to generate heading IDs that match rehype-slug's
 * output byte-for-byte. Previous implementation used a homegrown regex
 * that diverged on headings with parens, numbers, and unicode — the
 * "anchor links don't always work" bug.
 *
 * Scroll-spy via IntersectionObserver: whichever h2/h3 is in the
 * reading window (top 40% of viewport) gets highlighted.
 */

import { useEffect, useMemo, useState } from "react";
import GithubSlugger from "github-slugger";
import { cn } from "@/lib/utils";

export interface Heading {
  level: 2 | 3;
  text: string;
  slug: string;
}

/**
 * Extract h2/h3 headings from markdown + compute github-slugger IDs.
 * A fresh slugger per call matches rehype-slug's per-tree duplicate
 * handling ("foo" → "foo", then "foo" again → "foo-1").
 */
export function extractHeadings(markdown: string): Heading[] {
  const slugger = new GithubSlugger();
  const headings: Heading[] = [];
  if (!markdown) return headings;
  // Simple line-based parser — matches rehype's heading node extraction
  // for all practical markdown we ship. Fenced code blocks aren't a
  // concern because we only match line-start `#` patterns and the
  // markdown we write doesn't start code blocks at column 0 with
  // adjacent "##".
  let inFence = false;
  for (const raw of markdown.split("\n")) {
    const line = raw.trimEnd();
    if (line.startsWith("```")) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = line.match(/^(#{2,3})\s+(.+)$/);
    if (!m) continue;
    const level = m[1].length as 2 | 3;
    const text = m[2].replace(/\s*#+\s*$/, "").trim(); // strip closing #
    headings.push({ level, text, slug: slugger.slug(text) });
  }
  return headings;
}

interface DocsTocProps {
  markdown: string;
  /** Variant: inline for mobile/tablet (above content),
   *  sidebar for desktop (sticky right column). */
  variant?: "sidebar" | "inline";
}

export default function DocsToc({ markdown, variant = "sidebar" }: DocsTocProps) {
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);

  // Scroll-spy. rootMargin tuned so the "active" heading is the one
  // the reader is currently in the middle of, not the one about to
  // arrive. The top 40% is the reading zone.
  useEffect(() => {
    if (headings.length === 0) return;
    // Re-run after render so rehype-slug has added IDs to the DOM
    const ids = headings.map(h => h.slug);
    const observed = ids
      .map(id => document.getElementById(id))
      .filter((el): el is HTMLElement => !!el);

    if (observed.length === 0) return;

    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .map(e => e.target as HTMLElement)
          .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
        if (visible[0]) setActiveSlug(visible[0].id);
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0 },
    );
    observed.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, [headings]);

  if (headings.length < 2) return null;

  const list = (
    <ul className="space-y-1">
      {headings.map((h, i) => (
        <li key={`${h.slug}-${i}`}>
          <a
            href={`#${h.slug}`}
            className={cn(
              "block text-xs transition-colors border-l-2 -ml-px pl-3 py-0.5",
              h.level === 3 && "pl-6",
              activeSlug === h.slug
                ? "border-primary text-primary font-medium"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {h.text}
          </a>
        </li>
      ))}
    </ul>
  );

  if (variant === "inline") {
    return (
      <details className="xl:hidden mb-6 rounded-lg border border-border bg-secondary/30 p-4 group">
        <summary className="cursor-pointer text-[10px] text-muted-foreground uppercase tracking-wider font-semibold list-none flex items-center justify-between">
          <span>On this page</span>
          <span className="text-muted-foreground group-open:rotate-180 transition-transform">▾</span>
        </summary>
        <div className="mt-3">{list}</div>
      </details>
    );
  }

  return (
    <aside className="hidden xl:block w-56 shrink-0">
      <div className="sticky top-[calc(var(--topbar-h,64px)+1rem)] max-h-[calc(100vh-var(--topbar-h,64px)-2rem)] overflow-y-auto pr-2">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-2">
          On this page
        </p>
        {list}
      </div>
    </aside>
  );
}
