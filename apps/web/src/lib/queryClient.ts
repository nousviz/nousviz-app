/**
 * queryClient — shared TanStack Query client for the whole app.
 *
 * v0.10.0.7 (Phase 14 / P14.1): introduced as the client-side
 * data-cache layer. Closes the "loading… loading plugin… loading…"
 * cascade by deduping repeat fetches, returning cached data on
 * navigation, and pausing background work when tabs are hidden.
 *
 * Defaults tuned for NousViz's read-mostly admin UI:
 *
 *   staleTime              60s   — data considered fresh for 1 minute;
 *                                  repeat queries within that window are
 *                                  served from cache without a network
 *                                  round-trip. Tuned higher than the
 *                                  TanStack default (0s) because most
 *                                  NousViz data doesn't change second-by-
 *                                  second; the operator's perception of
 *                                  "instant navigation" is the win.
 *
 *   gcTime                 5min  — once a query has no observers, keep
 *                                  it in memory this long before garbage-
 *                                  collecting. Lets a quick navigate-
 *                                  away-and-back keep the cached data.
 *
 *   refetchOnWindowFocus   false — don't re-fetch when the operator
 *                                  switches back to the tab. Saves
 *                                  noise; the data is already cached.
 *
 *   refetchOnReconnect     true  — DO re-fetch when network comes back
 *                                  online (operator on a flaky connection).
 *
 *   retry                  1     — one retry on transient errors. The
 *                                  API is internal; we don't need the
 *                                  default 3 retries.
 *
 *   networkMode            online — only fire when actually online;
 *                                  TanStack Query's default "online"
 *                                  short-circuits offline correctly.
 *
 * Per-query overrides via the `options` arg of useApiQuery() / useQuery().
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 60_000,        // 1 minute
            gcTime: 5 * 60_000,       // 5 minutes
            refetchOnWindowFocus: false,
            refetchOnReconnect: true,
            retry: 1,
            networkMode: "online",
        },
        mutations: {
            retry: 0,                  // never retry mutations
            networkMode: "online",
        },
    },
});
