import { useMemo, useState } from "react";
import { Send, Terminal, AlertTriangle, Loader2 } from "lucide-react";
import type { HttpMethod, Operation, Parameter } from "./types";

interface Props {
  method: HttpMethod;
  path: string;
  op: Operation;
}

interface ResponseState {
  status: number;
  statusText: string;
  durationMs: number;
  body: string;
  contentType: string;
  bodyParsed?: unknown;
}

const UNSAFE_METHODS: ReadonlySet<HttpMethod> = new Set(["post", "put", "patch", "delete"]);

function readSessionToken(): string {
  // The SPA stores the token under "token" in localStorage (apiFetch reads it).
  try {
    return localStorage.getItem("token") ?? "";
  } catch {
    return "";
  }
}

function substitutePathParams(path: string, values: Record<string, string>): string {
  return path.replace(/\{([^}]+)\}/g, (match, name) => {
    const v = values[name];
    if (v === undefined || v === "") return match; // leave placeholder visible
    return encodeURIComponent(v);
  });
}

function buildQueryString(
  params: Parameter[],
  values: Record<string, string>
): string {
  const pairs: string[] = [];
  for (const p of params) {
    if (p.in !== "query") continue;
    const v = values[p.name];
    if (v === undefined || v === "") continue;
    pairs.push(`${encodeURIComponent(p.name)}=${encodeURIComponent(v)}`);
  }
  return pairs.length > 0 ? `?${pairs.join("&")}` : "";
}

