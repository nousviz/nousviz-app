import type { JsonSchema, OpenApiSpec } from "./types";
import { resolveRef } from "./types";

interface Props {
  schema: JsonSchema | undefined;
  spec: OpenApiSpec;
  depth?: number;
  inline?: boolean;
}

function describeType(s: JsonSchema): string {
  if (Array.isArray(s.type)) return s.type.join(" | ");
  if (s.type) {
    if (s.type === "array" && s.items) return `array<${describeType(s.items)}>`;
    return s.type;
  }
  if (s.anyOf) return s.anyOf.map(describeType).join(" | ");
  if (s.oneOf) return s.oneOf.map(describeType).join(" | ");
  if (s.allOf) return "object";
  if (s.$ref) {
    const m = s.$ref.match(/\/([^/]+)$/);
    return m ? m[1] : "$ref";
  }
  if (s.enum) return "enum";
  return "any";
}

export default function SchemaPreview({ schema, spec, depth = 0, inline = false }: Props) {
  if (!schema) {
    return <p className="text-xs text-muted-foreground italic">No schema declared.</p>;
  }

  // Resolve a ref one level. Deeper refs render as a clickable badge with the
  // schema name — we don't recurse to avoid cycles.
  if (schema.$ref) {
    const resolved = resolveRef(spec, schema.$ref);
    if (!resolved) {
      return <p className="text-xs text-muted-foreground italic">Unknown $ref: {schema.$ref}</p>;
    }
    if (depth >= 1) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-mono-deck text-primary">
          {resolved.name}
        </span>
      );
    }
    return (
      <SchemaPreview
        schema={resolved.schema}
        spec={spec}
        depth={depth + 1}
        inline={inline}
      />
    );
  }

  // anyOf/oneOf — render as union, expand each branch one level if simple.
  const union = schema.anyOf || schema.oneOf;
  if (union && union.length) {
    // Common FastAPI shape: anyOf:[{type:string},{type:null}] for Optional[str].
    const simple = union.every((s) => s.type && !s.properties && !s.$ref);
    if (simple) {
      return (
        <span className="text-xs font-mono-deck text-muted-foreground">
          {union.map(describeType).join(" | ")}
        </span>
      );
    }
    return (
      <div className="space-y-1">
        {union.map((s, i) => (
          <SchemaPreview key={i} schema={s} spec={spec} depth={depth + 1} inline />
        ))}
      </div>
    );
  }

  if (schema.type === "array" && schema.items) {
    return (
      <div>
        <p className="text-xs text-muted-foreground mb-1">
          array of <span className="font-mono-deck text-foreground">{describeType(schema.items)}</span>
        </p>
        {schema.items.properties && (
          <SchemaPreview schema={schema.items} spec={spec} depth={depth + 1} />
        )}
      </div>
    );
  }

  if (schema.properties) {
    const required = new Set(schema.required || []);
    const props = Object.entries(schema.properties);
    if (props.length === 0) {
      return <p className="text-xs text-muted-foreground italic">empty object</p>;
    }
    return (
      <div className={`rounded-md border border-border ${inline ? "" : "bg-background/50"}`}>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-secondary/30">
              <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                Field
              </th>
              <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                Type
              </th>
              <th className="text-left font-display text-[11px] uppercase tracking-wide text-muted-foreground px-3 py-1.5">
                Description
              </th>
            </tr>
          </thead>
          <tbody>
            {props.map(([name, s]) => (
              <tr key={name} className="border-b border-border last:border-b-0">
                <td className="px-3 py-1.5 align-top">
                  <span className="font-mono-deck text-foreground">{name}</span>
                  {required.has(name) && (
                    <span className="ml-1.5 text-[10px] text-rose-400 uppercase tracking-wide">
                      required
                    </span>
                  )}
                </td>
                <td className="px-3 py-1.5 align-top font-mono-deck text-muted-foreground">
                  {describeType(s)}
                </td>
                <td className="px-3 py-1.5 align-top text-muted-foreground">
                  {s.title || s.description || s.format || ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Primitive
  return (
    <div className="text-xs font-mono-deck text-muted-foreground">
      {describeType(schema)}
      {schema.enum && (
        <span className="ml-2 text-foreground">
          [{schema.enum.map((v) => JSON.stringify(v)).join(", ")}]
        </span>
      )}
    </div>
  );
}
