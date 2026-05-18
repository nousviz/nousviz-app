# NousViz Plugin SDK

The `nousviz-sdk` package is the contract between a NousViz plugin and the platform. Plugins that import from `nousviz_sdk` are portable; plugins that reach into `apps.*` will break on any release.

See [`CHANGELOG.md`](CHANGELOG.md) for SDK release history. The SDK version is pinned in [`pyproject.toml`](pyproject.toml).

---

## SDK is the only contract

**Plugins MUST import only from `nousviz_sdk`.** Reaching into `apps.*` is unsupported and breaks on any core release.

| What you want | SDK path | Don't use |
|---------------|----------|-----------|
| DB connection (own tables + refs) | `from nousviz_sdk import get_pg_conn` | `from apps.api.src.db import get_pg_conn` |
| Dict-style cursor | `from nousviz_sdk import dict_cursor` | `from apps.api.src.db import dict_cursor` |
| Decrypted credentials | `from nousviz_sdk import get_credential` | Reading `os.environ` directly |
| Plugin settings (read/write) | `from nousviz_sdk.settings import get_setting, set_setting` | Direct DB queries on `plugin_settings` |
| Sync heartbeat / cancel | `from nousviz_sdk.jobs import heartbeat, check_cancelled, get_run_id` | Raw `job_runs` UPDATEs |
| BaseSyncScript | `from nousviz_sdk.sync import BaseSyncScript` | Custom sync boilerplate |
| Lifecycle hooks | `from nousviz_sdk.hooks import HookContext, HookResult` | — |
| FastAPI router | `from nousviz_sdk import router_for_plugin` | `fastapi.APIRouter()` without prefix |

Plugins that need something not in the SDK: open an issue. Core either exposes it through the SDK or explains why the plugin shouldn't need it.

---

## How the SDK is installed at runtime (v0.9.0)

The SDK is editable-installed into the NousViz API and worker venvs by `scripts/setup.sh`:

```
pip install -e ./sdk
```

That line is in `apps/api/requirements.txt`. Running `setup.sh` installs it; the `/api/health` endpoint reports its availability. If `nousviz_sdk` isn't importable at API startup, the plugin install endpoint returns HTTP 503 with a remediation message, and every plugin's `load_status` shows `routes_registered: false`.

For standalone use (dev against a plugin without running the full stack), install from the SDK directory:

```bash
cd /path/to/nousviz
pip install -e ./sdk
```

Plugins can declare `nousviz-sdk>=1.0,<2.0` in their own `requirements.txt` — the SDK is published to PyPI on every tagged release of NousViz.

---

## Credential delivery (v0.9.0 / P208)

**Decrypted credentials never enter subprocess `os.environ`.** The NousViz jobs-worker runs a Unix socket credential broker. Each subprocess is spawned with a one-shot authentication token; on first `get_credential()` call, the SDK exchanges the token for the plugin's decrypted credentials, caches them in memory for the subprocess's lifetime, and moves on.

- The token is worthless after one use (cached response, subsequent calls hit memory)
- If a plugin tries to re-use a token, or another plugin tries to present it, the broker returns `DENIED`
- Without the broker env (`NOUSVIZ_CREDS_SOCKET` / `NOUSVIZ_CREDS_TOKEN` / `NOUSVIZ_PLUGIN_ID`), `get_credential()` raises `CredentialBrokerUnavailable` with a clear message

