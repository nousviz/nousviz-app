# Changelog

All notable changes to NousViz will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). NousViz adheres to [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`.

## [Unreleased]

_Nothing yet — see [ROADMAP.md](ROADMAP.md) for what's planned._

---

## [1.0.5] — 2026-10-06

### Fixed

- **Wide custom plugin widgets scroll instead of being cut off (B324).** A `type: custom` plugin widget whose root element was a plain `div` wrapping a table wider than the page forced its whole dashboard row out to the table's width. The content pane then clipped the extra columns, and the widget's own `overflow-x-auto` wrapper had nothing to scroll. Dashboard row tracks are now `minmax(0, Nfr)` instead of `Nfr`, so a widget can never widen its row and its scroll wrapper works as written. Column proportions are unchanged. On earlier versions, add `overflow-hidden` to the widget's root element. Reported by Darrell Helyar.
- **Public Repository installs send the repository URL (B325).** On the Install Plugin page, Public Repository mode dropped the URL from the install request, so a public plugin that is not in the official or community registry could not be installed. The URL is now sent in every mode. On earlier versions, use Private (Token) mode with a read-only token. Found and fixed by John Wright.
- **Plugin settings can be saved again after frontend trust is granted (B327).** Granting trust stores a core-owned key next to the plugin's settings. The settings form posted that key back and the server rejected the whole submission as an undeclared key, so from that moment the plugin's settings could not be saved. The settings endpoint no longer returns or accepts core-owned (underscore-prefixed) keys. Sync schedules and frontend trust have their own endpoints and are unaffected. Found and fixed by John Wright.
- **Updating a plugin now installs its `requirements.txt`.** Install has done this since B306; update did not, so an update that added or re-pinned a library shipped code that could not import it, and the failure only appeared later as an ImportError. The update now pip-installs the new requirements after the swap and before the API reload. As with install, a pip failure does not roll the update back: it is written to the plugin event log and reported as `deps_installed: false` in the update response, so the operator can fix the cause and update again.
- **Runtime dependency audit is clean again (B323).** `tailwindcss-animate`, a build-time Tailwind plugin, was listed as a runtime dependency and pulled Tailwind's build toolchain into the runtime audit, where two advisories (nanoid, braces) flagged it. It is now a dev dependency, like Tailwind itself. The built bundle is byte-identical. Both advisories remain visible in the dev-inclusive audit; braces has no patched release yet.

### Added

- **ML Runtime utility plugin.** Installs pinned open-source machine learning libraries — LightGBM 4.7.0, scikit-learn 1.9.1, numpy 2.5.3 — into the NousViz Python environment, so plugins that declare `requires: ml_runtime: true` can train and score models in their sync jobs on the install's own data. The install hook proves the libraries import (including LightGBM's OpenMP runtime) and prints the exact fix when they do not; the health check reports installed versions and drift from the pins. Operators have nothing extra to do on a standard Linux server. Libraries are shared with core and every plugin by design; see `plugins/utilities/ml-runtime/README.md` for the decision and upgrade procedure.

### Changed

- **Pull requests are checked for commits already on `main` (P211).** A pull request whose branch was cut from a rewritten or out-of-date copy of `main` now fails CI with a "rebase first" message instead of duplicating history when merged. `scripts/ci/check-pr-commits.sh` runs the same check locally. Dependabot now raises dependency and security updates as pull requests.

---

## [1.0.4] — 2026-09-14

### Changed

- **NousViz is now MIT licensed (B322).** The core moves from the Sustainable Use License to MIT — one licence for the whole public repository. You may self-host, modify, redistribute, embed, and offer NousViz as a hosted service; the only condition is that the copyright and permission notice stay with the code. The SDK, examples, bundled utility plugins and community plugins were already MIT. The `enterprise/` directory is a git submodule pointing at a private, separately licensed repository (the managed-edition add-on); its source is not in this repository or in any public build, and community installs never load it. README, CONTRIBUTING, DECISIONS, the glossary, the `/openapi.json` licence metadata and the web package manifest now say MIT.

### Fixed

- **Plugin installs: dependency installation is no longer silent, and a new plugin's routes are live without an API restart (B306).** A plugin's `requirements.txt` is pip-installed via `sys.executable` (always the running venv). The install response carries `deps_installed`, and success or failure is written to the plugin event log with the tail of pip's output — closing the silent-pip-failure gap noted in v1.0.3. After an install the API sends SIGHUP to the gunicorn master so sibling workers pick up the new routes; non-gunicorn parents are left alone. Recovered from production, where it had been running uncommitted.
- **`npm audit` high advisory cleared in `apps/web` runtime dependencies (B314).** PostCSS path-traversal (GHSA-r28c-9q8g-f849) and a react-router open-redirect moderate resolved by lockfile bumps within semver. Two moderates remain that need the react-router 7.x major (B316, open).
- **CI TypeScript check is green again.** `apps/web/src/lib/api.test.ts` (shipped in v1.0.2) imported vitest, which was never a dependency; the typecheck job had been red on every public run since v1.0.1 and the test had never executed. vitest + jsdom are now devDependencies with a minimal config, and all 17 tests run.

### Added

- **Edition switch (community by default) and the enterprise boundary (MC-201–MC-205).** `NOUSVIZ_EDITION` is read in one place (`apps/api/src/edition.py`); unset or unknown values mean community, the full self-hosted product. Core exposes four hook seams — user invite, plugin install, SMTP config, feature flag — with community no-op defaults; there is no entitlement logic in core. The managed-edition add-on lives in a private repository mounted as an unfetchable submodule pointer at `enterprise/`; it is imported only when the edition is `managed`, and a missing or broken add-on logs an error and the instance keeps community behaviour. CI now runs a public-build-clean job (no submodule, leak and import guards via `scripts/edition-guards.sh`) alongside the managed build. Self-hosters have nothing to do: leave `NOUSVIZ_EDITION` unset.
- **Entitlement contract schema and DRAFT tier fixtures (MC-001)** under `contracts/`, with schema and fixture tests. Tier numbers are placeholders pending pricing review; versioning is additive-only (see `contracts/README.md`).
- **`CONTRIBUTORS.md`** restores the attribution flattened by the v1.0 squash.
- **`scripts/audit_users.py`** — operator script recovered from production (see its docstring for usage).

---

## [1.0.3] — 2026-07-17

### Fixed

- **Fresh installs now include PyMySQL (`PyMySQL>=1.1.0,<2` in `apps/api/requirements.txt`).** `scripts/setup.sh` — the README server quickstart and the `install.sh` bootstrap both run it — installed only `apps/api/requirements.txt`, which never listed PyMySQL, while `cli.py` setup installed it explicitly. Result: on a setup.sh-installed host, core's own MySQL connection routes (`Test connection`, MySQL queries) and any MySQL-source plugin (e.g. `statsdrone-analytics`) crashed with `ModuleNotFoundError: No module named 'pymysql'`. The floor avoids CVE-2024-36039 (PyMySQL ≤1.0.x). Reported from the field by the StatsDrone plugin author (B309).
- **`install.sh` now checks out the latest release tag instead of tracking `main`.** v1.0.1 and v1.0.2 existed only as tags while `main` sat at v1.0.0, so every fresh clone got two long-fixed 401 bugs. The installer (and its update path) now fetches tags and pins the newest release; `main` is also brought up to the release line as of this release.
- **`VERSION` now reports the actual release.** The file stayed at `1.0.0` through v1.0.1 and v1.0.2, so `/api` health and the FastAPI docs misreported the running version.

### Added

- **B308 — Plugins can persist a credential they capture in-route (`nousviz_sdk.store_credential`, SDK 0.6.8).** Until now the plugin SDK could only *read* credentials (`get_credential`); the only encrypted-write path was core's OAuth redirect callback. Plugins that capture a secret directly in a route handler — e.g. an OAuth access/refresh token from a device / paste-back-code flow the provider can't redirect through core's callback — had nowhere contract-legal to store it. `store_credential(plugin_id, field_name, plaintext, credential_type="oauth2")` closes that gap: it dispatches to a privileged in-process writer the API registers at startup (symmetric to the existing read resolver), reusing the same encrypted-credentials path the operator Settings form uses. Field names may be namespaced (`access_token:<user_id>`) for per-user storage with no schema change. Available only from plugin route handlers (api-process); sync subprocesses raise `CredentialBrokerUnavailable` — they read credentials, they don't mint them.

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
