# NousViz SDK Reference

The NousViz SDK (`nousviz_sdk`) is the Python package plugin authors
import to interact with the host platform. It wraps the broker protocol
(credentials, DB connections), provides job-runtime helpers
(progress reporting, cancellation), and exposes a logging surface that
lands in `/system/logs`.

This page documents the public symbols. Internal helpers (anything
prefixed `_`) are not part of the contract.

> **SDK version**: 0.6.3 (ships in NousViz core via `pip install -e sdk/`).
> Symbols here are stable across patch releases of NousViz. Breaking
> changes increment the SDK minor version and ship a migration note in
> the CHANGELOG.

---

## Database

### `nousviz_sdk.get_pg_conn()`

Open a Postgres connection scoped to the calling plugin's role.

```python
from nousviz_sdk import get_pg_conn

with get_pg_conn() as conn:
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM my_plugin_table")
    (count,) = cur.fetchone()
```

The connection is brokered — the SDK reads `NOUSVIZ_PLUGIN_ID` from
the environment and asks the host for credentials. Plugins do **not**
embed Postgres credentials.

The role is `nousviz_plugin` (in core deployments). It has GRANT on
the plugin's declared tables and read on `app_logs`. Attempting to
read `users`, `credentials`, or other host tables returns
`InsufficientPrivilege`.

### `nousviz_sdk.dict_cursor(conn)` → `DictCursor`

Convenience wrapper that returns rows as dicts.

```python
with get_pg_conn() as conn:
    cur = dict_cursor(conn)
    cur.execute("SELECT id, label FROM my_table LIMIT 5")
    for row in cur.fetchall():
        print(row["label"])
```

### `nousviz_sdk.DictCursor`

Type used by `dict_cursor`. Behaves like `psycopg2.extras.RealDictCursor`
but with the plugin-broker connection lifecycle.

---

## Credentials

### `nousviz_sdk.get_credential(plugin_id, key, env_prefix=None) -> str | None`

Fetch a stored credential for the given plugin. Credentials are
encrypted at rest with `NOUSVIZ_ENCRYPTION_KEY`; the SDK only sees the
plaintext for the duration of the call.

```python
from nousviz_sdk import get_credential

api_key = get_credential("my-plugin", "api_key", env_prefix="MY_PLUGIN_")
if not api_key:
    raise RuntimeError("No api_key configured — set it in /plugin/my-plugin/settings")
```

### `nousviz_sdk.CredentialBrokerUnavailable`

Raised when the credential broker socket is missing — happens in test
contexts where the host process isn't running. Plugin code should
catch it and either skip the credentialed path or fall back to a
test-mode environment variable.

### `nousviz_sdk.CredentialBrokerError`

Raised when the broker accepts the request but reports an error
(unknown key, unauthorized plugin, etc.). The exception message is
operator-facing.

---

## Settings

### `nousviz_sdk.get_setting(plugin_id, key, default=None) -> Any`

Read a non-secret setting from `plugin_settings`. JSONB-typed; returns
the parsed Python value.

### `nousviz_sdk.set_setting(plugin_id, key, value) -> None`

Upsert a non-secret setting. Plugins typically don't write settings —
that's the operator's job from `/plugin/<slug>/settings`. The setter
exists for plugin-internal state (last-cursor, last-import-id, etc.).

### `nousviz_sdk.get_connection_field(plugin_id, field_name, default=None) -> Any`

Read a non-secret field from the plugin's connection block (B130).
Pre-v0.8.6.5 plugins read these via env vars; that path is gone —
use this helper instead.

```python
from nousviz_sdk import get_connection_field

base_url = get_connection_field("my-plugin", "base_url", default="https://api.example.com")
```

---

## Sync jobs

### `nousviz_sdk.BaseSyncScript`

Subclass this to write a sync script. The host invokes the subclass's
`main()` method; the base class handles broker setup, cancellation
checks, and final job-run row update.

```python
from nousviz_sdk.sync import BaseSyncScript
from nousviz_sdk import progress

class MySync(BaseSyncScript):
    def main(self):
        rows_total = 1000
        for i, row in enumerate(self.fetch_rows()):
            self.check_cancelled()
            self.upsert(row)
            if i % 100 == 0:
                progress.report(percent=i / rows_total, message=f"row {i}/{rows_total}")

if __name__ == "__main__":
    MySync().run()
```

### `nousviz_sdk.progress.report(percent=None, message=None, **extra)`

Live progress to the unified Sync card. Writes
`job_runs.progress` JSONB; the frontend polls this via
`GET /api/plugins/{id}/sync/status` and shows the bar.

`percent` should be 0.0–1.0. `extra` keys land in the JSONB blob and
are surfaced in the UI's progress detail.

### `nousviz_sdk.jobs.heartbeat(progress=None) -> None`

