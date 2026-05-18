-- Migration 075: B305 (v0.10.0.6) — invite-time plugin allowlist.
--
-- Adds user_invites.plugin_access_pending JSONB to carry the
-- invite-time plugin picker selection until the invitee accepts.
-- Shape stored when non-null:
--   {"mode": "specific", "plugin_ids": ["alerts", "webhooks"]}
-- mode='all' is represented by NULL (no row of data → no restriction),
-- so the column stays NULL for the existing flow where operators don't
-- pick plugins.
--
-- At invite acceptance, the register flow in apps/api/src/routes/auth.py
-- reads this column and, if non-null with mode='specific', writes
-- resource_acls rows in the same transaction that creates the user
-- (resource_type='plugin', principal_kind='user', principal_id=<uuid>,
-- permission='plugins.read'). After acceptance the invite row is
-- marked used_at and the column rides along — no separate cleanup
-- needed because the column is part of the soft-deleted invite row.
--
-- Additive, no backfill, no FK. Down-migration drops the column.

ALTER TABLE user_invites
    ADD COLUMN IF NOT EXISTS plugin_access_pending JSONB;
