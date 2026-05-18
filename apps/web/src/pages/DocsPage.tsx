import { apiFetch } from "@/lib/api";
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AlertCircle, BookOpen, ChevronDown } from "lucide-react";
import DocsNav, { flatDocList, groupBySection, SECTION_ORDER, SECTION_LABELS, type DocEntry } from "@/components/docs/DocsNav";
import DocsContent from "@/components/docs/DocsContent";
import DocsToc from "@/components/docs/DocsToc";
import DocsNavPrevNext from "@/components/docs/DocsNavPrevNext";

interface DocContent {
  slug: string;
  title: string;
  section: string;
  content: string;
}

/**
 * DocsPage — shell wiring for the /docs/:slug reading experience (P116 v0.8.5).
 *
 * Three-column responsive layout:
 *   xl+:   left nav | content | sticky right TOC
 *   md-lg: left nav | content (with inline collapsible TOC above)
 *   <md:   single column + mobile dropdown nav + inline TOC
 *
 * Data fetching + routing lives here; the rendering concerns are
 * delegated to the four components under components/docs/.
 */
export default function DocsPage() {
  const { slug } = useParams<{ slug?: string }>();
  const navigate = useNavigate();

  const [docList, setDocList] = useState<DocEntry[]>([]);
  const [doc, setDoc] = useState<DocContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load doc list on mount
  useEffect(() => {
    apiFetch("/api/docs")
      .then(r => r.json())
      .then(d => {
        setDocList(d.docs ?? []);
        setLoading(false);
        if (!slug && d.docs?.length > 0) {
          const first = (d.docs as DocEntry[]).find(x => x.available);
          if (first) navigate(`/docs/${first.slug}`, { replace: true });
        }
      })
      .catch(() => { setLoading(false); setError("Could not load documentation index."); });
    // slug intentionally omitted — only auto-navigate on initial mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load doc content when slug changes
  useEffect(() => {
    if (!slug) return;
    setContentLoading(true);
    setError(null);
    apiFetch(`/api/docs/${slug}`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json();
      })
      .then(d => { setDoc(d); setContentLoading(false); })
      .catch(() => { setError("Could not load this document."); setContentLoading(false); });
  }, [slug]);

  // Scroll to top on doc change (prevents carry-over scroll state from the
  // previous doc showing when the new one is shorter).
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [slug]);

  const flatDocs = flatDocList(docList);
  const groups = groupBySection(docList);

  return (
    <div className="flex gap-0 min-h-[calc(100vh-56px)] -mx-6 -mt-6">
      {/* Left rail: section nav (hidden on mobile) */}
      <DocsNav docList={docList} activeSlug={slug} loading={loading} />

      {/* Center content column */}
      <main className="flex-1 min-w-0 py-6 px-4 md:py-8 md:px-8 overflow-y-auto">
        {/* Mobile doc selector */}
        {!loading && docList.length > 0 && (
          <div className="md:hidden mb-4 relative">
            <select
              value={slug || ""}
              onChange={e => navigate(`/docs/${e.target.value}`)}
              className="w-full h-10 px-3 pr-8 rounded-lg bg-card border border-border text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {SECTION_ORDER.map(section => {
                const sectionDocs = groups[section];
                if (!sectionDocs?.length) return null;
                return (
                  <optgroup key={section} label={SECTION_LABELS[section] ?? section}>
                    {sectionDocs.map(entry => (
                      <option key={entry.slug} value={entry.slug}>{entry.title}</option>
                    ))}
                  </optgroup>
                );
              })}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          </div>
        )}

        {error ? (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        ) : contentLoading ? (
          <div className="py-20 text-center text-muted-foreground text-sm">Loading…</div>
        ) : doc ? (
          <>
            {/* Inline TOC for tablet/mobile — sidebar variant handles xl+ separately */}
            <DocsToc markdown={doc.content} variant="inline" />
            <DocsContent title={doc.title} content={doc.content} />
            <DocsNavPrevNext docs={flatDocs} currentSlug={doc.slug} />
          </>
        ) : (
          <div className="py-20 text-center">
            <BookOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground text-sm">Select a document from the sidebar.</p>
          </div>
        )}
      </main>

      {/* Right rail: sticky TOC (desktop only, xl+) */}
      {doc && !contentLoading && (
        <div className="hidden xl:block py-8 pr-6">
          <DocsToc markdown={doc.content} variant="sidebar" />
        </div>
      )}
    </div>
  );
}