export default function TryItOut({ method, path, op }: Props) {
  const params = op.parameters ?? [];
  const pathParams = useMemo(() => params.filter((p) => p.in === "path"), [params]);
  const queryParams = useMemo(() => params.filter((p) => p.in === "query"), [params]);
  const requestBodySchema = op.requestBody?.content?.["application/json"]?.schema;
  const hasBody = !!requestBodySchema;
  const isUnsafe = UNSAFE_METHODS.has(method);

  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const [body, setBody] = useState<string>("{\n  \n}");
  const [token, setToken] = useState<string>("");
  const [tokenLoaded, setTokenLoaded] = useState(false);
  const [pending, setPending] = useState(false);
  const [resp, setResp] = useState<ResponseState | null>(null);
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState(false);

  // Lazy-load the session token from localStorage on first interaction so
  // the value isn't bound into rendered output if the user never opens the form.
  const ensureToken = () => {
    if (!tokenLoaded) {
      setToken(readSessionToken());
      setTokenLoaded(true);
    }
  };

  const setParam = (name: string, value: string) => {
    setParamValues((prev) => ({ ...prev, [name]: value }));
  };

  const submit = async () => {
    setBodyError(null);
    setResp(null);

    // Validate path params: every {name} must have a non-empty value.
    const missing = pathParams
      .filter((p) => !(paramValues[p.name] && paramValues[p.name].length > 0))
      .map((p) => p.name);
    if (missing.length > 0) {
      setBodyError(`Missing path param: ${missing.join(", ")}`);
      return;
    }

    // Validate body JSON when applicable.
    let parsedBody: unknown = undefined;
    if (hasBody) {
      const trimmed = body.trim();
      if (trimmed.length > 0) {
        try {
          parsedBody = JSON.parse(trimmed);
        } catch (e) {
          setBodyError(`Invalid JSON: ${(e as Error).message}`);
          return;
        }
      }
    }

    if (isUnsafe && !confirmModal) {
      setConfirmModal(true);
      return;
    }
    setConfirmModal(false);

    const url = substitutePathParams(path, paramValues) + buildQueryString(params, paramValues);
    const headers: Record<string, string> = {};
    if (token) headers["X-Session-Token"] = token;
    if (parsedBody !== undefined) headers["Content-Type"] = "application/json";

    const init: RequestInit = {
      method: method.toUpperCase(),
      headers,
    };
    if (parsedBody !== undefined) {
      init.body = JSON.stringify(parsedBody);
    }

    setPending(true);
    const start = performance.now();
    try {
      const r = await fetch(url, init);
      const text = await r.text();
      let bodyParsed: unknown = undefined;
      const ct = r.headers.get("content-type") ?? "";
      if (ct.includes("application/json") && text.length > 0) {
        try {
          bodyParsed = JSON.parse(text);
        } catch {
          // Leave body as raw text.
        }
      }
      setResp({
        status: r.status,
        statusText: r.statusText,
        durationMs: Math.round(performance.now() - start),
        body: text,
        contentType: ct,
        bodyParsed,
      });
    } catch (e) {
      setResp({
        status: 0,
        statusText: "(network error)",
        durationMs: Math.round(performance.now() - start),
        body: (e as Error).message,
        contentType: "",
      });
    } finally {
      setPending(false);
    }
  };

  const codeColor = (code: number) =>
    code >= 200 && code < 300
      ? "text-emerald-400"
      : code >= 400 && code < 500
      ? "text-amber-400"
      : code >= 500
      ? "text-rose-400"
      : "text-muted-foreground";

  return (
    <div className="rounded-md border border-border bg-card/40 p-4 space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Terminal className="w-3.5 h-3.5" />
        Sends a real request from this browser. Path/query params are substituted into the URL; body is sent as JSON.
      </div>

      {/* Path params */}
      {pathParams.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-display uppercase tracking-wide text-muted-foreground">Path parameters</div>
          {pathParams.map((p) => (
            <ParamInput key={p.name} param={p} value={paramValues[p.name] ?? ""} onChange={(v) => setParam(p.name, v)} />
          ))}
        </div>
      )}

      {/* Query params */}
      {queryParams.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-display uppercase tracking-wide text-muted-foreground">Query parameters</div>
          {queryParams.map((p) => (
            <ParamInput key={p.name} param={p} value={paramValues[p.name] ?? ""} onChange={(v) => setParam(p.name, v)} />
          ))}
        </div>
      )}

      {/* Body */}
      {hasBody && (
        <div className="space-y-2">
          <div className="text-[11px] font-display uppercase tracking-wide text-muted-foreground">Request body (JSON)</div>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            spellCheck={false}
            className="w-full h-40 text-xs font-mono-deck bg-background/60 border border-border rounded p-3 focus:outline-none focus:ring-1 focus:ring-primary/30"
          />
          {bodyError && (
            <div className="flex items-center gap-2 text-xs text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5" />
              {bodyError}
            </div>
          )}
        </div>
      )}

      {/* Auth token */}
      <div className="space-y-2">
        <div className="text-[11px] font-display uppercase tracking-wide text-muted-foreground">X-Session-Token</div>
        <input
          type="text"
          value={token}
          onFocus={ensureToken}
          onChange={(e) => setToken(e.target.value)}
          placeholder="(your-session-token — auto-filled from localStorage when you focus this field)"
          className="w-full text-xs font-mono-deck bg-background/60 border border-border rounded p-2 focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
      </div>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={pending}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-display uppercase tracking-wide disabled:opacity-50"
        >
          {pending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          Send
        </button>
        <span className="text-xs font-mono-deck text-muted-foreground">
          {method.toUpperCase()} {substitutePathParams(path, paramValues)}
          {buildQueryString(params, paramValues)}
        </span>
      </div>

      {/* Response */}
      {resp && (
        <div className="space-y-2 pt-2 border-t border-border">
          <div className="text-[11px] font-display uppercase tracking-wide text-muted-foreground">Response</div>
          <div className="flex items-center gap-3 text-xs">
            <span className={`font-mono-deck ${codeColor(resp.status)}`}>
              {resp.status || "—"} {resp.statusText}
            </span>
            <span className="text-muted-foreground">{resp.durationMs}ms</span>
            {resp.contentType && (
              <span className="text-muted-foreground font-mono-deck">{resp.contentType}</span>
            )}
          </div>
          <pre className="text-xs font-mono-deck bg-background/60 border border-border rounded p-3 overflow-x-auto max-h-96 overflow-y-auto">
            <code>
              {resp.bodyParsed !== undefined
                ? JSON.stringify(resp.bodyParsed, null, 2)
                : resp.body || "(empty body)"}
            </code>
          </pre>
        </div>
      )}

      {/* Confirm modal for unsafe methods */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="rounded-md border border-border bg-card p-5 max-w-md space-y-3">
            <div className="flex items-center gap-2 text-amber-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-display text-sm">Confirm {method.toUpperCase()} request</span>
            </div>
            <p className="text-xs text-muted-foreground">
              This is an unsafe method. The request will modify state on the live API. Continue?
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setConfirmModal(false)}
                className="px-3 py-1.5 text-xs font-display uppercase tracking-wide rounded border border-border hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submit}
                className="px-3 py-1.5 text-xs font-display uppercase tracking-wide rounded bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30"
              >
                Send anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ParamInput({
  param,
  value,
  onChange,
}: {
  param: Parameter;
  value: string;
  onChange: (v: string) => void;
}) {
  const placeholder = param.description || `${param.in} param: ${param.name}`;
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2 text-[11px] font-mono-deck text-muted-foreground">
        <span className="text-foreground">{param.name}</span>
        {param.required && <span className="text-rose-400">*</span>}
        {param.schema?.type && <span>({String(param.schema.type)})</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full text-xs font-mono-deck bg-background/60 border border-border rounded p-2 focus:outline-none focus:ring-1 focus:ring-primary/30"
      />
    </div>
  );
}
