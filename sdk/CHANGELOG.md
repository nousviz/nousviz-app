# nousviz-sdk Changelog

The `nousviz-sdk` package is versioned in lockstep with NousViz core for v1.0. See the [main CHANGELOG](../CHANGELOG.md) for the full release story.

## [1.0.0] — 2026-05-18

First public release of the Plugin SDK.

Stable contract for plugin authors. Anything imported from `nousviz_sdk` is supported across the v1.x line.

### Exposed surface

- `nousviz_sdk.get_pg_conn` / `dict_cursor` — Postgres connection with per-plugin role permissions
- `nousviz_sdk.get_credential` — fetch encrypted plugin credentials via the credential broker
- `nousviz_sdk.settings.get_setting` / `set_setting` — per-plugin operator settings
- `nousviz_sdk.jobs.heartbeat` / `check_cancelled` / `get_run_id` — sync-job lifecycle
- `nousviz_sdk.sync.BaseSyncScript` — opinionated sync-script base class
- `nousviz_sdk.hooks.HookContext` / `HookResult` — install / uninstall / update lifecycle hooks
- `nousviz_sdk.router_for_plugin` — FastAPI router factory with the correct `/api/plugins/{slug}` prefix
- `nousviz_sdk.log_event` — structured log emitter visible in the operator's Logs page

### Contract

- Plugins **must** import only from `nousviz_sdk`. Anything under `apps.*` is internal.
- Plugins **must not** read other plugins' tables directly — cross-plugin combine happens in the operator's Data Explorer.
- Plugin subprocesses receive a sanitised environment — no `NOUSVIZ_*` variables, no operator secrets.
- Plugin credentials are delivered via single-use broker tokens; the encryption key never enters a plugin process.