**What's in subprocess env:**
- Non-secret connection fields (host, port, database name, etc.)
- `NOUSVIZ_PLUGIN_ID`, `NOUSVIZ_JOB_RUN_ID` (identity/context)
- `NOUSVIZ_CREDS_SOCKET` / `NOUSVIZ_CREDS_TOKEN` (single-use, expires 30s)
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` (not secret)
- Standard system vars (PATH, HOME, LANG)

**What's NOT in subprocess env:**
- Plugin credentials (password, api_token, PEM, etc.) — fetched via broker
- `NOUSVIZ_ENCRYPTION_KEY` — stays in the API/worker processes only
- `POSTGRES_PASSWORD` — core's high-privilege role password
- `NOUSVIZ_PLUGIN_PASSWORD` — delivered via broker's `__db__` key on demand
- `GITHUB_TOKEN` and other operator secrets

---

## Database privileges (v0.9.0 / P203)

Plugin subprocesses connect to Postgres as a dedicated `nousviz_plugin` role (migration 047), not as the high-privilege `nousviz` role. The `nousviz_plugin` role has:

| Table / operation | Plugin access |
|-------------------|---------------|
| Own plugin's declared tables | full CRUD (granted at install time) |
| `schema_migrations`, `plugin_registry`, `plugin_modules` | SELECT only |
| `job_runs` | INSERT, SELECT, UPDATE (for heartbeats) |
| `app_logs` | INSERT only |
| `plugin_settings` | SELECT, INSERT, UPDATE, DELETE |
| `credentials`, `credential_audit_log` | **NO ACCESS** |
| `users`, `user_accounts`, `user_sessions` | **NO ACCESS** |
| `api_keys`, `deploy_keys`, `plugin_audit_log` | **NO ACCESS** |
| Other plugins' tables | **NO ACCESS** |

A plugin that tries `SELECT * FROM credentials` gets `permission denied for table credentials` from Postgres. This is the OS-level firewall. Plugin authors get credentials via `get_credential()` (broker) and DB access via `get_pg_conn()` (scoped role).

**If you hit a `permission denied` you didn't expect:** re-check that your plugin declares the table in `databases.postgres.tables`, and that you're querying your own namespace. If your legitimate use case isn't covered by the matrix, open an issue.

---

## Quick start

```python
from nousviz_sdk import get_pg_conn, router_for_plugin, get_credential

router = router_for_plugin("my-plugin")

@router.get("/data")
def get_data():
    api_key = get_credential("my-plugin", "api_key")
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM my_plugin_items LIMIT 10")
        return {"rows": cur.fetchall()}
```

Put this in `plugins/installed/my-plugin/api/routes.py` and restart the API. The plugin loader picks it up automatically.

---

## Sync / background jobs

```python
from nousviz_sdk.sync import BaseSyncScript
from nousviz_sdk import get_pg_conn, get_credential

class MySync(BaseSyncScript):
    def run(self, since=None):
        api_key = get_credential("my-plugin", "api_key")
        # ... fetch data, insert rows ...
        self._rows_synced = 42

if __name__ == "__main__":
    MySync().main()
```

The jobs-worker spawns this script with a credential broker token and monitors heartbeats. Use `self.check_cancelled()` in long loops to respect operator-initiated cancels.

---

## Hooks

```yaml
# plugin.yaml
hooks:
  on_credentials_saved: hooks.lifecycle:on_saved
```

```python
# hooks/lifecycle.py  (at plugin root, NOT in src/)
from nousviz_sdk.hooks import HookContext, HookResult

def on_saved(ctx: HookContext) -> HookResult:
    # ctx.plugin_id, ctx.hook_name, ctx.payload
    # Credentials are fetched via get_credential() — not in ctx.
    return HookResult(ok=True, message="Credentials acknowledged")
```

Hooks run in a jobs-worker subprocess with the same broker-delivered credential flow as syncs. Failing hooks show in `/system/logs` under `source=hook_runner` when the module itself fails to import (wrong directory, typo) — you don't need to ssh to diagnose.

---

## Local development & testing (v0.9.2 / B138)

The credential broker makes plugin code that calls `get_credential()`
or `get_pg_conn()` impossible to run outside a NousViz-spawned subprocess
— there's no broker socket and no token. To write `pytest` tests against
your plugin, use the dev harness:

```python
from nousviz_sdk.testing import use_test_credentials

def test_my_plugin_sync():
    with use_test_credentials({
        "host": "localhost",
        "port": 5432,
        "database": "test",
        "username": "test",
        "password": "test",
    }):
        from my_plugin.src import sync
        result = sync.run()
        assert result.ok
```

`use_test_credentials()` registers a stub resolver. Inside the `with` block:

- `get_credential(plugin_id, key)` returns the matching value
- `get_pg_conn()` works if you supplied a `__db__` block (or use the
  default from `fake_db_credentials()`)
- The cache and resolver are reset on exit, so tests don't leak state

`reset_sdk_state()` is also exported if you need a fresh start without
the context manager (e.g., a pytest fixture finalizer).

What this does NOT do:

- DB: `get_pg_conn()` connects to whatever Postgres your env points at.
  Use a test DB or fixture.
- HTTP: pair with FastAPI's `TestClient`.
- Subprocess paths: this runs in-process. For the real subprocess path
  (broker token + Unix socket), use NousViz's own integration tests as
  a reference.

---

## Logging structured events (v0.9.2 / B140)

`nousviz_sdk.logging.log_event(level, message, detail=...)` lets your
plugin emit structured entries that land in `/system/logs` with your
plugin's source tag.

```python
from nousviz_sdk.logging import log_event

