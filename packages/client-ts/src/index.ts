/**
 * @nousviz/client — Auto-generated TypeScript client for the NousViz API.
 *
 * Re-exports everything from the generated layer plus a small
 * `createClient({ baseUrl, getToken })` helper that wires up the
 * shared OpenAPI config so callers don't have to set base URL + auth
 * header manually.
 */

import { OpenAPI } from "./generated";
import type { OpenAPIConfig } from "./generated";

// Re-export every model + service.
export * from "./generated";

/**
 * Configure the shared client.
 *
 * @example
 *   import { createClient, AuthService } from "@nousviz/client";
 *
 *   createClient({
 *     baseUrl: "https://nousviz.online",
 *     getToken: () => localStorage.getItem("token") ?? "",
 *   });
 *
 *   const me = await AuthService.authMe();
 *   console.log(me.email);
 *
 * Calls without `getToken` are sent unauthenticated — fine for the
 * public endpoints (`GET /api/health`, etc.) and for development.
 */
export function createClient(opts: {
  baseUrl: string;
  /** Called per request to populate `X-Session-Token`. Sync only. */
  getToken?: () => string | null | undefined;
  /** Override request headers. Merged with the auth header. */
  headers?: Record<string, string>;
}): void {
  OpenAPI.BASE = opts.baseUrl.replace(/\/+$/, "");
  if (opts.getToken) {
    OpenAPI.HEADERS = async () => {
      const token = opts.getToken?.();
      const out: Record<string, string> = { ...(opts.headers ?? {}) };
      if (token) out["X-Session-Token"] = token;
      return out;
    };
  } else if (opts.headers) {
    OpenAPI.HEADERS = opts.headers;
  }
}

/** The underlying OpenAPI config object. Exposed for advanced overrides. */
export { OpenAPI };
export type { OpenAPIConfig };
