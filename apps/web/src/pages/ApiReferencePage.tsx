/**
 * ApiReferencePage — interactive API reference, native React.
 *
 * B221 (v0.9.7.1): replaces the v0.9.7.0 Scalar mount. Uses NousViz primitives
 * (Section card pattern, NavSection, font-mono-deck, design tokens) so the
 * page reads as part of the platform inside AppLayout's chrome.
 *
 * Reads /openapi.json once on mount via useOpenApiSpec (module-cached).
 */

import { useEffect, useMemo, useState } from "react";
import { Code as CodeIcon, ExternalLink, AlertCircle, Loader2 } from "lucide-react";
import OperationList, { buildTagGroups } from "./ApiReference/OperationList";
import OperationDetail from "./ApiReference/OperationDetail";
import { useHashOperation } from "./ApiReference/useHashOperation";
import { useOpenApiSpec } from "./ApiReference/useOpenApiSpec";
import type { HttpMethod, Operation } from "./ApiReference/types";

export default function ApiReferencePage() {
  const { spec, loading, error } = useOpenApiSpec();
  const groups = useMemo(() => (spec ? buildTagGroups(spec) : []), [spec]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useHashOperation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Default to first operation of first group when nothing is selected.
  useEffect(() => {
    if (selected || groups.length === 0) return;
    const first = groups[0].operations[0];
    if (first) setSelected({ method: first.method, path: first.path });
    // setSelected identity is stable from useHashOperation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, groups]);

  const currentOp = useMemo<{ method: HttpMethod; path: string; op: Operation } | null>(() => {
    if (!selected || !spec) return null;
    const item = spec.paths[selected.path];
    if (!item) return null;
    const op = (item as Record<string, Operation>)[selected.method];
    if (!op) return null;
    return { method: selected.method, path: selected.path, op };
  }, [selected, spec]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-12">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading API spec…
      </div>
    );
  }

  if (error || !spec) {
    return (
      <div className="flex items-start gap-2 text-sm text-rose-400 py-12">
        <AlertCircle className="w-4 h-4 mt-0.5" />
        <div>
          <p>Failed to load /openapi.json.</p>
          {error && <p className="text-xs text-muted-foreground mt-1 font-mono-deck">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Page header — keeps consistent with other top-level pages */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CodeIcon className="w-4 h-4 text-muted-foreground" />
          <h1 className="font-display text-base text-foreground">API reference</h1>
          {spec.info?.version && (
            <span className="text-xs font-mono-deck text-muted-foreground">
              v{spec.info.version}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <a
            href="/openapi.json"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ExternalLink className="w-3 h-3" /> openapi.json
          </a>
          <a
            href="/openapi.yaml"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ExternalLink className="w-3 h-3" /> openapi.yaml
          </a>
        </div>
      </header>

      {/* Mobile nav toggle */}
      <button
        type="button"
        onClick={() => setMobileNavOpen((o) => !o)}
        className="md:hidden w-full h-9 px-3 rounded-md border border-border bg-card text-sm text-foreground flex items-center justify-between"
      >
        <span>Browse operations</span>
        <span className="text-xs text-muted-foreground">
          {mobileNavOpen ? "Hide" : "Show"}
        </span>
      </button>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Left: operation list */}
        <aside
          className={`${mobileNavOpen ? "block" : "hidden"} md:block w-full md:w-72 shrink-0`}
        >
          <div className="md:sticky md:top-[calc(var(--topbar-h)+1rem)] md:max-h-[calc(100vh-var(--topbar-h)-3rem)] md:overflow-y-auto md:pr-1">
            <OperationList
              groups={groups}
              selected={selected}
              onSelect={(op) => {
                setSelected(op);
                setMobileNavOpen(false);
              }}
              search={search}
              onSearchChange={setSearch}
            />
          </div>
        </aside>

        {/* Right: operation detail */}
        <main className="flex-1 min-w-0">
          {currentOp ? (
            <OperationDetail
              spec={spec}
              method={currentOp.method}
              path={currentOp.path}
              op={currentOp.op}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Select an operation from the list.
            </p>
          )}
        </main>
      </div>
    </div>
  );
}
