import type { Parameter, OpenApiSpec } from "./types";
import { resolveRef } from "./types";

function typeFor(p: Parameter, spec: OpenApiSpec): string {
  let s = p.schema;
  if (!s) return "any";
  if (s.$ref) {
    const r = resolveRef(spec, s.$ref);
    if (r) s = r.schema;
  }
  if (Array.isArray(s.type)) return s.type.join(" | ");
  if (s.type) return s.type;
  if (s.anyOf) {
    const types = s.anyOf
      .map((b) => (Array.isArray(b.type) ? b.type.join(" | ") : b.type))
      .filter(Boolean);
    return types.join(" | ") || "any";
  }
  return "any";
}

export default function ParametersTable({
  parameters,
  spec,
}: {
  parameters: Parameter[];
  spec: OpenApiSpec;
}) {
  if (!parameters.length) return null;
  const path = parameters.filter((p) => p.in === "path");
  const query = parameters.filter((p) => p.in === "query");
  const groups: { label: string; rows: Parameter[] }[] = [];
  if (path.length) groups.push({ label: "Path parameters", rows: path });
  if (query.length) groups.push({ label: "Query parameters", rows: query });

  return (
    <div className="space-y-3">
      {groups.map((g) => (
        <div key={g.label}>
          <h4 className="text-xs font-display uppercase tracking-wide text-muted-foreground mb-2">
            {g.label}
          </h4>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-secondary/30 border-b border-border">
                  <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                    Name
                  </th>
                  <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                    Type
                  </th>
                  <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                    Required
                  </th>
                  <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody>
                {g.rows.map((p) => (
                  <tr key={p.in + p.name} className="border-b border-border last:border-b-0">
                    <td className="px-3 py-1.5 align-top font-mono-deck text-foreground">
                      {p.name}
                    </td>
                    <td className="px-3 py-1.5 align-top font-mono-deck text-muted-foreground">
                      {typeFor(p, spec)}
                    </td>
                    <td className="px-3 py-1.5 align-top">
                      {p.required ? (
                        <span className="text-[10px] text-rose-400 uppercase tracking-wide">
                          required
                        </span>
                      ) : (
                        <span className="text-[10px] text-muted-foreground">optional</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 align-top text-muted-foreground">
                      {p.description || p.schema?.title || ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
