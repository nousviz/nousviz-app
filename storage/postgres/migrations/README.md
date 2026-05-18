# Migrations

This directory holds the platform's Postgres schema as a sequence of
forward-only migrations. The migration runner in
[scripts/setup.sh](../../../scripts/setup.sh) applies them in
lexicographic order on every fresh install and on every deploy that
adds new files.

## Forward migrations

`NNN_<name>.sql` — runs once per database. Idempotent (uses `CREATE … IF
NOT EXISTS`, `IF EXISTS` guards, etc.) so re-runs are safe in case the
runner is interrupted mid-pass.

## Rollback files

`NNN_<name>_down.sql` — **manual rollback procedures only. Never run by
the forward migration runner.**

The runner (since v0.9.11.0) filters them out of its glob and
explicitly skips any `_down.sql` that slips through. To use one,
pipe it into psql by hand:

```bash
sudo -u postgres psql -d nousviz < storage/postgres/migrations/NNN_name_down.sql
```

## A note on `schema_migrations` history

Servers provisioned **before v0.9.11.0** (2026-05-02) have rows in
`schema_migrations` for `*_down.sql` files. This is a historical
artifact: the migration runner pre-v0.9.11.0 ran every `*.sql` file
including the rollback variants — see ticket B244 for the full
investigation.

The fix in v0.9.11.0 stops that going forward but does not modify
existing rows. The orphan `_down.sql` rows are inert:

- The runner's already-applied check still skips them.
- The new glob (`[0-9]*.sql` plus a `case` skip) doesn't pick them up.
- They're cosmetic noise in the ledger; nothing reads them.

If you want to clean them up on an existing server (optional):

```sql
DELETE FROM schema_migrations WHERE filename LIKE '%\_down.sql' ESCAPE '\';
```

This is safe because the rollback files are not real migrations and
their absence from `schema_migrations` does not cause anything to
re-run.

## Recovering from the pre-v0.9.11.0 install crash

If your install hit the v0.9.0 → v0.9.10.7 fresh-install bug — symptom
is `psycopg2.errors.UndefinedTable: relation "credentials" does not
exist` during phase [6/7] migrations on a brand-new install — the
recovery procedure is:

```bash
# 1. Wipe the partially-installed schema entirely.
sudo -u postgres dropdb nousviz
sudo -u postgres dropuser nousviz
sudo -u postgres dropuser nousviz_plugin
sudo -u postgres dropuser nousviz_query

# 2. Update to v0.9.11.0+ (which has the migration glob fix).
git pull && git checkout v0.9.11.0   # or any tag >= v0.9.11.0

# 3. Re-run setup.
sudo ./scripts/setup.sh --server
```

Production servers running v0.9.10.7 or earlier are NOT affected — they
were provisioned before the bug surfaced and their `schema_migrations`
ledger is paid forward. Only fresh installs hit this.

## Adding a new migration

1. Create `NNN_<feature>.sql` (forward) and optionally
   `NNN_<feature>_down.sql` (rollback).
2. Number sequentially — current highest is the latest in this directory.
3. The forward file MUST be idempotent (`CREATE TABLE IF NOT EXISTS`,
   etc.) so a partially-failed run can be re-tried.
4. Test on a fresh container: `dropdb nousviz; ./scripts/setup.sh` →
   no errors, all tables present.
5. CI's `clean-install` job verifies this on every PR — see
   `.github/workflows/ci.yml`.
