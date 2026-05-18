# Plugin sync scheduling

NousViz plugins fetch data from external sources via a `src/sync.py` script declared in their `plugin.yaml`. Installing a plugin does **not** automatically schedule its sync — you need one extra step: register the sync with your process manager.

Without this step, sync only runs when you click the **Sync** button in the UI. Dashboards backed by the plugin's tables will show stale data until you trigger a manual sync.

---

## PM2 (recommended)

NousViz ships with a PM2 ecosystem config at `ecosystem.config.js`. Add a block for each plugin you install.

### 1. Open `ecosystem.config.js`

Scroll to the section marked `── Plugin sync workers ──`. Add a new object inside the `apps` array:

```javascript
{
  name: "sync-<PLUGIN_ID>",
  cwd: APP_DIR,
  script: ".venv/bin/python3",
  args: "plugins/installed/<PLUGIN_ID>/src/sync.py",
  interpreter: "none",
  cron_restart: "<CRON_FROM_MANIFEST>",   // match plugin.yaml sync.schedule
  autorestart: false,                      // don't restart between cron runs
  log_date_format: "YYYY-MM-DD HH:mm:ss Z",
  error_file: `${APP_DIR}/logs/sync-<PLUGIN_ID>-error.log`,
  out_file: `${APP_DIR}/logs/sync-<PLUGIN_ID>-out.log`,
},
```

Replace:
- `<PLUGIN_ID>` with the plugin's slug (e.g. `starter-plugin`)
- `<CRON_FROM_MANIFEST>` with the `sync.schedule` value from the plugin's `plugin.yaml` (e.g. `"0 */4 * * *"` for every 4 hours)

### 2. Reload PM2

```bash
pm2 reload ecosystem.config.js --update-env
```

PM2 picks up the new worker without restarting the rest of the stack.

### 3. Verify

```bash
pm2 list
```

You should see `sync-<PLUGIN_ID>` with `status: online`.

In the NousViz UI, visit **Settings → Jobs** and refresh. The plugin's entry will now show `cron_active: true` and the "Not scheduled" warning will disappear.

After the next scheduled run, the `Last run` column populates with the actual run timestamp.

---

## System crontab (alternative)

If you're not using PM2, register the sync via your system crontab:

```bash
crontab -e
```

Add a line per plugin:

```
<CRON_SCHEDULE> cd /opt/nousviz && .venv/bin/python3 plugins/installed/<PLUGIN_ID>/src/sync.py >> logs/sync-<PLUGIN_ID>.log 2>&1
```

Replace `/opt/nousviz` with your install path if different. The `cd` is important — the sync script uses relative paths.

Verify:
```bash
crontab -l | grep nousviz
```

The NousViz jobs API picks up crontab entries automatically if they contain the string `nousviz`.

---

## Removing a plugin's sync schedule

When you uninstall a plugin:

- **PM2:** remove the corresponding block from `ecosystem.config.js`, then `pm2 delete sync-<PLUGIN_ID> && pm2 save`
- **crontab:** remove the line via `crontab -e`

Leaving stale entries running against an uninstalled plugin will fail (script not found) and clutter the logs.

---

## Why no auto-registration?

Automatic PM2 registration during plugin install is planned (tracked in follow-up work) but not shipped. Auto-editing `ecosystem.config.js` on every install has sharp edges — it fights the rsync-based deploy workflow, complicates uninstall cleanup, and needs careful error handling when the config is in an unexpected state. For now the manual step keeps control with the operator.

---

## Troubleshooting

### Plugin shows `Last run: Never` after I registered it

- Check `pm2 logs sync-<PLUGIN_ID>` for errors — often a credential or connection issue
- Confirm the plugin uses `BaseSyncScript` from the SDK. Plugins that write their own `plugin_settings._last_sync` row will still display correctly (the UI falls back to that key), but switching to `BaseSyncScript` gives you richer status (start/complete timestamps, duration, error text, full run history)
- If the plugin writes its own `job_runs` rows, confirm migration 041 is applied: `SELECT COUNT(*) FROM job_runs` should work without error

### Plugin shows `status: stale`

The jobs API marks a plugin as stale when the time since the last run exceeds 2× the declared schedule interval. Either:
- The sync is failing silently — check `pm2 logs sync-<PLUGIN_ID>`
- The cron schedule doesn't match the plugin manifest — re-check `cron_restart` in `ecosystem.config.js` against `sync.schedule` in the plugin's `plugin.yaml`
- PM2 isn't running — `pm2 status` / `pm2 resurrect`

### How do I trigger a manual sync?

Click **Sync** in the plugin's UI page, or hit the API directly:

```bash
curl -X POST http://localhost:8000/api/plugins/<PLUGIN_ID>/sync \
     -H "X-Session-Token: $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"mode":"incremental"}'
```

Modes: `incremental` (default), `full` (ignore incremental cutoff), `days` (with `days: N`).

Since v0.9.6.0 (B205) the endpoint is **always async**: it returns `{run_id, status: "queued"}` immediately and the worker runs the script. If a run is already in flight, the endpoint returns **HTTP 409** with `{run_id, status, already_running: true}` — re-poll `/api/plugins/<PLUGIN_ID>/sync/status` instead of triggering a second run.

## Live progress reporting (v0.9.6.0)

Plugin sync scripts can report progress so the unified Sync card on the plugin Settings tab and the `/system/jobs` row expansion render a live progress bar, message line, and elapsed time.

### Minimal example

```python
from nousviz_sdk import progress, jobs
from nousviz_sdk.sync import BaseSyncScript

class MySync(BaseSyncScript):
    plugin_id = "my-plugin"

    def run(self, since=None):
        total = self.api.count(self.jql)
        done = 0
        for batch in self.api.iter_pages(self.jql):
            if jobs.check_cancelled():
                self.logger.info("cancel requested — exiting cleanly")
                return
            for record in batch:
                self.upsert(record)
                done += 1
            progress.report(
                rows_done=done,
                rows_total=total,
                message=f"Fetching records {done}/{total}",
            )
```

### `progress.report()` API

```python
nousviz_sdk.progress.report(
    pct: float | None = None,
    message: str | None = None,
    rows_done: int | None = None,
    rows_total: int | None = None,
) -> None
```

All fields are optional. The UI renders:
- A **determinate** progress bar when `pct` is set, OR when both `rows_done` and `rows_total` are set (it computes the percentage).
- An **indeterminate** spinner otherwise — useful for steps where you can't predict total work (e.g. pagination through an opaque API).
- The `message` line below the bar.

Calls are throttled at 0.5s under the hood, so safe to call inside a tight loop. A bare `progress.report()` (no args) bumps the run's heartbeat without changing the displayed progress — useful for signaling liveness in long inner steps.

### Cancellation

Pair `progress.report()` with `jobs.check_cancelled()` between batches. When an operator clicks Cancel in the UI, the worker sets the run to `cancelling`; `check_cancelled()` returns `True` on the next call. Exit cleanly from `run()` — partial data is fine.

### Plugins that don't emit progress

Existing sync scripts continue to work without changes. The Sync card shows "Running…" + elapsed time + a heartbeat dot but no progress bar. Adopt the API incrementally — even one `progress.report(message=...)` call per batch is a meaningful improvement over silent waiting.
