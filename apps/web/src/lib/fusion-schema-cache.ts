/**
 * fusion-schema-cache — process-lifetime cache of CatalogTable responses
 * for the fusion builder's source/column dropdowns (B263 / v0.9.11.7).
 *
 * The cache wraps `/api/catalog/plugins/{id}/tables/{table}` lookups so
 * the visual builder doesn't re-hit the API on every column dropdown
 * render. Lookups are async (lazy fetch) and shared across pages via
 * the singleton export.
 */

import { apiFetch } from "@/lib/api";
import type { SchemaCacheLookup, SchemaColumn } from "./fusion-compiler";

interface CatalogTableResponse {
  name: string;
  plugin_id: string;
  table_type: string;
  columns: SchemaColumn[];
  row_count_estimate: number | null;
}

export class FusionSchemaCache implements SchemaCacheLookup {
  private inflight = new Map<string, Promise<CatalogTableResponse | null>>();
  private resolved = new Map<string, SchemaColumn[]>();

  /** Async fetch + cache. Returns null if the API rejects (404/403/etc). */
  async fetch(pluginId: string, table: string): Promise<SchemaColumn[] | null> {
    const key = this.key(pluginId, table);
    if (this.resolved.has(key)) return this.resolved.get(key)!;

    if (!this.inflight.has(key)) {
      this.inflight.set(key, this.fetchOnce(pluginId, table));
    }
    const result = await this.inflight.get(key)!;
    if (result) {
      this.resolved.set(key, result.columns);
      return result.columns;
    }
    return null;
  }

  /** Synchronous lookup — returns null if not yet loaded. Used by the
   * compiler for inline validation without blocking; the builder's
   * preview re-runs whenever a fetch resolves so failed validations
   * eventually clear once the schema lands. */
  lookup(pluginId: string, table: string): SchemaColumn[] | null {
    return this.resolved.get(this.key(pluginId, table)) ?? null;
  }

  invalidate(pluginId?: string, table?: string): void {
    if (!pluginId) {
      this.resolved.clear();
      this.inflight.clear();
      return;
    }
    const prefix = `${pluginId}::`;
    if (!table) {
      for (const k of [...this.resolved.keys()]) {
        if (k.startsWith(prefix)) this.resolved.delete(k);
      }
      for (const k of [...this.inflight.keys()]) {
        if (k.startsWith(prefix)) this.inflight.delete(k);
      }
      return;
    }
    const k = this.key(pluginId, table);
    this.resolved.delete(k);
    this.inflight.delete(k);
  }

  private key(pluginId: string, table: string): string {
    return `${pluginId}::${table}`;
  }

  private async fetchOnce(
    pluginId: string,
    table: string,
  ): Promise<CatalogTableResponse | null> {
    try {
      const res = await apiFetch(
        `/api/catalog/plugins/${encodeURIComponent(pluginId)}/tables/${encodeURIComponent(table)}`,
      );
      if (!res.ok) return null;
      return (await res.json()) as CatalogTableResponse;
    } catch {
      return null;
    }
  }
}

/** Singleton — shared across pages so column lookups are warm. */
export const sharedFusionSchemaCache = new FusionSchemaCache();
