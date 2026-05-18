/**
 * DocsNav — left-rail documentation section navigation (P116 v0.8.5).
 *
 * Lift-and-shift of the existing sidebar logic from DocsPage.tsx so
 * the main page can stay small after the v0.8.5 layout restructure.
 */

import { Link } from "react-router-dom";
import { BookOpen, ChevronRight, FileText } from "lucide-react";

export interface DocEntry {
  slug: string;
  title: string;
  section: string;
  available: boolean;
}

const SECTION_ORDER = ["platform", "plugins", "development"];

const SECTION_LABELS: Record<string, string> = {
  platform: "Platform",
  plugins: "Plugins",
  development: "Development",
};

function groupBySection(docs: DocEntry[]): Record<string, DocEntry[]> {
  const groups: Record<string, DocEntry[]> = {};
  for (const doc of docs) {
    if (!groups[doc.section]) groups[doc.section] = [];
    groups[doc.section].push(doc);
  }
  return groups;
}

interface DocsNavProps {
  docList: DocEntry[];
  activeSlug?: string;
  loading: boolean;
}

export default function DocsNav({ docList, activeSlug, loading }: DocsNavProps) {
  const groups = groupBySection(docList);

  return (
    <aside className="hidden md:block w-56 shrink-0 border-r border-border bg-card/50 py-6 px-3 overflow-y-auto">
      <div className="flex items-center gap-2 px-2 mb-5">
        <BookOpen className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-semibold text-foreground">Documentation</h2>
      </div>

      {loading ? (
        <p className="text-xs text-muted-foreground px-2">Loading…</p>
      ) : (
        SECTION_ORDER.map(section => {
          const sectionDocs = groups[section];
          if (!sectionDocs?.length) return null;
          return (
            <div key={section} className="mb-5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground px-2 pb-1.5">
                {SECTION_LABELS[section] ?? section}
              </p>
              {sectionDocs.map(entry => (
                <Link
                  key={entry.slug}
                  to={`/docs/${entry.slug}`}
                  className={[
                    "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
                    entry.slug === activeSlug
                      ? "bg-primary/10 text-primary font-medium"
                      : entry.available
                      ? "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                      : "text-muted-foreground/40 cursor-not-allowed pointer-events-none",
                  ].join(" ")}
                >
                  <FileText className="w-3.5 h-3.5 shrink-0" />
                  <span className="flex-1 truncate">{entry.title}</span>
                  {entry.slug === activeSlug && <ChevronRight className="w-3 h-3 shrink-0" />}
                </Link>
              ))}
            </div>
          );
        })
      )}
    </aside>
  );
}

/**
 * Build a flat array of available docs in section order — used by
 * DocsNavPrevNext to compute the adjacent doc in each direction.
 */
export function flatDocList(docList: DocEntry[]): DocEntry[] {
  const groups = groupBySection(docList);
  const flat: DocEntry[] = [];
  for (const section of SECTION_ORDER) {
    for (const entry of groups[section] || []) {
      if (entry.available) flat.push(entry);
    }
  }
  return flat;
}

export { SECTION_ORDER, SECTION_LABELS, groupBySection };
