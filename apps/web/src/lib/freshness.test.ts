/**
 * B165 (v0.9.5): unit tests for the JS classifyFreshness port.
 *
 * Pure function, no side effects. Tests pin the contract: same
 * input → same output, regardless of the wall clock at test time
 * (we inject `now`).
 *
 * If apps/web doesn't have a test runner wired (Vitest/Jest), these
 * tests are a one-off verification: run with
 *   npx tsx apps/web/src/lib/freshness.test.ts
 * — assertion failures throw and exit nonzero.
 */

import { classifyFreshness } from "./freshness";

const now = new Date("2026-04-27T12:00:00Z");

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }
}

// "never" — no last sync at all
assert(
  classifyFreshness(null, "0 * * * *", now) === "never",
  "null lastSync → never",
);
assert(
  classifyFreshness(undefined, "*/5 * * * *", now) === "never",
  "undefined lastSync → never",
);

// "unknown" — last sync exists but no schedule declared
assert(
  classifyFreshness("2026-04-27T11:30:00Z", undefined, now) === "unknown",
  "lastSync without schedule → unknown",
);
assert(
  classifyFreshness("2026-04-27T11:30:00Z", null, now) === "unknown",
  "lastSync with null schedule → unknown",
);

// "ok" — within 2× the declared interval
const thirtyMinAgo = new Date(now.getTime() - 30 * 60 * 1000).toISOString();
assert(
  classifyFreshness(thirtyMinAgo, "0 * * * *", now) === "ok",
  "30min ago on hourly schedule → ok (within 2×1h grace)",
);

const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000).toISOString();
assert(
  classifyFreshness(fiveMinAgo, "*/5 * * * *", now) === "ok",
  "5min ago on 5min schedule → ok (just at the edge)",
);

// "stale" — past 2× the declared interval
const threeHoursAgo = new Date(now.getTime() - 3 * 60 * 60 * 1000).toISOString();
assert(
  classifyFreshness(threeHoursAgo, "0 * * * *", now) === "stale",
  "3h ago on hourly schedule → stale (past 2×1h grace)",
);

const fifteenMinAgo = new Date(now.getTime() - 15 * 60 * 1000).toISOString();
assert(
  classifyFreshness(fifteenMinAgo, "*/5 * * * *", now) === "stale",
  "15min ago on 5min schedule → stale (past 2×5min grace)",
);

// Unknown cron pattern → conservative 24h default
const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000).toISOString();
assert(
  classifyFreshness(oneHourAgo, "42 3 * 1-6 *", now) === "ok",
  "1h ago on unknown cron → ok (24h default × 2 = 48h grace)",
);

// Invalid date string → unknown
assert(
  classifyFreshness("not-an-iso-date", "0 * * * *", now) === "unknown",
  "invalid lastSync → unknown",
);

// B169 (v0.9.5.1): "untracked" — no last sync AND no schedule.
// Distinguishes from "never synced" (which implies a schedule exists
// and the table should sync but hasn't).
assert(
  classifyFreshness(null, null, now) === "untracked",
  "null lastSync + null schedule → untracked (not 'never')",
);
assert(
  classifyFreshness(undefined, undefined, now) === "untracked",
  "undefined lastSync + undefined schedule → untracked",
);
// "never" still fires when schedule IS declared (real problem)
assert(
  classifyFreshness(null, "0 * * * *", now) === "never",
  "null lastSync + present schedule → never (real problem)",
);

// eslint-disable-next-line no-console
console.log("freshness.test.ts: all assertions passed");
