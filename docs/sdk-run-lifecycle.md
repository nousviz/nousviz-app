# SDK run lifecycle: who creates the `job_runs` row?

**Status:** stable as of v0.9.11.22 (B282).

NousViz tracks every sync invocation as a row in the `job_runs` table. Two
parts of the platform can create that row, and they must not both create
one for the same invocation. This doc spells out the contract so the next
person extending the SDK doesn't re-introduce the duplicate-insert bug
that B282 fixed.

## The two paths

### 1. Async / scheduled / queued (the production path)

```
                 INSERT (status='queued',
                         source='cron',
                         details={cron_source, scheduler_id, ...})
scheduler ───────► job_runs row N
                         │
                         │ UPDATE (status='running',
                         │         claimed_by=<worker>,
                         │         claimed_at=now())
worker ─────────► claims row N
                         │
                         │ subprocess.Popen(env={
                         │   NOUSVIZ_JOB_RUN_ID: "N",
                         │   NOUSVIZ_PLUGIN_ID:  "...",
                         │   ...
                         │ })
sync child ─────► reads NOUSVIZ_JOB_RUN_ID=N from env
                         │
                         │ self._run_id = N
                         │ (no INSERT — adopt the worker-claimed row)
SDK (BaseSync.main()) ──► _complete_run() UPDATEs row N
```

The scheduler creates the row, the worker claims it, the SDK adopts the
existing row id from the env var. Exactly one row per invocation.

### 2. Standalone / dev / direct-invocation (the local path)

```
$ python plugins/installed/my-plugin/src/sync.py --source=manual
                         │
                         │ no NOUSVIZ_JOB_RUN_ID in env
                         ▼
SDK (BaseSync.main()) ──► _start_run() INSERTs a fresh row
                         │   (status='running', source=<arg>)
                         │
                         │ self._run_id = new id
                         │ ...sync runs...
                         │
                         │ _complete_run() UPDATEs the row it created
```

When invoked directly (developer running a sync by hand, CI testing a
plugin in isolation, scripted backfill outside the worker queue), there
is no inherited run id — the SDK creates one itself.

## The contract (from the SDK side)

`BaseSyncScript._start_run()` (in `sdk/nousviz_sdk/sync.py`):

1. Read `os.environ.get("NOUSVIZ_JOB_RUN_ID", "").strip()`.
2. If non-empty and parses as `int`: set `self._run_id = int(...)`,
   log `"Adopted worker-claimed run N"` at INFO, return without
   inserting.
3. If non-empty but malformed: log a WARNING, fall through to step 4.
4. Insert a fresh `job_runs` row, populate `self._run_id` from the
   `RETURNING id`. (This is the standalone path.)

Other SDK helpers (`nousviz_sdk.jobs`, `nousviz_sdk.hooks`,
`nousviz_sdk.logging`) read the same env var as their authoritative
source for the current run id. `_start_run()` is the only one that
also has an INSERT fallback because `main()` runs before any other
helper has a chance to fail.

## The contract (from the worker side)

`apps/worker/src/run_jobs.py` sets `NOUSVIZ_JOB_RUN_ID` in the child
env before `subprocess.Popen` (currently around line 579). It also
sets `NOUSVIZ_PLUGIN_ID` and the broker socket / token. **Do not
remove `NOUSVIZ_JOB_RUN_ID` from the worker spawn env without also
removing the SDK's adoption branch — losing one without the other
returns the duplication.**

## What pre-B282 looked like

Before v0.9.11.22, `_start_run()` always INSERTed. The result:
every cron sync produced two rows in `job_runs` — one from the
scheduler (`details={...}`, `claimed_by` set) and one from the SDK
(`details='{}'::jsonb`, `claimed_by` NULL). Both completed
independently with the same final status, doubling retention growth
and confusing the failure-rate denominator on `/system/jobs`. See
`todo/0.9.11/tickets/B282-sdk-double-insert-job-runs.md` for the
full investigation.

## Adding a new SDK helper

If you add a new SDK helper that needs the current run id, read it
from `nousviz_sdk.jobs.get_current_run_id()` (which already handles
the in-process and env-var sources). Don't re-implement the env-var
read in the new helper — drift between readers is how this bug
happened in the first place.

## References

- `sdk/nousviz_sdk/sync.py:131` — `_start_run()` adoption logic
- `apps/worker/src/run_jobs.py:579` — worker-side env-var set
- `storage/postgres/migrations/068_b282_dedup_orphan_sdk_run_rows.sql` — historical-orphan cleanup
- `tests/test_sync_pipeline.py::test_b282_*` — regression tests
