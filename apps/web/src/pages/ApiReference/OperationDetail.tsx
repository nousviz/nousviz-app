import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Lock, Globe } from "lucide-react";
import MethodBadge from "./MethodBadge";
import SchemaPreview from "./SchemaPreview";
import ParametersTable from "./ParametersTable";
import TryItOut from "./TryItOut";
import type { OpenApiSpec, HttpMethod, Operation } from "./types";

interface Props {
  spec: OpenApiSpec;
  method: HttpMethod;
  path: string;
  op: Operation;
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-display uppercase tracking-wide text-muted-foreground">
        {label}
      </h3>
      {children}
    </section>
  );
}

function effectiveSecurity(op: Operation, spec: OpenApiSpec): Record<string, string[]>[] {
  if (op.security !== undefined) return op.security;
  return spec.security ?? [];
}

function describeSecurity(
  security: Record<string, string[]>[]
): { isPublic: boolean; names: string[] } {
  if (!security || security.length === 0) {
    // OpenAPI: missing global security = no auth required by default.
    return { isPublic: true, names: [] };
  }
  // OpenAPI: security: [{}] explicitly means "public" (empty requirement).
  const hasEmpty = security.some((req) => Object.keys(req).length === 0);
  const names = new Set<string>();
  for (const req of security) {
    for (const k of Object.keys(req)) names.add(k);
  }
  return {
    isPublic: hasEmpty && names.size === 0,
    names: [...names],
  };
}

function buildCurlExample(method: HttpMethod, path: string, hasBody: boolean): string {
  const url = `https://nousviz.online${path}`;
  const lines = [`curl -X ${method.toUpperCase()} "${url}" \\`];
  lines.push(`  -H "X-Session-Token: <your-session-token>"`);
  if (hasBody) {
    lines[lines.length - 1] += ` \\`;
    lines.push(`  -H "Content-Type: application/json" \\`);
    lines.push(`  -d '{ ... }'`);
  }
  return lines.join("\n");
}

export default function OperationDetail({ spec, method, path, op }: Props) {
  const requestBodySchema = op.requestBody?.content?.["application/json"]?.schema;
  const hasBody = !!requestBodySchema;
  const responses = Object.entries(op.responses ?? {});
  const security = effectiveSecurity(op, spec);
  const sec = describeSecurity(security);
  const curl = useMemo(
    () => buildCurlExample(method, path, hasBody),
    [method, path, hasBody]
  );

  return (
    <article className="space-y-8 max-w-3xl">
      {/* Header */}
      <header className="space-y-3 pb-5 border-b border-border">
        <div className="flex flex-wrap items-center gap-3">
          <MethodBadge method={method} />
          <code className="font-mono-deck text-base text-foreground break-all">
            {path}
          </code>
        </div>
        {op.summary && (
          <h1 className="font-display text-xl text-foreground">{op.summary}</h1>
        )}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          {op.tags?.map((t) => (
            <span
              key={t}
              className="px-2 py-0.5 rounded bg-secondary border border-border font-mono-deck text-[10px] uppercase tracking-wide"
            >
              {t}
            </span>
          ))}
          {op.operationId && (
            <span className="font-mono-deck text-[11px]">
              operationId: <span className="text-foreground">{op.operationId}</span>
            </span>
          )}
        </div>
      </header>

      {/* Description */}
      {op.description && (
        <Section label="Description">
          <div
            className="prose prose-invert prose-sm max-w-none
              prose-p:text-muted-foreground prose-p:leading-relaxed
              prose-a:text-primary prose-a:no-underline hover:prose-a:underline
              prose-code:text-primary prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-[0.85em] prose-code:font-mono-deck prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-[hsl(var(--secondary))] prose-pre:border prose-pre:border-border prose-pre:rounded-md
              prose-strong:text-foreground
              prose-li:text-muted-foreground"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{op.description}</ReactMarkdown>
          </div>
        </Section>
      )}

      {/* Security */}
      <Section label="Security">
        {sec.isPublic ? (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Globe className="w-3.5 h-3.5" />
            Public — no auth required.
          </p>
        ) : (
          <div className="space-y-1.5">
            {sec.names.map((n) => {
              const scheme = spec.components?.securitySchemes?.[n];
              return (
                <p key={n} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Lock className="w-3.5 h-3.5" />
                  <span className="font-mono-deck text-foreground">{scheme?.name || n}</span>
                  <span>{scheme?.description}</span>
                </p>
              );
            })}
          </div>
        )}
      </Section>

      {/* Parameters */}
      {op.parameters && op.parameters.length > 0 && (
        <Section label="Parameters">
          <ParametersTable parameters={op.parameters} spec={spec} />
        </Section>
      )}

      {/* Request body */}
      {requestBodySchema && (
        <Section label="Request body">
          {op.requestBody?.description && (
            <p className="text-xs text-muted-foreground">
              {op.requestBody.description}
            </p>
          )}
          <SchemaPreview schema={requestBodySchema} spec={spec} />
        </Section>
      )}

      {/* Responses */}
      <Section label="Responses">
        {responses.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No responses declared.</p>
        ) : (
          <div className="space-y-3">
            {responses.map(([code, resp]) => {
              const schema = resp.content?.["application/json"]?.schema;
              const codeNum = parseInt(code, 10);
              const codeColor =
                codeNum >= 200 && codeNum < 300
                  ? "text-emerald-400"
                  : codeNum >= 400 && codeNum < 500
                  ? "text-amber-400"
                  : codeNum >= 500
                  ? "text-rose-400"
                  : "text-muted-foreground";
              return (
                <div key={code} className="rounded-md border border-border bg-card/40 p-3 space-y-2">
                  <div className="flex items-center gap-3">
                    <span className={`font-mono-deck text-sm ${codeColor}`}>{code}</span>
                    {resp.description && (
                      <span className="text-xs text-muted-foreground">{resp.description}</span>
                    )}
                  </div>
                  {schema && Object.keys(schema).length > 0 && (
                    <SchemaPreview schema={schema} spec={spec} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* Try-it-out widget */}
      <Section label="Try it">
        <TryItOut method={method} path={path} op={op} />
      </Section>

      {/* Curl reference */}
      <Section label="Curl">
        <pre className="text-xs font-mono-deck bg-background/60 border border-border rounded p-3 overflow-x-auto">
          <code>{curl}</code>
        </pre>
      </Section>
    </article>
  );
}