log_event("error", "Failed to sync customer data",
          detail={"customer_id": 12345, "retry_count": 3})
```

Levels: `info`, `warn`, `error`. In a test harness (no
`NOUSVIZ_PLUGIN_ID` env), it falls back to stderr — no exception, no
DB write. So your tests don't need to mock the logger.

---

## Frontend components (v0.9.4+)

Plugins can ship custom React widgets in their own repo. Operators consent at install time; NousViz dynamically imports the bundle and registers the component into the same registry the YAML `type: custom, component: <Name>` panels resolve against.

### Manifest

```yaml
frontend:
  components:
    - name: MyWidget
      path: widget/dist/MyWidget.js
```

`name` must be PascalCase. `path` must be relative, end in `.js`, and must NOT contain `..`. The widget-serve endpoint refuses requests for filenames not declared in the manifest.

### Build

Plugin author owns the build pipeline. **Use `--alias:react=/api/widget-runtime/react.js` and the matching jsx-runtime alias** so your widget imports the host's React at runtime instead of bundling its own:

```bash
esbuild widget/MyWidget.tsx \
  --bundle \
  --format=esm \
  --jsx=automatic \
  --target=es2020 \
  --alias:react=/api/widget-runtime/react.js \
  --alias:react/jsx-runtime=/api/widget-runtime/react-jsx-runtime.js \
  --external:/api/widget-runtime/react.js \
  --external:/api/widget-runtime/react-jsx-runtime.js \
  --outfile=widget/dist/MyWidget.js
