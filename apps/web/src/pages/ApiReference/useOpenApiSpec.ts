import { useEffect, useState } from "react";
import type { OpenApiSpec } from "./types";

// Module-scoped cache so navigation away and back doesn't refetch.
let cachedSpec: OpenApiSpec | null = null;
let inFlight: Promise<OpenApiSpec> | null = null;

export function useOpenApiSpec() {
  const [spec, setSpec] = useState<OpenApiSpec | null>(cachedSpec);
  const [loading, setLoading] = useState<boolean>(!cachedSpec);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedSpec) return;
    let cancelled = false;
    if (!inFlight) {
      // Public endpoint — raw fetch, not apiFetch.
      inFlight = fetch("/openapi.json", { credentials: "omit" })
        .then((r) => {
          if (!r.ok) throw new Error(`/openapi.json ${r.status}`);
          return r.json();
        })
        .then((j) => {
          cachedSpec = j as OpenApiSpec;
          return cachedSpec;
        })
        .finally(() => {
          // On success or failure, clear the in-flight slot so a refresh can retry.
          // On success cachedSpec is set; on failure the next render will re-enter.
          inFlight = null;
        });
    }
    inFlight
      .then((s) => {
        if (cancelled) return;
        setSpec(s);
        setLoading(false);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { spec, loading, error };
}
