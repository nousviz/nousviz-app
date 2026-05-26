# Changelog

All notable changes to NousViz will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). NousViz adheres to [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`.

## [Unreleased]

_Nothing yet — see [ROADMAP.md](ROADMAP.md) for what's planned._

---

## [1.0.2] — 2026-05-26

### Fixed — defence-in-depth against the v1.0.1 outage pattern

v1.0.1 fixed the one-line bug, but the *reason* a single backend 401 became
a multi-day team-wide outage was that three frontend layers happily amplified
it: `apiFetch` auto-logged-out on any 401, the plugin loader silently swallowed
errors, and the boot splash's timeout fallback dropped the user into a
permanently-broken dashboard. v1.0.2 closes each of those amplifiers.

- **`apiFetch` 401 auto-logout is now scoped to `/api/auth/me` and `/api/auth/me/permissions` only.** Previously, any 401 from any endpoint cleared the session token from `localStorage` and redirected to the login page. That meant a single bug on one endpoint could log out everyone on the platform. Now only the canonical session-check endpoints trigger the logout flow — a 401 from any other endpoint is returned to the caller as a normal response. A legitimately-expired session still gets caught on the next page-load `/api/auth/me` call. New unit test `apps/web/src/lib/api.test.ts` exercises the scoping.
- **The plugin-component loader now retries `/api/plugins` with exponential backoff (3 attempts, <2s total) before giving up.** Previously the loader had a single try-catch that silently `return`ed on any error — failure was indistinguishable from "no trusted plugins exist," and the dashboard fell through to a broken render with no signal that anything was wrong. On terminal failure, the loader now logs to the console and calls `notifyPluginLoaderFailed(reason)` so `AuthGate` can show the user a recoverable error screen instead.
- **New `LoadErrorScreen` replaces the "render anyway" fallback in `AuthGate`.** When the plugin loader hits terminal failure (or the 15-second splash timeout fires with the loader still failed), the user now sees a clear card with the failure reason and a one-click Reload button. The reload re-runs the loader in-app without a full page reload — a transient API hiccup recovers in two clicks instead of cascading into a refresh-and-relogin loop.
- **New `scripts/smoke-test-viewer.sh` exercises the user-visible path end-to-end after every deploy.** Logs in as a configured test-viewer account (`NOUSVIZ_SMOKE_VIEWER_EMAIL` + `_PASSWORD`), then verifies `/api/auth/me`, `/api/auth/me/permissions`, `/api/plugins`, and a plugin dashboard spec all return 2xx as a real viewer. Asserts the `/api/auth/me` response role is `viewer` (defends against accidentally pointing the smoke at an admin account). The v1.0.0 → v1.0.1 outage would have failed this smoke in <5 seconds.

---

## [1.0.1] — 2026-05-26

### Fixed

- **`GET /api/plugins` no longer returns 401 for unauthenticated callers on a public route.** The middleware whitelists `/api/plugins` (share-viewer loader, plugin-frontend-component bootstrap), but the handler bubbled up an `HTTPException(401)` from `get_me()` when applying the B305 per-user plugin allowlist filter, masquerading a public endpoint as auth-required. The handler now tolerates a 401 from `get_me` and returns the unfiltered list — the correct semantics for an unauthenticated caller on a public route. Non-401 `HTTPException`s still propagate. Regression test in `tests/test_list_plugins_public_no_token.py`.

---

## [1.0.0] — 2026-05-18

First public release.

NousViz is a self-hosted, open-source data intelligence platform. Browse any data source through the Data Explorer, build dashboards on top of it, get alerted when the numbers move — all through a plugin ecosystem. Runs natively on Postgres. No Docker required.

### Platform

- **Data Explorer** — Three-level drilldown: Connection → Table → Row. Sort, filter, paginate. Save any view as a dashboard widget. Cross-plugin combine happens inside the Data Explorer authoring flow.
- **Dashboard builder** — Free-form grid with drag-to-resize, inline heading and text edits. Composes plugin-rendered widgets and operator-built widgets on the same canvas. Three rendering modes for operator-built widgets: Table, KPI, Metric.
- **Multi-user accounts** — Per-user email + bcrypt-hashed password, 4-role RBAC (viewer / analyst / admin / superadmin), invite flow with optional SMTP-delivered invitation emails, browser-session and API-key auth methods, step-up auth on sensitive operations.
- **Alerts** — Threshold (drop / rise / absolute) and zero-check alerts on any numeric metric. Email and webhook delivery. Trigger history with operator feedback (useful / neutral / useless).
- **Webhooks** — Inbound URLs for ingest; outbound POST for Slack, Discord, PagerDuty, or any arbitrary endpoint. Typed Slack templates plus generic JSON POST.
- **Annotations** — Tag events across datasets with category, severity, sources, and pinning. Time-range annotations overlay on dashboards. Undo history for every edit.
- **Shared links** — Password-protected public views of any dashboard or widget. Bcrypt-hashed share passwords, optional expiry, access log.
- **AES-256-GCM credential encryption** — Plugin credentials encrypted at rest with the operator-supplied `NOUSVIZ_ENCRYPTION_KEY`. Brokered to plugin subprocesses via single-use tokens — the encryption key never enters a plugin process.
- **MCP server** — AI agents can query installed plugins and connections via FastMCP.

### Plugin ecosystem

- **Plugin marketplace** — Browse, install, update, and uninstall plugins from a built-in marketplace. Three-tier source resolution: official (clones from `github.com/nousviz/plugin-{slug}`), community (third-party manifests with `repository_url`), and private (operator-provided repository URL).
- **Plugin SDK** — `pip install nousviz-sdk` for plugin authors. Stable contract for manifests, hooks, sync scripts, dataport metadata, dashboards, and alerts. Starter template at [`sdk/examples/starter-plugin/`](sdk/examples/starter-plugin/).
- **Plugin manifest** — YAML-declared. Manifest fields cover identity, navigation, dashboards, alerts, datasets, connections, sync schedule, and storage requirements.
- **Per-plugin Postgres role** — Each plugin gets a dedicated `nousviz_plugin_{slug}` Postgres role with permissions scoped to its declared tables. Plugins cannot read other plugins' tables directly; cross-plugin combine happens in the Data Explorer.
- **Plugin install security** — Commit-SHA pinning (no HEAD installs), `repository_url` validated against an SSRF blocklist, rate-limited install endpoint, isolated pip environments, sanitised subprocess environment (no `NOUSVIZ_*` vars leak to plugin code).
- **OAuth callback router** — Core owns the OAuth callback path for plugins that need third-party OAuth (no per-plugin OAuth domain registration).
- **Generated API clients** — Python (`packages/client-py`) and TypeScript (`packages/client-ts`) clients are generated from the OpenAPI spec and shipped in this repo.

### Bundled utility plugins

- **ClickHouse** — Column-oriented analytics database for plugins that need it. Marketplace-installable.
- **MySQL** — Shared MySQL connection for plugins that sync from MySQL sources.
- **Webhooks** — Inbound data ingestion + outbound alert delivery.

### Operator surfaces

- **Native install** — `scripts/setup.sh` provisions Postgres + Node + nginx on macOS / Debian / Ubuntu / RHEL / Fedora / Arch / WSL2. `--server` mode finishes the nginx site end-to-end. `scripts/ssl-setup.sh` adds Let's Encrypt HTTPS once DNS is pointed.
- **Push-deploy** — `scripts/deploy-local.sh` builds the frontend locally and rsyncs to a remote box. For low-RAM servers where the on-server build is OOM-killed.
- **Operator recovery** — `scripts/reset-password.sh` for lost-superadmin recovery when SMTP isn't configured. Writes a new bcrypt hash via parameterized SQL, kills active sessions, audits the reset.
- **Admin CLI** — Web-based terminal for superadmins (user management, health checks, migrations, log tail).
- **SMTP** — Branded email templates for invites, alerts, password resets.
- **Health monitoring** — System health checks with email alerts on state transitions.
- **Dark mode** — Multiple themes including a sovereign dark variant.

### Compatibility and prerequisites

- Python 3.10 – 3.12 (3.13+ not yet supported)
- Node.js 18+
- PostgreSQL 14+ (installed automatically by `scripts/setup.sh`)
- 2 GB RAM recommended for on-server builds

### License

- Core under the [Sustainable Use License](LICENSE) — free to self-host and modify.
- SDK, examples, bundled utility plugins, and community plugins under MIT.

[Unreleased]: https://github.com/nousviz/nousviz-app/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/nousviz/nousviz-app/releases/tag/v1.0.0
