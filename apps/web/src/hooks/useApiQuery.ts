/**
 * useApiQuery — thin wrapper around TanStack Query's useQuery that
 * fetches from the NousViz API via apiFetch().
 *
 * v0.10.0.7 (Phase 14 / P14.1): introduced to replace the component-
 * local setLoading(true) + useEffect(fetch).finally(setLoading(false))
 * pattern across the app (71 sites identified by Phase 14). One unified
 * cache, request dedupe, stale-while-revalidate, and prefetch-on-hover.
 *
 * Usage:
 *
 *   const { data, isLoading, error, refetch } = useApiQuery<PluginListResponse>(
 *     ["plugins", "list"],          // cache key — any tuple of serialisable values
 *     "/api/plugins"                // endpoint
 *   );
 *
 *   if (isLoading) return <Skeleton />;
 *   if (error)     return <ErrorPanel message={error.message} />;
 *   return <PluginGrid plugins={data?.plugins ?? []} />;
 *
 * With per-query options (override the global defaults from queryClient.ts):
 *
 *   useApiQuery(["alerts", "live"], "/api/alerts", {
 *     refetchInterval: 30_000,     // poll every 30s while tab visible
 *     staleTime: 0,                // always consider stale
 *   });
 *
 * Prefetching (e.g. on sidebar hover) — call directly on the query client:
 *
 *   import { queryClient } from "@/lib/queryClient";
 *   queryClient.prefetchQuery({
 *     queryKey: ["plugin", id],
 *     queryFn: () => apiFetch(`/api/plugins/${id}`).then(r => r.json()),
 *   });
 *
 * Mutation invalidation — after a successful POST/PUT/DELETE, invalidate
 * the affected cache entries so any mounted observer re-fetches:
 *
 *   queryClient.invalidateQueries({ queryKey: ["plugins"] });
 */

import { useQuery, type UseQueryOptions, type UseQueryResult } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

type QueryKey = readonly unknown[];

type ApiQueryOptions<TData> = Omit<
    UseQueryOptions<TData, Error, TData, QueryKey>,
    "queryKey" | "queryFn"
> & {
    /**
     * Optional fetch initialiser passed to apiFetch (e.g. for POST query
     * shapes, custom headers). Rarely needed — most useApiQuery calls
     * are simple GETs.
     */
    fetchInit?: RequestInit;

    /**
     * Optional response transformer. Defaults to `r => r.json()`.
     */
    transform?: (response: Response) => Promise<TData>;
};

/**
 * Default response transformer — parses JSON. Throws if the response
 * is not 2xx so the error path runs.
 */
async function defaultTransform<TData>(response: Response): Promise<TData> {
    if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
    }
    return response.json() as Promise<TData>;
}

export function useApiQuery<TData = unknown>(
    queryKey: QueryKey,
    endpoint: string,
    options?: ApiQueryOptions<TData>,
): UseQueryResult<TData, Error> {
    const { fetchInit, transform = defaultTransform, ...queryOptions } = options ?? {};

    return useQuery<TData, Error, TData, QueryKey>({
        queryKey,
        queryFn: async () => {
            const response = await apiFetch(endpoint, fetchInit);
            return transform(response);
        },
        ...queryOptions,
    });
}
