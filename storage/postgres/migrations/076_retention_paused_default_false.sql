-- Migration 076: v0.10.0.6.2 — retention policies ship enabled by default.
--
-- Phase 12 audit findings §I9 + Phase 14 P0.1 verification identified that
-- 7 of 9 retention policies were paused on the production install — not
-- because the operator paused them, but because migration 064 declared
--
--     paused BOOLEAN NOT NULL DEFAULT TRUE
--
-- so every new policy ships paused and must be explicitly unpaused. The
-- operator unpaused job_runs:* at install time and never the rest; result
-- was unbounded growth on auth_audit (51 MB), app_logs (25 MB), and other
-- log tables on every production install.
--
-- This migration flips the default for FUTURE inserts only. Existing
-- rows on long-lived installs keep their stored paused value — a separate
-- one-time SQL UPDATE handles the unpause on existing prod (operator-run
-- with backup verification; see evidence/p0.1-verdict.md for the SQL).
--
-- Forward-compatible: future code that inserts new policy rows will get
-- the correct unpaused default; explicit paused=true inserts still work.

ALTER TABLE system_retention_overrides
    ALTER COLUMN paused SET DEFAULT FALSE;

-- Surface the change in the comments so future readers know why.
COMMENT ON COLUMN system_retention_overrides.paused IS
    'Whether the retention policy is paused. Defaults to FALSE since '
    'migration 076 (v0.10.0.6.2) — previously TRUE, which caused new '
    'policies to ship paused and accumulate log tables forever.';
