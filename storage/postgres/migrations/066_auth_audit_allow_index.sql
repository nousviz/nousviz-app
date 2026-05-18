-- Migration 066: B272/B273 follow-up (v0.9.11.19.2) — partial index
-- on auth_audit for the dominant decision='allow' query path.
--
-- The 2026-05-04 diagnostic engine flagged auth_audit at 27% sequential
-- scan rate. Code analysis (apps/api/src/routes/system.py) showed three
-- query patterns dominate:
--
--   1. _last_accessed_per_route — WHERE decision='allow' AND
--      permission NOT LIKE '_role.%' AND occurred_at > now() - 30 days
--      GROUP BY route_method, route_path, user_role
--
--   2. _audit_summary — same shape, hourly window, used by /system/permissions
--
--   3. users-with-permissions LATERAL — already served by
--      auth_audit_user_idx (user_id, occurred_at DESC)
--
-- Existing indexes on auth_audit:
--   - auth_audit_occurred_at_idx (occurred_at DESC)
--   - auth_audit_user_idx (user_id, occurred_at DESC)
--   - auth_audit_mismatch_idx (occurred_at DESC) WHERE decision='shadow_mismatch'
--
-- The partial index below targets queries 1 and 2 directly. With
-- decision='allow' the dominant filter (a vast majority of audit
-- rows are allows on a healthy system), a partial index on that
-- subset gives the planner a tight ordered set without scanning the
-- 'deny' / 'shadow_mismatch' rows that aren't the predicate target.
--
-- Plain CREATE INDEX (not CONCURRENTLY) since auth_audit is small
-- (~19 MB / 53k rows on production today); the brief lock is
-- negligible for an append-only audit table.

CREATE INDEX IF NOT EXISTS auth_audit_allow_occurred_at_idx
    ON auth_audit (occurred_at DESC)
    WHERE decision = 'allow';
