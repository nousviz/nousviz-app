// OpenAPI 3.x subset that B221's native renderer cares about.
// Intentionally narrow — see todo/0.9.7/tickets/B221-native-api-reference.md
// for what's in vs out of scope.

export type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

export interface OpenApiSpec {
  openapi?: string;
  info?: {
    title?: string;
    description?: string;
    version?: string;
    license?: { name?: string; url?: string };
    contact?: { name?: string; url?: string; email?: string };
  };
  servers?: { url: string; description?: string }[];
  tags?: { name: string; description?: string }[];
  paths: Record<string, PathItem>;
  components?: {
    schemas?: Record<string, JsonSchema>;
    securitySchemes?: Record<string, SecurityScheme>;
  };
  security?: Record<string, string[]>[];
}

export type PathItem = Partial<Record<HttpMethod, Operation>>;

export interface Operation {
  tags?: string[];
  summary?: string;
  description?: string;
  operationId?: string;
  parameters?: Parameter[];
  requestBody?: RequestBody;
  responses?: Record<string, Response>;
  security?: Record<string, string[]>[];
}

export interface Parameter {
  name: string;
  in: "path" | "query" | "header" | "cookie";
  required?: boolean;
  description?: string;
  schema?: JsonSchema;
}

export interface RequestBody {
  description?: string;
  required?: boolean;
  content?: Record<string, MediaType>;
}

export interface Response {
  description?: string;
  content?: Record<string, MediaType>;
}

export interface MediaType {
  schema?: JsonSchema;
  example?: unknown;
}

// JSON Schema subset used by FastAPI's emission. Recursion is allowed via
// `properties`, `items`, `anyOf`, `oneOf`. We render one level of $ref by
// pointer-resolution, deeper refs render as a clickable schema name.
export interface JsonSchema {
  $ref?: string;
  type?: string | string[];
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
  anyOf?: JsonSchema[];
  oneOf?: JsonSchema[];
  allOf?: JsonSchema[];
  enum?: unknown[];
  default?: unknown;
  format?: string;
  example?: unknown;
}

export interface SecurityScheme {
  type: string;
  name?: string;
  in?: string;
  description?: string;
  scheme?: string;
}

// Resolves a single-level "#/components/schemas/<Name>" pointer.
// Returns null on unknown ref (callers render a sentinel).
export function resolveRef(spec: OpenApiSpec, ref: string): { name: string; schema: JsonSchema } | null {
  const m = ref.match(/^#\/components\/schemas\/(.+)$/);
  if (!m) return null;
  const name = m[1];
  const schema = spec.components?.schemas?.[name];
  if (!schema) return null;
  return { name, schema };
}

// Stable hash slug for selection: "GET:/api/plugins/{plugin_id}" → that exact string.
// We don't URL-encode aggressively because deep links read better with `{}` intact.
export function operationHash(method: HttpMethod, path: string): string {
  return `${method.toUpperCase()}:${path}`;
}

export function parseHash(hash: string): { method: HttpMethod; path: string } | null {
  const cleaned = hash.startsWith("#") ? hash.slice(1) : hash;
  const idx = cleaned.indexOf(":");
  if (idx < 0) return null;
  const method = cleaned.slice(0, idx).toLowerCase() as HttpMethod;
  const path = cleaned.slice(idx + 1);
  if (!["get", "post", "put", "patch", "delete"].includes(method)) return null;
  if (!path.startsWith("/")) return null;
  return { method, path };
}