Lower-level than `progress.report` — updates `job_runs.heartbeat_at`
plus optional progress dict. Use when you want to signal the worker is
alive without changing the progress bar.

### `nousviz_sdk.jobs.check_cancelled() -> bool`

Returns True iff the operator has clicked "Cancel" on the Sync card.
Long-running sync loops should call this every iteration so cancels
are cooperative, not waited-on-timeout.

### `nousviz_sdk.jobs.get_run_id() -> int | None`

The current `job_runs.id`. Useful if your plugin needs to log
events that reference back to the run row.

---

## Logging

### `nousviz_sdk.log_event(level, source, message, detail=None, run_id=None)`

Structured logging into `app_logs`. Records appear in
`/system/logs?source=plugin` (or whatever `source` you pass).

```python
from nousviz_sdk import log_event

log_event(
    level="info",
    source="plugin",
    message="Imported 1234 records",
    detail={"plugin_id": "my-plugin", "imported": 1234},
)
```

When called from a worker subprocess (env `NOUSVIZ_PLUGIN_ID` is set),
the SDK writes directly to `app_logs` via the broker-resolved
`get_pg_conn()` — see B238 (v0.9.10.1) for the contract.

`run_id` is auto-populated from `NOUSVIZ_JOB_RUN_ID` if the call
happens during a sync run; you only need to pass it explicitly when
calling from a non-sync context.

---

## Hooks

### `nousviz_sdk.HookContext`

Passed into hook handlers. Exposes `.plugin_id`, `.payload`, and
`.run_id`. Handlers should treat it as read-only.

### `nousviz_sdk.HookResult`

Return value for hook handlers. Set `.ok` and `.message` to control
how the hook outcome shows in `/system/logs`.

```python
from nousviz_sdk import HookContext, HookResult

def on_credentials_saved(ctx: HookContext) -> HookResult:
    fields = ctx.payload.get("fields", [])
    if "api_key" not in fields:
        return HookResult(ok=False, message="api_key not provided")
    # ... do work ...
    return HookResult(ok=True, message=f"Verified {len(fields)} fields")
```

Hooks are declared in `plugin.yaml` under `hooks.on_credentials_saved`,
`hooks.on_sync_complete`, etc.

---

## Routing

### `nousviz_sdk.router_for_plugin(plugin_id) -> APIRouter`

Returns a FastAPI `APIRouter` pre-mounted at `/api/plugins/<plugin_id>`.
Use this in `apps/api/src/routes.py` (your plugin's routes file):

```python
from nousviz_sdk import router_for_plugin, get_pg_conn

router = router_for_plugin("my-plugin")

@router.get("/data")
def get_data():
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM my_plugin_table LIMIT 10")
        return {"rows": cur.fetchall()}
```

Routes are auto-registered with the host RBAC at
`plugins.read` (GET) and `plugins.configure` (POST/PATCH/PUT/DELETE)
by default. Override via `register_route(...)` from the host's RBAC
module if your route needs different permissions.

---

## Schedule

### `nousviz_sdk.schedule.get_schedule(plugin_id) -> dict | None`

Returns the plugin's effective schedule:

```python
{
    "manifest_cron": "0 6 * * *",
    "override_cron": None,
    "effective_cron": "0 6 * * *",
    "next_fire_at": "2026-05-02T06:00:00Z",
}
```

Plugins rarely call this — the host UI surfaces it. Useful if your
plugin needs to reason about its own cadence.

---

## Testing

### `nousviz_sdk.testing` (B138)

Test harness for plugin-author tests. Stubs the broker, provides
in-memory `get_pg_conn()` against an ephemeral SQLite-or-Postgres,
captures `log_event` calls for assertion.

```python
from nousviz_sdk.testing import TestHarness

def test_my_plugin_sync():
    with TestHarness(plugin_id="my-plugin") as h:
        h.set_credential("api_key", "test-key")
        from my_plugin.sync import MySync
        MySync().run()
        assert "Imported" in h.captured_logs[0]["message"]
```

Full reference in `sdk/nousviz_sdk/testing/__init__.py`.

---

## Compatibility

- Pinned to `psycopg2-binary` (v2.9+).
- Python 3.10+ (uses `|` union syntax in some signatures).
- Type hints throughout — your editor's autocomplete should work.

## Where to file issues

- SDK contract bugs: `https://github.com/nousviz/nousviz-app/issues` with the
  `sdk` label.
- Plugin authoring questions: `docs/contributing-a-plugin.md`.

## See also

- [Contributing a Plugin](contributing-a-plugin.md) — full plugin
  authoring walkthrough.
- [Plugin Architecture](plugin-architecture.md) — how plugins fit into
  NousViz's runtime.
- [/docs/api](/docs/api) — interactive reference for the host API
  (the surface plugins extend, not the SDK itself).
