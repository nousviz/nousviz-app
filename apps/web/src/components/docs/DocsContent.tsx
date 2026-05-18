/**
 * DocsContent — rendered markdown + progress bar + reading time (P116 v0.8.5).
 *
 * Typography rebuilt from the old `prose-sm` with too-close heading
 * sizes into a proper scale:
 *   h1 text-3xl   (dominant)
 *   h2 text-2xl   (section break with bottom border)
 *   h3 text-xl    (subsection)
 *   h4 text-base + muted
 *
 * Prose width constrained to ~72 characters for comfortable reading.
 * On a wide monitor content doesn't stretch across the full column.
 *
 * Progress bar is fixed below the topbar and tracks window scroll.
 * Reading time computed from word count at 200 wpm (typical adult reading).
 */

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import rehypeSlug from "rehype-slug";
import { Clock } from "lucide-react";
import "highlight.js/styles/github-dark.css";

interface DocsContentProps {
  title: string;
  content: string;
}

function computeReadingTime(content: string): number {
  const words = (content || "").split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 200));
}

export default function DocsContent({ title, content }: DocsContentProps) {
  // Window scroll progress bar — tracks the whole page, not a sub-container,
  // because on desktop the content area is inside a flex column that uses
  // the page's natural scroll.
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const doc = document.documentElement;
      const scrolled = doc.scrollTop || document.body.scrollTop;
      const max = doc.scrollHeight - doc.clientHeight;
      setPct(max > 0 ? Math.min(100, Math.max(0, (scrolled / max) * 100)) : 0);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [content]);

  const readingMin = computeReadingTime(content);

  return (
    <>
      {/* Progress bar — fixed at top edge of viewport, 2px, pointer-events off */}
      <div
        className="fixed top-0 left-0 right-0 h-[2px] bg-transparent z-40 pointer-events-none"
        aria-hidden="true"
      >
        <div
          className="h-full bg-primary transition-[width] duration-100"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="max-w-[72ch]">
        {/* Doc header with title + reading time chip */}
        <header className="mb-8 pb-6 border-b border-border">
          <h1 className="text-3xl font-semibold text-foreground mb-2">{title}</h1>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            <span>{readingMin} min read</span>
          </div>
        </header>

        <article
          className="prose prose-invert prose-base max-w-none
            prose-headings:font-semibold prose-headings:text-foreground prose-headings:scroll-mt-20
            prose-h1:text-3xl prose-h1:mb-6
            prose-h2:text-2xl prose-h2:mt-12 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-border
            prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3
            prose-h4:text-base prose-h4:text-muted-foreground prose-h4:mt-6 prose-h4:mb-2
            prose-p:text-muted-foreground prose-p:leading-relaxed
            prose-a:text-primary prose-a:no-underline hover:prose-a:underline
            prose-code:text-primary prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-[0.85em] prose-code:font-mono-deck prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-[hsl(var(--secondary))] prose-pre:border prose-pre:border-border prose-pre:rounded-xl prose-pre:p-4
            prose-strong:text-foreground
            prose-table:text-sm prose-table:border prose-table:border-border prose-table:rounded-lg prose-table:overflow-hidden
            prose-th:text-foreground prose-th:font-medium prose-th:border prose-th:border-border prose-th:px-3 prose-th:py-2 prose-th:bg-secondary/50
            prose-td:text-muted-foreground prose-td:border prose-td:border-border prose-td:px-3 prose-td:py-2
            prose-blockquote:border-primary prose-blockquote:text-muted-foreground prose-blockquote:not-italic
            prose-li:text-muted-foreground prose-li:marker:text-muted-foreground/50
            prose-hr:border-border
          "
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSlug, rehypeHighlight]}>
            {content}
          </ReactMarkdown>
        </article>
      </div>
    </>
  );
}
