import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import MethodBadge from "./MethodBadge";
import type { OpenApiSpec, HttpMethod, Operation } from "./types";

export interface OperationEntry {
  method: HttpMethod;
  path: string;
  summary: string;
  tag: string;
}

export interface TagGroup {
  name: string;
  description?: string;
  operations: OperationEntry[];
}

export function buildTagGroups(spec: OpenApiSpec): TagGroup[] {
  const declaredTags = spec.tags ?? [];
  const byTag = new Map<string, OperationEntry[]>();

  for (const [path, item] of Object.entries(spec.paths ?? {})) {
    for (const method of ["get", "post", "put", "patch", "delete"] as HttpMethod[]) {
      const op = (item as Record<string, Operation>)[method];
      if (!op) continue;
      const tag = (op.tags && op.tags[0]) || "untagged";
      if (!byTag.has(tag)) byTag.set(tag, []);
      byTag.get(tag)!.push({
        method,
        path,
        summary: op.summary || "",
        tag,
      });
    }
  }

  const groups: TagGroup[] = [];
  // Preserve declared tag order; append undeclared tags at the end.
  const seen = new Set<string>();
  for (const t of declaredTags) {
    const ops = byTag.get(t.name) || [];
    if (ops.length === 0) continue;
    groups.push({ name: t.name, description: t.description, operations: ops });
    seen.add(t.name);
  }
  for (const [name, ops] of byTag) {
    if (seen.has(name)) continue;
    groups.push({ name, operations: ops });
  }
  // Sort each group: stable by path then method order is fine — operators read
  // alphabetically by path within a tag.
  for (const g of groups) {
    g.operations.sort((a, b) => {
      const cmp = a.path.localeCompare(b.path);
      return cmp !== 0 ? cmp : a.method.localeCompare(b.method);
    });
  }
  return groups;
}

function filterGroups(groups: TagGroup[], q: string): TagGroup[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return groups;
  return groups
    .map((g) => {
      const tagMatches = g.name.toLowerCase().includes(needle);
      const ops = g.operations.filter((op) => {
        if (tagMatches) return true;
        const hay = `${op.method} ${op.path} ${op.summary}`.toLowerCase();
        return hay.includes(needle);
      });
      return { ...g, operations: ops };
    })
    .filter((g) => g.operations.length > 0);
}

export default function OperationList({
  groups,
  selected,
  onSelect,
  search,
  onSearchChange,
}: {
  groups: TagGroup[];
  selected: { method: HttpMethod; path: string } | null;
  onSelect: (op: { method: HttpMethod; path: string }) => void;
  search: string;
  onSearchChange: (v: string) => void;
}) {
  const filtered = useMemo(() => filterGroups(groups, search), [groups, search]);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  function toggle(name: string) {
    setCollapsed((c) => ({ ...c, [name]: !c[name] }));
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search operations…"
          className="w-full h-8 pl-8 pr-3 rounded-md bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-body"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-xs text-muted-foreground px-1 py-2">
          No operations match <span className="font-mono-deck">{search}</span>.
        </p>
      ) : (
        <nav aria-label="API operations" className="space-y-3">
          {filtered.map((g) => {
            const isCollapsed = !!collapsed[g.name];
            return (
              <div key={g.name}>
                <button
                  type="button"
                  onClick={() => toggle(g.name)}
                  className="w-full flex items-center gap-1.5 px-1 py-1 text-xs font-display uppercase tracking-wide text-muted-foreground hover:text-foreground"
                >
                  {isCollapsed ? (
                    <ChevronRight className="w-3 h-3" />
                  ) : (
                    <ChevronDown className="w-3 h-3" />
                  )}
                  <span>{g.name}</span>
                  <span className="ml-auto text-[10px] tabular-nums text-muted-foreground/60">
                    {g.operations.length}
                  </span>
                </button>
                {!isCollapsed && (
                  <ul className="space-y-0.5 mt-0.5">
                    {g.operations.map((op) => {
                      const isSelected =
                        selected &&
                        selected.method === op.method &&
                        selected.path === op.path;
                      return (
                        <li key={op.method + op.path}>
                          <button
                            type="button"
                            onClick={() => onSelect({ method: op.method, path: op.path })}
                            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-xs transition-colors ${
                              isSelected
                                ? "bg-primary/10 text-foreground"
                                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                            }`}
                          >
                            <MethodBadge method={op.method} size="xs" />
                            <span className="font-mono-deck truncate" title={op.path}>
                              {op.path}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>
      )}
    </div>
  );
}
