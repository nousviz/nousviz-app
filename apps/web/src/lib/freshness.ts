/**
 * B165 (v0.9.5): JS port of `_classify_status` + `_schedule_max_age`
 * from `apps/api/src/routes/jobs.py`. Used by the Datasets page to
 * render a status pill per dataset row based on last sync time vs
 * declared cron schedule.
 *
 * Why JS-side and not server-side: the Datasets page reads /api/plugins
 * (which already returns last_sync per dataset) and aggregates client-
 * side. Adding a freshness field server-side would require changing the
 * /api/plugins response shape — not worth the churn for one widget.
 * If a future feature needs the same classification on multiple pages,
 * promote this to the backend (B166-style follow-up).
 *
 * Threshold: a dataset is "stale" when age > 2 × the declared interval
 * (one grace period). "unknown" when last sync exists but no schedule
 * declared. "never" when no last sync at all.
 */

export type FreshnessStatus = "ok" | "stale" | "never" | "untracked" | "unknown";

const SCHEDULE_MAX_AGE_MS: Record<string, number> = {
  "*/5 * * * *":   5 * 60 * 1000,
  "*/10 * * * *":  10 * 60 * 1000,
  "*/15 * * * *":  15 * 60 * 1000,
  "*/30 * * * *":  30 * 60 * 1000,
  "0 * * * *":     60 * 60 * 1000,
  "0 */2 * * *":   2 * 60 * 60 * 1000,
  "0 */4 * * *":   4 * 60 * 60 * 1000,
  "0 */6 * * *":   6 * 60 * 60 * 1000,
  "0 */12 * * *":  12 * 60 * 60 * 1000,
  "0 6 * * *":     24 * 60 * 60 * 1000,
  "0 0 * * *":     24 * 60 * 60 * 1000,
  "0 0 * * 1":     7 * 24 * 60 * 60 * 1000,
};

const DEFAULT_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24h — conservative

function scheduleMaxAgeMs(cron: string | undefined): number {
  if (!cron) return DEFAULT_MAX_AGE_MS;
  return SCHEDULE_MAX_AGE_MS[cron] ?? DEFAULT_MAX_AGE_MS;
}

export function classifyFreshness(
  lastSyncIso: string | null | undefined,
  schedule: string | null | undefined,
  now: Date = new Date(),
): FreshnessStatus {
  // B169 (v0.9.5.1): distinguish "untracked" from "never synced". A
  // table with no last_sync AND no schedule isn't necessarily broken —
  // it may be webhook-ingested, manually populated, or sync-tracked at
  // the plugin level rather than per-table. Calling that "Never synced"
  // is misleading. Reserve "never" for the case where a schedule IS
  // declared but no sync has happened (a real problem).
  if (!lastSyncIso && !schedule) return "untracked";
  if (!lastSyncIso) return "never";
  if (!schedule) return "unknown";

  const lastDt = new Date(lastSyncIso);
  if (Number.isNaN(lastDt.getTime())) return "unknown";

  const ageMs = now.getTime() - lastDt.getTime();
  const thresholdMs = scheduleMaxAgeMs(schedule) * 2;
  return ageMs > thresholdMs ? "stale" : "ok";
}