```

Both `--alias` AND `--external` are required. `--alias` rewrites the bare specifier (`"react"` → `"/api/widget-runtime/react.js"`); `--external` then prevents esbuild from trying to resolve that resulting URL on disk and instead leaves it as an `import` statement in the bundle, which the browser resolves at runtime against the host. Without `--external`, esbuild fails with `Could not resolve "/api/widget-runtime/react.js"`.

The aliases route `import { useState } from "react"` through host-served shim files at known stable URLs. The shims re-export the host's React copy, so all hooks share the same `ReactCurrentDispatcher` and your widget's `useState`/`useEffect` work correctly.

Bundle size is small (~3-10KB depending on what else you import) because React isn't inlined.

Commit the bundled `widget/dist/*.js` files to your plugin repo.

### Why aliases not bundling (B156)

Earlier guidance (v0.9.4.5) recommended bundling React into each widget. **That was wrong.** Widgets using hooks crashed with `TypeError: Cannot read properties of null (reading 'useState')` at first render — the well-known React-18 dual-instance bug, where the widget's bundled React's `useState` looks up dispatcher state in its own React copy, which is null because the host's React is the one actively rendering.

v0.9.4.7 fixes this by serving a tiny React shim at `/api/widget-runtime/react.js` (and `/react-jsx-runtime.js`) that re-exports `window.NousViz.React.*` — the same React the host uses. Plugins build with `--alias:react=<that URL>` so their bare `import "react"` resolves to the shim, which forwards to the host's React. One React copy in play, hooks work.

The aliases are stable URLs maintained by core. They're public-readable (no auth required, since `import(url)` doesn't carry session tokens). Plugins don't bundle React at all.

Externalising React without these aliases (the historical pre-v0.9.4.7 builds) still fails — `import "react"` is a bare specifier the browser can't resolve without an importmap. The aliases ARE the alternative to importmap.

### Component shape

Each widget receives `CustomWidgetProps`:

```tsx
/// <reference path="./nousviz_widget_types.d.ts" />
import { useState, useEffect } from "react";

export default function MyWidget({ pluginId, config }: CustomWidgetProps) {
  const [data, setData] = useState<unknown>(null);
  useEffect(() => {
    window.NousViz.widgets
      .apiFetch(`/api/plugins/${pluginId}/some-endpoint`)
      .then(r => r.json())
      .then(setData);
  }, [pluginId]);
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      {JSON.stringify(data)}
    </div>
  );
}
```

Copy `sdk/widget-types/nousviz_widget_types.d.ts` from the NousViz repo into your plugin's repo for the `CustomWidgetProps` and `window.NousViz.widgets` types.

### Host SDK (`window.NousViz.widgets`)

Published at runtime by NousViz core before any plugin widget mounts. Stable from v0.9.4.1; semver applies.

| Helper | Use |
|--------|-----|
| `apiFetch(input, init?)` | Authenticated fetch (adds session token) |
| `formatRelativeTime(iso)` | "2 hours ago" / "in 5 minutes" |
| `formatAbsoluteTime(iso)` | "2026-04-25, 14:00:00 UTC" |
| `formatNumber(n)` | "1,234,567" |
| `formatBytes(n)` | "1.4 MB" |
| `cn(...inputs)` | Tailwind class-name merger |

Other libs (recharts, lucide-react, custom helpers): bundle into your plugin's `.js`.

### Tailwind classes

Plugin widgets share the host's Tailwind config. Common utilities (`bg-card`, `text-foreground`, `bg-emerald-500/10`, etc.) work without setup.

**Constraint:** Tailwind processes class strings at the host's build time, not at install. Exotic utilities the host has never used may be missing from the host's pre-built CSS. Stick to utilities the host's own widgets use (browse `apps/web/src/widgets/`), or use inline `style={{...}}` for arbitrary colors/spacing. The host's `tailwind.config.ts` does scan plugin widget dirs, so an operator who runs a full `setup.sh` after installing a plugin will pick up plugin-specific classes.

### Operator workflow (one-time per plugin install/update)

1. Install or Update plugin via marketplace
2. Plugin page banner: "This plugin includes custom frontend code"
3. Click **Trust this plugin**
4. Hard-refresh browser
5. Custom widgets render

Operators revoke trust via Settings → Plugins → "Revoke trust".

### Trust model

Plugin frontend code runs **with the same privileges as the host application**. Same model as Home Assistant integrations, Grafana plugins, Jenkins plugins. v1.0 will introduce iframe-sandboxed execution for untrusted public-marketplace sources.

### Frontend widget failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Widget renders but classes don't style | Utility missing from host's CSS | Use a class the host already uses, or operator rebuilds host frontend |
| `Cannot read properties of undefined (reading 'apiFetch')` | Widget evaluated before host SDK published | Should not happen; file a bug if it does |
| `Failed to resolve module specifier "react"` | Build didn't alias `react` to the host shim | Rebuild with `--alias:react=/api/widget-runtime/react.js --alias:react/jsx-runtime=/api/widget-runtime/react-jsx-runtime.js` plus matching `--external:/api/widget-runtime/...` flags (see Build above) |
| `Could not resolve "/api/widget-runtime/react.js"` (esbuild) | Used `--alias` without matching `--external` | Add `--external:/api/widget-runtime/react.js --external:/api/widget-runtime/react-jsx-runtime.js` to the build command |
| `Cannot read properties of null (reading 'useState')` (B156) | Pre-v0.9.4.7 build that bundled React in (dual-instance hooks bug) | Rebuild with the aliases above; do NOT bundle React |
| `React is not defined` | Build target too old or `--jsx` mode wrong | Use `--jsx=automatic --target=es2020` |
| "did not export a default React component" | Missing `export default` | End your widget file with `export default function ...` |
| Banner says trusted but widget doesn't render | Cached old bundle | Hard-refresh (Cmd-Shift-R) |

---

## Failure modes to expect (Python SDK)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: nousviz_sdk` | SDK not installed in the venv | Run `pip install -e ./sdk` in the API/worker venv. `scripts/setup.sh` does this. |
| `CredentialBrokerUnavailable` | Running outside a NousViz subprocess | Use `nousviz_sdk.testing.use_test_credentials` for local tests. |
| `CredentialBrokerError: denied` | Token consumed or expired | SDK caches after first fetch — this shouldn't happen in normal plugin code. |
| `permission denied for table X` | Plugin accessing a table outside its grants | Check your manifest's `databases.postgres.tables` — add the table if it's yours, or stop accessing it if it's core. |
| `load_status.routes_registered: false` | Plugin's routes.py failed to import | Check `/system/logs` filtered by your plugin id. |

---

## Further reading

- Full plugin architecture: `docs/plugin-architecture.md`
- Security model: `docs/security-model.md`
- Writing a plugin end-to-end: `docs/contributing-a-plugin.md`
